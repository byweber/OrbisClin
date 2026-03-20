"""
app/core/models.py — Modelos SQLAlchemy.

Correções em relação à versão anterior:
  - Tabelas renomeadas: 'sessions' → 'exam_sessions', 'files' → 'exam_files'
    (consistência com as queries e routers)
  - Adicionado campo extracted_text em ExamFile (necessário para o worker Celery)
  - Índice composto em ExamFile para buscas frequentes por session_id + file_type
  - Imports via pacote app.core (não imports relativos planos)
"""
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Index, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="VIEWER")
    matricula = Column(String, nullable=True)
    birth_date = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


class Patient(Base):
    __tablename__ = "patients"

    id = Column(String, primary_key=True)
    name = Column(String, index=True)
    birth_date = Column(String, nullable=True)
    sex = Column(String, nullable=True)

    sessions = relationship("ExamSession", back_populates="patient", lazy="select")


class ExamSession(Base):
    __tablename__ = "exam_sessions"  # era 'sessions'

    id = Column(Integer, primary_key=True, index=True)
    accession_number = Column(String, unique=True, index=True)
    patient_id = Column(String, ForeignKey("patients.id"), index=True)
    procedure_type = Column(String, index=True)
    exam_date = Column(String, index=True)
    requesting_physician = Column(String, nullable=True)
    performing_physician = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now, index=True)

    patient = relationship("Patient", back_populates="sessions")
    files = relationship("ExamFile", back_populates="session", lazy="select")


class ExamFile(Base):
    __tablename__ = "exam_files"  # era 'files'

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("exam_sessions.id"), index=True)
    file_type = Column(String)
    file_path = Column(String)
    filename = Column(String)
    extracted_text = Column(Text, nullable=True)  # preenchido pelo worker Celery
    uploaded_at = Column(DateTime, default=datetime.now, index=True)

    session = relationship("ExamSession", back_populates="files")

    __table_args__ = (
        Index("ix_examfile_session_type", "session_id", "file_type"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    action = Column(String, index=True)
    target = Column(String)
    details = Column(String)
    timestamp = Column(DateTime, default=datetime.now, index=True)
