"""
worker.py — Celery worker para tarefas assíncronas.

Correções:
  1. SessionLocal instanciado dentro da task (não no import), evitando
     problemas de thread-safety do SQLite em processos separados.
  2. Tratamento explícito de PDFs corrompidos/protegidos por senha.
  3. Timeout de processamento para PDFs muito grandes.
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
    # Evita tasks zumbis
    task_soft_time_limit=120,
    task_time_limit=180,
)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def extract_text_from_pdf_task(self, file_path: str, file_id: int) -> str:
    """
    Extrai texto de um PDF e salva no campo extracted_text do ExamFile.
    Importa SessionLocal aqui dentro para garantir isolamento por processo.
    """
    # Import tardio: garante que cada worker cria sua própria conexão
    from database import SessionLocal
    from models import ExamFile

    if not file_path.lower().endswith(".pdf"):
        return "Skipped: not a PDF"

    if not os.path.exists(file_path):
        logger.warning(f"[CELERY] Arquivo não encontrado: {file_path}")
        return "Skipped: file not found"

    db = SessionLocal()
    try:
        logger.info(f"[CELERY] Extraindo texto do arquivo ID={file_id}: {file_path}")

        try:
            doc = fitz.open(file_path)
        except fitz.FileDataError as e:
            logger.warning(f"[CELERY] PDF corrompido (ID={file_id}): {e}")
            return f"Skipped: corrupt PDF — {e}"

        # PDF protegido por senha
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
            else:
                logger.warning(f"[CELERY] ExamFile ID={file_id} não encontrado no banco.")
                return "Skipped: record not found"

        return "Empty: no text extracted"

    except Exception as exc:
        db.rollback()
        logger.error(f"[CELERY] Erro inesperado (ID={file_id}): {exc}", exc_info=True)
        # Tenta novamente em caso de erro transitório
        raise self.retry(exc=exc)

    finally:
        db.close()
