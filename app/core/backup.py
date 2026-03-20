"""
app/core/backup.py — Geração de backup completo (código + banco + storage).
"""
import os
import zipfile
from datetime import datetime
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()

# Raiz do projeto (dois níveis acima de app/core/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKUP_DIR = BASE_DIR / "backups"
MAX_BACKUPS = 7

IGNORE_DIRS = {
    "backups", "__pycache__", "venv", ".git", ".idea", ".vscode",
    "test_storage", ".pytest_cache",
}
IGNORE_EXTENSIONS = {".pyc", ".log", ".tmp"}


def create_backup() -> str | None:
    """Gera backup FULL e retorna o caminho do zip criado."""
    print("--- INICIANDO BACKUP COMPLETO DO ORBISCLIN ---")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    zip_filename = f"orbisclin_backup_{timestamp}.zip"
    zip_path = BACKUP_DIR / zip_filename

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(BASE_DIR):
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                for file in files:
                    if any(file.endswith(ext) for ext in IGNORE_EXTENSIONS):
                        continue
                    file_abs = Path(root) / file
                    if file_abs == zip_path:
                        continue
                    rel_path = file_abs.relative_to(BASE_DIR)
                    zipf.write(file_abs, arcname=str(rel_path))

        size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"Backup criado: {zip_path} ({size_mb:.2f} MB)")
        _clean_old_backups()
        return str(zip_path)

    except Exception as e:
        print(f"ERRO no backup: {e}")
        return None


def _clean_old_backups() -> None:
    try:
        files = sorted(
            [BACKUP_DIR / f for f in os.listdir(BACKUP_DIR) if f.endswith(".zip")],
            key=os.path.getmtime,
        )
        for old in files[:-MAX_BACKUPS]:
            old.unlink(missing_ok=True)
            print(f"  Backup antigo removido: {old.name}")
    except Exception as e:
        print(f"Erro na limpeza de backups: {e}")


if __name__ == "__main__":
    create_backup()
