"""
app/routers/audit.py — Trilha de auditoria.
"""
import hashlib
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.core import models

router = APIRouter(prefix="/api/audit", tags=["Audit"])


def _short_hash(log: models.AuditLog) -> str:
    raw = f"{log.id}{log.username}{log.action}{log.target}{log.timestamp}"
    return hashlib.sha256(raw.encode()).hexdigest()[:8].upper()


@router.get("")
@router.get("/")
async def get_audit_logs(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current=Depends(require_admin),
):
    query = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc())

    if start:
        try:
            query = query.filter(models.AuditLog.timestamp >= datetime.strptime(start, "%Y-%m-%d"))
        except ValueError:
            pass
    if end:
        try:
            end_dt = datetime.strptime(end, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(models.AuditLog.timestamp <= end_dt)
        except ValueError:
            pass

    logs = query.limit(500).all()
    return [
        {
            "date": log.timestamp.strftime("%d/%m/%Y %H:%M:%S") if log.timestamp else "-",
            "time": log.timestamp.strftime("%d/%m %H:%M") if log.timestamp else "-",
            "user": log.username,
            "action": log.action,
            "target": log.target or "-",
            "details": log.details or "-",
            "hash_short": _short_hash(log),
        }
        for log in logs
    ]
