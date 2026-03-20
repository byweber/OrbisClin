from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timedelta, time
import os

# Imports locais
from database import get_db
from models import User, ExamSession, ExamFile, Patient, AuditLog
from security import get_current_user, log_audit
import backup  # Script de backup criado anteriormente

router = APIRouter(tags=["Stats"])

@router.get("/api/stats")
async def get_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Segurança: Apenas ADMIN vê estatísticas
    if current_user.role != "ADMIN":
        # Retorna estrutura zerada para não quebrar o frontend se acessado indevidamente
        return {
            "total_exams": 0, "total_files": 0, "uploads_today": 0, 
            "history": [], "types": []
        }
    
    today = datetime.now().date()
    
    # --- Contadores Principais ---
    total_exams = db.query(ExamSession).count()
    total_files = db.query(ExamFile).count()
    
    # Uploads de hoje (Usando intervalo seguro de datas)
    start_of_day = datetime.combine(today, time.min)
    end_of_day = datetime.combine(today, time.max)
    uploads_today = db.query(ExamFile).filter(
        ExamFile.uploaded_at >= start_of_day,
        ExamFile.uploaded_at <= end_of_day
    ).count()
    
    # --- Gráfico 1: Histórico de Uploads (7 dias) ---
    # Geramos os últimos 7 dias manualmente para garantir que dias com 0 apareçam
    history = []
    for i in range(6, -1, -1):
        target_date = today - timedelta(days=i)
        d_start = datetime.combine(target_date, time.min)
        d_end = datetime.combine(target_date, time.max)
        
        # Count com filtro de range (Funciona 100% em SQLite e Postgres)
        count = db.query(ExamFile).filter(
            ExamFile.uploaded_at >= d_start,
            ExamFile.uploaded_at <= d_end
        ).count()
        
        history.append({
            "date": target_date.strftime("%d/%m"),
            "count": count
        })

    # --- Gráfico 2: Distribuição por Tipo ---
    # Agrupa por tipo de procedimento
    types_query = db.query(
        ExamSession.procedure_type, 
        func.count(ExamSession.id)
    ).group_by(ExamSession.procedure_type).all()
    
    type_data = []
    for t in types_query:
        label = t[0] if t[0] else "OUTROS" # Trata NULL como Outros
        type_data.append({"label": label, "value": t[1]})

    return {
        "total_exams": total_exams, 
        "total_files": total_files, 
        "uploads_today": uploads_today, 
        "history": history, 
        "types": type_data
    }

@router.get("/api/audit")
async def get_audit(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "ADMIN": return []
    # Busca os últimos 50 logs ordenados por data
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(50).all()
    return [{
        "date": l.timestamp.strftime("%d/%m %H:%M"), 
        "user": l.username, 
        "action": l.action, 
        "target": l.target, 
        "details": l.details
    } for l in logs]

@router.get("/api/reports")
async def get_reports(
    start: str = Query(None), end: str = Query(None), type: str = Query(None), req: str = Query(None),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    q = db.query(ExamSession).join(Patient)
    
    # Filtros dinâmicos
    if start: q = q.filter(ExamSession.exam_date >= start)
    if end: q = q.filter(ExamSession.exam_date <= end)
    if type and type != "TODOS": q = q.filter(ExamSession.procedure_type == type)
    if req: q = q.filter(ExamSession.requesting_physician.like(f"%{req.upper()}%"))
    
    res = q.order_by(ExamSession.exam_date.desc()).all()
    
    # Auditoria leve (só conta o tamanho) para não floodar o log
    log_audit(db, current_user.username, "REPORT_GENERATED", f"Registros: {len(res)}")
    
    return [{
        "exam_date": s.exam_date,
        "patient_name": s.patient.name,
        "procedure": s.procedure_type,
        "requesting_physician": s.requesting_physician,
        "performing_physician": s.performing_physician
    } for s in res]

# Rota de Backup Manual (Implementada anteriormente)
from fastapi.responses import FileResponse
@router.get("/api/system/backup")
async def trigger_manual_backup(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "ADMIN": 
        raise HTTPException(403, "Acesso restrito a administradores.")
    
    zip_path = backup.create_backup()
    
    if zip_path and os.path.exists(zip_path):
        filename = os.path.basename(zip_path)
        log_audit(db, current_user.username, "SYSTEM_BACKUP", "Manual Download", filename)
        return FileResponse(zip_path, filename=filename, media_type='application/zip')
    else:
        raise HTTPException(500, "Falha ao gerar arquivo de backup.")