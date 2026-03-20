"""
app/routers/reports.py — Relatórios gerenciais filtráveis.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user, log_audit
from app.core import models

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("")
@router.get("/")
async def get_reports(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    req: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    query = (
        db.query(models.ExamSession)
        .join(models.Patient)
        .options(joinedload(models.ExamSession.patient))
        .order_by(models.ExamSession.exam_date.desc())
    )

    if start:
        query = query.filter(models.ExamSession.exam_date >= start)
    if end:
        query = query.filter(models.ExamSession.exam_date <= end)
    if type and type != "TODOS":
        query = query.filter(models.ExamSession.procedure_type == type)
    if req:
        query = query.filter(
            models.ExamSession.requesting_physician.ilike(f"%{req.upper()}%")
        )

    sessions = query.limit(1000).all()
    log_audit(db, current.username, "REPORT_GENERATED", f"Registros: {len(sessions)}")

    def _fmt_date(d: str | None) -> str:
        if not d:
            return "-"
        try:
            return datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return d

    return [
        {
            "exam_date": _fmt_date(s.exam_date),
            "patient_name": s.patient.name if s.patient else "-",
            "patient_id": s.patient_id,
            "accession_number": s.accession_number,
            "procedure": s.procedure_type or "-",
            "requesting_physician": s.requesting_physician or "-",
            "performing_physician": s.performing_physician or "-",
        }
        for s in sessions
    ]