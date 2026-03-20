from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User
# CORREÇÃO MANTIDA: verify_password presente
from security import get_current_user, get_password_hash, log_audit, validate_password_complexity, verify_password

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.get("")
async def get_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "ADMIN": raise HTTPException(403)
    return [{"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role, "matricula": u.matricula, "birth_date": u.birth_date, "is_active": u.is_active} for u in db.query(User).all()]

@router.post("")
async def create_user(
    username: str = Form(...), password: str = Form(...), full_name: str = Form(...), 
    role: str = Form(...), matricula: str = Form(...), birth_date: str = Form(...),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if current_user.role != "ADMIN": raise HTTPException(403)
    if not validate_password_complexity(password): return JSONResponse({"status": "error", "message": "Senha fraca. Min 8 chars, letras e números."}, 400)
    if db.query(User).filter(User.username == username).first(): return JSONResponse({"status": "error", "message": "Já existe"}, 400)
    db.add(User(username=username, hashed_password=get_password_hash(password), full_name=full_name.upper(), role=role, matricula=matricula, birth_date=birth_date, is_active=True))
    db.commit(); log_audit(db, current_user.username, "USER_CREATE", username)
    return JSONResponse({"status": "success"})

@router.post("/me/password")
async def change_own_password(current_password: str = Form(...), new_password: str = Form(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not verify_password(current_password, current_user.hashed_password): return JSONResponse({"status": "error", "message": "Senha atual incorreta"}, 400)
    if not validate_password_complexity(new_password): return JSONResponse({"status": "error", "message": "Senha fraca"}, 400)
    current_user.hashed_password = get_password_hash(new_password); db.commit()
    log_audit(db, current_user.username, "PWD_CHANGE_SELF", "Self", "OK")
    return JSONResponse({"status": "success"})

@router.post("/{user_id}/password")
async def admin_reset_password(user_id: int, password: str = Form(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "ADMIN": raise HTTPException(403, "Restrito")
    if not validate_password_complexity(password): return JSONResponse({"status": "error", "message": "Senha fraca"}, 400)
    u = db.query(User).filter(User.id == user_id).first()
    if not u: return JSONResponse({"status": "error"}, 404)
    u.hashed_password = get_password_hash(password); db.commit()
    log_audit(db, current_user.username, "PWD_RESET_ADMIN", u.username)
    return JSONResponse({"status": "success"})

@router.put("/{user_id}/status")
async def toggle_user_status(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "ADMIN": raise HTTPException(403, "Restrito")
    if current_user.id == user_id: return JSONResponse({"status": "error", "message": "Não pode inativar a si mesmo"}, 400)
    u = db.query(User).filter(User.id == user_id).first()
    if u: u.is_active = not u.is_active; db.commit(); log_audit(db, current_user.username, "USER_STATUS", u.username, str(u.is_active)); return JSONResponse({"status": "success"})
    return JSONResponse({"status": "error"}, 404)

@router.put("/{user_id}")
async def update_user_data(
    user_id: int, username: str = Form(...), full_name: str = Form(...), 
    role: str = Form(...), matricula: str = Form(...), birth_date: str = Form(...),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if current_user.role != "ADMIN": raise HTTPException(403)
    u = db.query(User).filter(User.id == user_id).first()
    if not u: return JSONResponse({"status": "error"}, 404)
    if db.query(User).filter(User.username == username, User.id != user_id).first(): return JSONResponse({"status": "error", "message": "Login em uso"}, 400)
    u.username = username; u.full_name = full_name.upper(); u.role = role; u.matricula = matricula; u.birth_date = birth_date
    db.commit(); log_audit(db, current_user.username, "USER_UPDATE", username)
    return JSONResponse({"status": "success"})