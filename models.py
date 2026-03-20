from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    matricula = Column(String)
    birth_date = Column(String)
    role = Column(String, default="VIEWER")
    is_active = Column(Boolean, default=True)

class Patient(Base):
    __tablename__ = "patients"
    id = Column(String, primary_key=True, index=True) # Prontuário
    name = Column(String, index=True)
    birth_date = Column(String)
    sex = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    sessions = relationship("ExamSession", back_populates="patient", cascade="all, delete-orphan")

class ExamSession(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    accession_number = Column(String, unique=True, index=True)
    patient_id = Column(String, ForeignKey("patients.id"), index=True)
    exam_date = Column(String)
    procedure_type = Column(String)
    requesting_physician = Column(String)
    performing_physician = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    patient = relationship("Patient", back_populates="sessions")
    files = relationship("ExamFile", back_populates="session", cascade="all, delete-orphan")

class ExamFile(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    file_type = Column(String) 
    file_path = Column(String) 
    filename = Column(String)  
    uploaded_at = Column(DateTime, default=datetime.now)
    session = relationship("ExamSession", back_populates="files")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now)
    username = Column(String, index=True) 
    action = Column(String, index=True)   
    target = Column(String)               
    details = Column(Text)
    previous_hash = Column(String, default="0")
    hash = Column(String)