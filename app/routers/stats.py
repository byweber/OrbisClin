"""
app/routers/stats.py — Estatísticas para o dashboard.
"""
from collections import defaultdict
from datetime import datetime, timedelta, time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.core import models

router = APIRouter(prefix="/api/stats", tags=["Stats"])


@router.get("")
@router.get("/")
async def get_stats(
    db: Session = Depends(get_db),
    current=Depends(require_admin),
):
    today = datetime.now().date()

    total_exams = db.query(models.ExamSession).count()
    total_files = db.query(models.ExamFile).count()

    start_of_day = datetime.combine(today, time.min)
    end_of_day   = datetime.combine(today, time.max)
    uploads_today = (
        db.query(models.ExamFile)
        .filter(models.ExamFile.uploaded_at >= start_of_day,
                models.ExamFile.uploaded_at <= end_of_day)
        .count()
    )

    # Histórico dos últimos 7 dias
    history = []
    for i in range(6, -1, -1):
        target = today - timedelta(days=i)
        d_start = datetime.combine(target, time.min)
        d_end   = datetime.combine(target, time.max)
        count = (
            db.query(models.ExamFile)
            .filter(models.ExamFile.uploaded_at >= d_start,
                    models.ExamFile.uploaded_at <= d_end)
            .count()
        )
        history.append({"date": target.strftime("%d/%m"), "count": count})

    # Distribuição por tipo de procedimento
    types_raw = (
        db.query(models.ExamSession.procedure_type,
                 db.query(models.ExamSession.id).filter(
                     models.ExamSession.procedure_type == models.ExamSession.procedure_type
                 ).count)
    )
    from sqlalchemy import func
    types_query = (
        db.query(models.ExamSession.procedure_type, func.count(models.ExamSession.id))
        .group_by(models.ExamSession.procedure_type)
        .all()
    )
    types = [
        {"label": t[0] if t[0] else "OUTROS", "value": t[1]}
        for t in types_query
    ]

    return {
        "total_exams": total_exams,
        "total_files": total_files,
        "uploads_today": uploads_today,
        "history": history,
        "types": types,
        "patients": db.query(models.Patient).count(),
    }
