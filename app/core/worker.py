"""
app/core/worker.py — Celery worker para extração de texto de PDFs.

Imports tardios dentro da task garantem isolamento por processo (SQLite thread-safety).
"""
import os
import logging

import fitz  # PyMuPDF
from celery import Celery

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "orbisclin_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_soft_time_limit=120,
    task_time_limit=180,
)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def extract_text_from_pdf_task(self, file_path: str, file_id: int) -> str:
    # Import tardio: cada worker cria sua própria conexão ao banco
    from app.core.database import SessionLocal
    from app.core.models import ExamFile

    if not file_path.lower().endswith(".pdf"):
        return "Skipped: not a PDF"

    if not os.path.exists(file_path):
        logger.warning(f"[CELERY] Arquivo não encontrado: {file_path}")
        return "Skipped: file not found"

    db = SessionLocal()
    try:
        try:
            doc = fitz.open(file_path)
        except fitz.FileDataError as e:
            logger.warning(f"[CELERY] PDF corrompido (ID={file_id}): {e}")
            return f"Skipped: corrupt PDF — {e}"

        if doc.needs_pass:
            logger.warning(f"[CELERY] PDF protegido por senha (ID={file_id})")
            doc.close()
            return "Skipped: password-protected PDF"

        try:
            full_text = " ".join(page.get_text() for page in doc)
        finally:
            doc.close()

        clean_text = " ".join(full_text.upper().split())

        if clean_text:
            record = db.query(ExamFile).filter(ExamFile.id == file_id).first()
            if record:
                record.extracted_text = clean_text
                db.commit()
                logger.info(f"[CELERY] Texto salvo para ID={file_id} ({len(clean_text)} chars)")
                return "Success"
            return "Skipped: record not found"

        return "Empty: no text extracted"

    except Exception as exc:
        db.rollback()
        logger.error(f"[CELERY] Erro inesperado (ID={file_id}): {exc}", exc_info=True)
        raise self.retry(exc=exc)

    finally:
        db.close()
