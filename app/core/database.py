"""
app/core/database.py — Configuração do banco de dados SQLAlchemy.
Lê DATABASE_URL e STORAGE_DIR exclusivamente via config.py / .env.
"""
import pathlib
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import get_settings

settings = get_settings()

STORAGE_DIR = pathlib.Path(settings.STORAGE_DIR)
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# connect_args apenas para SQLite
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
