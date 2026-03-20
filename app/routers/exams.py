import os
import aiofiles
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Query
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session, joinedload
from jose import jwt
from database import get_db, STORAGE_DIR
from models import User, ExamSession, ExamFile, Patient
from security import get_current_user, log_audit, SECRET_KEY, ALGORITHM

router = APIRouter(tags=["Exams"])


@router.get("/api/patients/{patient_id}")
async def get_patient(patient_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if not p: return JSONResponse({"found": False})
    return JSONResponse({"found": True, "name": p.name, "birth_date": p.birth_date, "sex": p.sex})


@router.put("/api/patients/{patient_id}")
async def update_patient(patient_id: str, name: str = Form(...), birth_date: str = Form(...), sex: str = Form(...),
                         db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "ADMIN": raise HTTPException(403, "Restrito a ADMIN")
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if not p: raise HTTPException(404, "Paciente não encontrado")
    today = datetime.now().strftime("%Y-%m-%d")
    if birth_date > today: raise HTTPException(400, "Data futura inválida")
    old = f"{p.name} ({p.birth_date})"
    p.name = name.upper().strip();
    p.birth_date = birth_date;
    p.sex = sex
    db.commit()
    log_audit(db, current_user.username, "PATIENT_UPDATE", patient_id, f"{old} -> {p.name}")
    return JSONResponse({"status": "success"})


@router.post("/api/upload")
async def upload_exam(
        accession_number: str = Form(...), patient_id: str = Form(...), patient_name: str = Form(...),
        file_type: str = Form(...),
        procedure_type: Optional[str] = Form(None), birth_date: Optional[str] = Form(None),
        sex: Optional[str] = Form(None),
        exam_date: Optional[str] = Form(None), requesting_physician: Optional[str] = Form(None),
        performing_physician: Optional[str] = Form(None),
        file: List[UploadFile] = File(...), db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role == "VIEWER": raise HTTPException(403, "Acesso Negado")
    if not accession_number.isdigit() or not patient_id.isdigit(): raise HTTPException(400, "IDs devem ser numéricos")

    # --- VALIDAÇÃO DE SEGURANÇA E LOTE ---
    if procedure_type not in ["DERMATOLOGIA", "AVALIAÇÃO DE FERIDAS"] and len(file) > 1:
        raise HTTPException(400, "Múltiplos arquivos são permitidos apenas para Dermatologia e Avaliação de Feridas.")

    for f in file:
        header = await f.read(4);
        await f.seek(0)
        is_pdf = header == b'%PDF'
        is_jpeg = header[:3] == b'\xff\xd8\xff'
        is_png = header == b'\x89PNG'

        if procedure_type in ["DERMATOLOGIA", "AVALIAÇÃO DE FERIDAS"]:
            if not (is_pdf or is_jpeg or is_png):
                raise HTTPException(400, f"O arquivo {f.filename} é inválido. Envie PDF, JPG ou PNG.")
        else:
            if not is_pdf:
                raise HTTPException(400,
                                    f"O arquivo {f.filename} é inválido. Apenas formato PDF é aceito para este exame.")
    # ----------------------------------------

    try:
        acc, pid, pname = accession_number.strip(), patient_id.strip(), patient_name.upper().strip()
        patient = db.query(Patient).filter(Patient.id == pid).first()
        if patient:
            if patient.name != pname: return JSONResponse(
                {"status": "error", "message": f"ID {pid} pertence a {patient.name}"}, 400)
        else:
            patient = Patient(id=pid, name=pname, birth_date=birth_date, sex=sex)
            db.add(patient);
            db.commit()

        sess = db.query(ExamSession).filter(ExamSession.accession_number == acc).first()
        if sess:
            if sess.patient_id != pid: return JSONResponse(
                {"status": "error", "message": "Pedido duplicado para outro paciente"}, 400)

            # Validação para não sobrescrever um EXAME já existente nesta sessão
            if file_type == 'EXAME':
                exist_exam = db.query(ExamFile).filter(ExamFile.session_id == sess.id,
                                                       ExamFile.file_type == 'EXAME').first()
                if exist_exam: return JSONResponse(
                    {"status": "error", "message": "O exame principal já existe neste atendimento"}, 400)

            # Bloqueio de segurança para anexos
            if sess.procedure_type not in ["DERMATOLOGIA", "AVALIAÇÃO DE FERIDAS"]:
                for f in file:
                    header = await f.read(4);
                    await f.seek(0)
                    if header != b'%PDF': return JSONResponse(
                        {"status": "error", "message": "Apenas PDF é aceito para anexos deste tipo de exame."}, 400)
        else:
            sess = ExamSession(accession_number=acc, patient_id=pid, exam_date=exam_date, procedure_type=procedure_type,
                               requesting_physician=requesting_physician.upper(),
                               performing_physician=performing_physician.upper())
            db.add(sess);
            db.commit();
            db.refresh(sess)

        now = datetime.now()
        tdir = STORAGE_DIR / now.strftime("%Y") / now.strftime("%m") / acc
        tdir.mkdir(parents=True, exist_ok=True)

        # Salvando cada arquivo do array
        for idx, f in enumerate(file):
            header = await f.read(4);
            await f.seek(0)
            is_pdf = header == b'%PDF'
            is_jpeg = header[:3] == b'\xff\xd8\xff'

            ext = os.path.splitext(f.filename)[1].lower()
            if not ext: ext = ".pdf" if is_pdf else (".jpg" if is_jpeg else ".png")

            suffix = f"_{idx + 1}" if len(file) > 1 else ""
            fpath = tdir / f"{now.strftime('%Y%m%d_%H%M%S')}{suffix}_{file_type}{ext}"

            async with aiofiles.open(fpath, "wb") as buffer:
                while content := await f.read(1024 * 1024): await buffer.write(content)

            db.add(ExamFile(session_id=sess.id, file_type=file_type, file_path=str(fpath), filename=f.filename))
            log_audit(db, current_user.username, "UPLOAD", f"{pname} #{acc} [{file_type}]", f.filename)

        db.commit()
        return JSONResponse({"status": "success"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, 500)


@router.get("/api/search")
async def search_exams(q: str = "", type: str = "", page: int = 1, limit: int = 20, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    try:
        query = db.query(ExamSession).join(Patient)
        if q: s = f"%{q.upper()}%"; query = query.filter(
            (Patient.name.like(s)) | (Patient.id.like(s)) | (ExamSession.accession_number.like(s)))
        if type and type != "TODOS": query = query.filter(ExamSession.procedure_type == type)
        total = query.count()
        res = query.options(joinedload(ExamSession.patient), joinedload(ExamSession.files)).order_by(
            ExamSession.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

        data = [{
            "id": s.id, "patient_name": s.patient.name, "patient_id": s.patient.id,
            "birth_date": datetime.strptime(s.patient.birth_date, "%Y-%m-%d").strftime(
                "%d/%m/%Y") if s.patient.birth_date else "-",
            "birth_date_raw": s.patient.birth_date, "sex": s.patient.sex,
            "accession_number": s.accession_number, "exam_date": s.exam_date, "procedure": s.procedure_type or "GERAL",
            "req_phys": s.requesting_physician, "perf_phys": s.performing_physician,
            "files": [
                {"type": f.file_type, "name": f.filename, "date": f.uploaded_at.strftime("%d/%m %H:%M"), "id": f.id} for
                f in s.files]
        } for s in res]
        return {"data": data, "total": total, "page": page, "pages": (total + limit - 1) // limit}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.put("/api/sessions/{session_id}")
async def update_session(session_id: int, requesting_physician: str = Form(...), performing_physician: str = Form(...),
                         db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "ADMIN": raise HTTPException(403)
    s = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not s: raise HTTPException(404)
    s.requesting_physician = requesting_physician.upper();
    s.performing_physician = performing_physician.upper()
    db.commit();
    log_audit(db, user.username, "CLINICAL_UPDATE", f"Session #{s.accession_number}")
    return JSONResponse({"status": "success"})


@router.delete("/api/files/{file_id}")
async def delete_file(file_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "ADMIN": raise HTTPException(403)
    f = db.query(ExamFile).filter(ExamFile.id == file_id).first()
    if not f: raise HTTPException(404)
    if os.path.exists(f.file_path): os.remove(f.file_path)
    db.delete(f);
    db.commit();
    log_audit(db, user.username, "FILE_DELETE", f"ID: {file_id}")
    return JSONResponse({"status": "success"})


@router.get("/view/{file_id}")
async def view_file(file_id: int, token: str, db: Session = Depends(get_db)):
    try:
        username = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]).get("sub")
    except:
        raise HTTPException(401)
    f = db.query(ExamFile).filter(ExamFile.id == file_id).first()
    if not f: raise HTTPException(404)
    log_audit(db, username, "VIEW_FILE", f.filename, str(file_id))

    ext = os.path.splitext(f.file_path)[1].lower()
    media_type = "application/pdf"
    if ext in [".jpg", ".jpeg"]:
        media_type = "image/jpeg"
    elif ext == ".png":
        media_type = "image/png"

    return FileResponse(f.file_path, media_type=media_type)