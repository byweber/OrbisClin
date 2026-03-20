"""
app/routers/exams.py — Upload, busca e visualização de exames.

Correções:
  1. Bug do file seek: seek(0) → read(4) → seek(0) na detecção de extensão
  2. ILIKE em SQLite: usa func.lower() para busca case-insensitive real
  3. Imports via app.core
  4. Mantidos endpoints extras do projeto real:
     GET/PUT /api/patients/{id}, PUT /api/sessions/{id}, DELETE /api/files/{id}
  5. FIX: /view/{id} agora aceita httponly cookie além do query param ?token=
     (token via localStorage foi removido na migração para cookie — bug de visualização)
"""
import os
import aiofiles
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from jose import jwt, JWTError
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.database import get_db, STORAGE_DIR
from app.core.models import ExamFile, ExamSession, Patient, User
from app.core.security import SECRET_KEY, ALGORITHM, get_current_user, log_audit
# import do worker movido para dentro do upload (lazy) — evita bloqueio se Redis estiver fora

router = APIRouter(tags=["Exams"])
settings = get_settings()

MULTI_FILE_PROCEDURES = {"DERMATOLOGIA", "AVALIAÇÃO DE FERIDAS"}


# ── Extração de texto — Celery com fallback síncrono ─────────────────────────

def _enqueue_text_extraction(file_path: str, file_id: int, db) -> None:
    """
    Tenta enfileirar a extração de texto via Celery/Redis.
    Se Redis estiver indisponível, executa de forma síncrona no processo atual.
    Nunca bloqueia nem lança exceção — extração é sempre opcional.
    """
    import logging
    logger = logging.getLogger(__name__)

    # 1. Tenta Celery — verifica conexão com Redis antes de importar o worker
    try:
        import redis as _redis
        _r = _redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        _r.ping()   # falha rápido (1s) se Redis estiver fora
        _r.close()
        # Redis OK — usa Celery
        from app.core.worker import extract_text_from_pdf_task
        extract_text_from_pdf_task.delay(file_path, file_id)
        return
    except Exception:
        pass  # Redis fora — cai no fallback

    # 2. Fallback síncrono — extrai texto direto no processo, sem travar
    try:
        import fitz
        from app.core.models import ExamFile as _ExamFile
        if not os.path.exists(file_path):
            return
        doc = fitz.open(file_path)
        if doc.needs_pass:
            doc.close()
            return
        text = " ".join(page.get_text() for page in doc)
        doc.close()
        clean = " ".join(text.upper().split())
        if clean:
            record = db.query(_ExamFile).filter(_ExamFile.id == file_id).first()
            if record:
                record.extracted_text = clean
                db.commit()
                logger.info(f"[SYNC] Texto extraído para ID={file_id} ({len(clean)} chars)")
    except Exception as e:
        logger.warning(f"[SYNC] Extração de texto falhou (ID={file_id}): {e}")


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _detect_extension(f: UploadFile) -> str:
    """Lê magic bytes e retorna extensão correta, sempre reposicionando o cursor."""
    await f.seek(0)
    header = await f.read(4)
    await f.seek(0)   # SEMPRE após leitura
    if header[:3] == b'\xff\xd8\xff':
        return ".jpg"
    if header == b'\x89PNG':
        return ".png"
    if header == b'%PDF':
        return ".pdf"
    _, ext = os.path.splitext(f.filename or "")
    return ext.lower() if ext else ".bin"


async def _validate_file_type(f: UploadFile, procedure_type: Optional[str]) -> None:
    """Valida tipo do arquivo por magic bytes."""
    await f.seek(0)
    header = await f.read(4)
    await f.seek(0)
    is_pdf  = header == b'%PDF'
    is_jpg  = header[:3] == b'\xff\xd8\xff'
    is_png  = header == b'\x89PNG'
    if procedure_type in MULTI_FILE_PROCEDURES:
        if not (is_pdf or is_jpg or is_png):
            raise HTTPException(400, f"Arquivo inválido: {f.filename}. Envie PDF, JPG ou PNG.")
    else:
        if not is_pdf:
            raise HTTPException(400, f"Arquivo inválido: {f.filename}. Apenas PDF é aceito para este exame.")


# ── Pacientes ─────────────────────────────────────────────────────────────────

@router.get("/api/patients/{patient_id}")
async def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if not p:
        return JSONResponse({"found": False})
    return JSONResponse({"found": True, "name": p.name, "birth_date": p.birth_date, "sex": p.sex})


@router.put("/api/patients/{patient_id}")
async def update_patient(
    patient_id: str,
    name: str = Form(...),
    birth_date: str = Form(...),
    sex: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "ADMIN":
        raise HTTPException(403, "Restrito a ADMIN.")
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if not p:
        raise HTTPException(404, "Paciente não encontrado.")
    today = datetime.now().strftime("%Y-%m-%d")
    if birth_date > today:
        raise HTTPException(400, "Data de nascimento futura inválida.")
    old = f"{p.name} ({p.birth_date})"
    p.name = name.upper().strip()
    p.birth_date = birth_date
    p.sex = sex
    db.commit()
    log_audit(db, current_user.username, "PATIENT_UPDATE", patient_id, f"{old} → {p.name}")
    return JSONResponse({"status": "success"})


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post("/api/upload")
async def upload_exam(
    accession_number: str = Form(...),
    patient_id: str = Form(...),
    patient_name: str = Form(...),
    file_type: str = Form(...),
    procedure_type: Optional[str] = Form(None),
    birth_date: Optional[str] = Form(None),
    sex: Optional[str] = Form(None),
    exam_date: Optional[str] = Form(None),
    requesting_physician: Optional[str] = Form(None),
    performing_physician: Optional[str] = Form(None),
    file: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "VIEWER":
        raise HTTPException(403, "Acesso negado.")

    if procedure_type not in MULTI_FILE_PROCEDURES and len(file) > 1:
        raise HTTPException(400, "Múltiplos arquivos são permitidos apenas para Dermatologia e Avaliação de Feridas.")

    # Valida todos antes de salvar qualquer um
    for f in file:
        await _validate_file_type(f, procedure_type)

    acc   = accession_number.strip()
    pid   = patient_id.strip()
    pname = patient_name.upper().strip()

    patient = db.query(Patient).filter(Patient.id == pid).first()
    if patient:
        if patient.name != pname:
            return JSONResponse({"status": "error", "message": f"ID {pid} pertence a {patient.name}"}, 400)
    else:
        patient = Patient(id=pid, name=pname, birth_date=birth_date, sex=sex)
        db.add(patient)
        db.commit()

    sess = db.query(ExamSession).filter(ExamSession.accession_number == acc).first()
    if sess:
        if sess.patient_id != pid:
            return JSONResponse({"status": "error", "message": "Número de acesso pertence a outro paciente."}, 400)
        if file_type == "EXAME":
            exist_exam = db.query(ExamFile).filter(
                ExamFile.session_id == sess.id, ExamFile.file_type == "EXAME"
            ).first()
            if exist_exam:
                return JSONResponse({"status": "error", "message": "Exame principal já existe neste atendimento."}, 400)
    else:
        sess = ExamSession(
            accession_number=acc,
            patient_id=pid,
            exam_date=exam_date,
            procedure_type=procedure_type,
            requesting_physician=(requesting_physician or "").upper() or None,
            performing_physician=(performing_physician or "").upper() or None,
        )
        db.add(sess)
        db.commit()
        db.refresh(sess)

    now  = datetime.now()
    tdir = STORAGE_DIR / now.strftime("%Y") / now.strftime("%m") / acc
    tdir.mkdir(parents=True, exist_ok=True)

    saved = []
    for idx, f in enumerate(file):
        ext = await _detect_extension(f)  # seek correto aqui
        suffix = f"_{idx + 1}" if len(file) > 1 else ""
        fpath = tdir / f"{now.strftime('%Y%m%d_%H%M%S')}{suffix}_{file_type}{ext}"

        async with aiofiles.open(fpath, "wb") as buf:
            while chunk := await f.read(1024 * 1024):
                await buf.write(chunk)

        new_file = ExamFile(
            session_id=sess.id,
            file_type=file_type,
            file_path=str(fpath),
            filename=f.filename,
        )
        db.add(new_file)
        db.commit()
        db.refresh(new_file)
        saved.append(new_file.id)

        if ext == ".pdf":
            # Extração de texto: tenta Celery/Redis primeiro; se indisponível, faz direto no processo
            _enqueue_text_extraction(str(fpath), new_file.id, db)

        log_audit(db, current_user.username, "UPLOAD", f"{pname} #{acc} [{file_type}]", f.filename)

    return JSONResponse({"status": "success", "files": saved})


# ── Busca ─────────────────────────────────────────────────────────────────────

@router.get("/api/search")
async def search_exams(
    q: str = "",
    type: str = "",
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(ExamSession)
        .join(Patient)
        .options(joinedload(ExamSession.patient), joinedload(ExamSession.files))
    )

    if q:
        # func.lower() garante case-insensitive real no SQLite
        q_lower = q.lower()
        pattern = f"%{q_lower}%"
        query = query.filter(
            func.lower(Patient.name).like(pattern)
            | func.lower(Patient.id).like(pattern)
            | func.lower(ExamSession.accession_number).like(pattern)
        )

    if type and type not in ("TODOS", "IMAGEM (PACS)"):
        query = query.filter(ExamSession.procedure_type == type)

    total = query.count()
    results = (
        query.order_by(ExamSession.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    data = [
        {
            "id": s.id,
            "patient_name": s.patient.name,
            "patient_id": s.patient.id,
            "birth_date": (
                datetime.strptime(s.patient.birth_date, "%Y-%m-%d").strftime("%d/%m/%Y")
                if s.patient.birth_date else "-"
            ),
            "birth_date_raw": s.patient.birth_date,
            "sex": s.patient.sex,
            "accession_number": s.accession_number,
            "exam_date": (
                datetime.strptime(s.exam_date, "%Y-%m-%d").strftime("%d/%m/%Y")
                if s.exam_date else "-"
            ),
            "exam_date_raw": s.exam_date,
            "procedure": s.procedure_type or "GERAL",
            "req_phys": s.requesting_physician,
            "perf_phys": s.performing_physician,
            "is_pacs": False,
            "files": [
                {"id": f.id, "type": f.file_type, "name": f.filename,
                 "date": f.uploaded_at.strftime("%d/%m %H:%M")}
                for f in s.files
            ],
        }
        for s in results
    ]

    # Busca complementar no Orthanc PACS — desabilitada temporariamente
    # Para reativar: descomentar o bloco abaixo e restaurar a opção IMAGEM (PACS) em home.html
    # if type in ("", "TODOS", "IMAGEM (PACS)"):
    #     try:
    #         async with httpx.AsyncClient(timeout=3.0) as client:
    #             payload: dict = {"Level": "Study", "Expand": True, "Query": {}}
    #             if q:
    #                 payload["Query"]["PatientName"] = f"*{q.upper()}*" if not q.isdigit() else None
    #                 if q.isdigit():
    #                     payload["Query"]["PatientID"] = f"*{q}*"
    #             resp = await client.post(
    #                 f"{settings.ORTHANC_URL}/tools/find",
    #                 json=payload,
    #                 auth=(settings.ORTHANC_USER, settings.ORTHANC_PASS),
    #             )
    #             if resp.status_code == 200:
    #                 for st in resp.json():
    #                     data.append({
    #                         "id": st.get("ID"),
    #                         "patient_name": st.get("PatientMainDicomTags", {})
    #                                          .get("PatientName", "").replace("^", " "),
    #                         "patient_id": st.get("PatientMainDicomTags", {}).get("PatientID", ""),
    #                         "accession_number": st.get("MainDicomTags", {}).get("AccessionNumber", ""),
    #                         "procedure": "IMAGEM DICOM",
    #                         "is_pacs": True,
    #                         "files": [],
    #                     })
    #     except httpx.RequestError:
    #         pass  # Orthanc indisponível não quebra a busca local

    return {"data": data, "total": total, "page": page, "pages": (total + limit - 1) // limit}


# ── Sessões ───────────────────────────────────────────────────────────────────

@router.put("/api/sessions/{session_id}")
async def update_session(
    session_id: int,
    requesting_physician: str = Form(...),
    performing_physician: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "ADMIN":
        raise HTTPException(403)
    s = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not s:
        raise HTTPException(404)
    s.requesting_physician = requesting_physician.upper()
    s.performing_physician = performing_physician.upper()
    db.commit()
    log_audit(db, current_user.username, "CLINICAL_UPDATE", f"Session #{s.accession_number}")
    return JSONResponse({"status": "success"})


# ── Arquivos ──────────────────────────────────────────────────────────────────

@router.delete("/api/files/{file_id}")
async def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "ADMIN":
        raise HTTPException(403)
    f = db.query(ExamFile).filter(ExamFile.id == file_id).first()
    if not f:
        raise HTTPException(404)
    if os.path.exists(f.file_path):
        os.remove(f.file_path)
    db.delete(f)
    db.commit()
    log_audit(db, current_user.username, "FILE_DELETE", f"ID: {file_id}")
    return JSONResponse({"status": "success"})


@router.get("/view/{file_id}")
async def view_file(
    file_id: int,
    request: Request,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    # FIX: prioriza httponly cookie; aceita ?token= como fallback (compatibilidade)
    resolved_token = request.cookies.get("orbisclin_session") or token
    if not resolved_token:
        raise HTTPException(401, "Não autenticado.")

    try:
        payload = jwt.decode(resolved_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
    except JWTError:
        raise HTTPException(401, "Token inválido.")

    f = db.query(ExamFile).filter(ExamFile.id == file_id).first()
    if not f or not os.path.exists(f.file_path):
        raise HTTPException(404, "Arquivo não encontrado.")

    log_audit(db, username or "?", "VIEW_FILE", f.filename, str(file_id))

    ext = os.path.splitext(f.file_path)[1].lower()
    media_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".pdf": "application/pdf"}
    return FileResponse(f.file_path, media_type=media_types.get(ext, "application/octet-stream"))