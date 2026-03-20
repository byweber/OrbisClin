"""
app/routers/timeline.py — Timeline evolutiva de imagens por paciente.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.core import models

router = APIRouter(tags=["Timeline"])


def _fmt_date(d: str | None) -> str:
    if not d:
        return "-"
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return d


@router.get("/api/timeline/{patient_id}")
async def get_patient_timeline(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(404, "Paciente não encontrado.")

    sessions = (
        db.query(models.ExamSession)
        .filter(
            models.ExamSession.patient_id == patient_id,
            models.ExamSession.procedure_type.in_(["DERMATOLOGIA", "AVALIAÇÃO DE FERIDAS"]),
        )
        .options(joinedload(models.ExamSession.files))
        .order_by(models.ExamSession.exam_date.asc())
        .all()
    )

    timeline_data = []
    for s in sessions:
        images = [
            f for f in s.files
            if f.file_path.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        if images:
            timeline_data.append({
                "session_id": s.id,
                "exam_date_fmt": _fmt_date(s.exam_date),
                "procedure": s.procedure_type,
                "accession_number": s.accession_number,
                "images": [{"file_id": img.id, "filename": img.filename} for img in images],
            })

    return {
        "patient_id": patient.id,
        "patient_name": patient.name,
        "timeline": timeline_data,
    }