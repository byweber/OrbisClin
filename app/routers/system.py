"""
app/routers/system.py — Operações de sistema (backup).
"""
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.backup import create_backup
from app.core.security import require_admin, log_audit
from app.core.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("/backup")
async def download_backup(
    db: Session = Depends(get_db),
    current=Depends(require_admin),
):
    zip_path = create_backup()
    if not zip_path or not os.path.exists(zip_path):
        raise HTTPException(500, "Falha ao gerar backup.")

    filename = os.path.basename(zip_path)
    log_audit(db, current.username, "SYSTEM_BACKUP", "Manual Download", filename)
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
