"""
app/routers/users.py — CRUD completo de usuários.
"""
from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import User
from app.core.security import (
    get_current_user,
    get_password_hash,
    log_audit,
    require_admin,
    validate_password_complexity,
    verify_password,
)

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("")
@router.get("/")
async def list_users(
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
):
    users = db.query(User).order_by(User.full_name).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "role": u.role,
            "matricula": u.matricula,
            "birth_date": u.birth_date,
            "is_active": u.is_active,
        }
        for u in users
    ]


@router.post("")
@router.post("/")
async def create_user(
    full_name: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("VIEWER"),
    matricula: str = Form(""),
    birth_date: str = Form(""),
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(409, detail={"message": f"Login '{username}' já está em uso."})

    validate_password_complexity(password)

    if role not in ("VIEWER", "MEDICO", "ADMIN"):
        raise HTTPException(422, detail={"message": "Perfil inválido."})

    new_user = User(
        username=username.strip().lower(),
        hashed_password=get_password_hash(password),
        full_name=full_name.strip().upper(),
        role=role,
        matricula=matricula.strip() or None,
        birth_date=birth_date or None,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    log_audit(db, current.username, "USER_CREATE", new_user.username, f"Role: {role}")
    return JSONResponse({"status": "success", "id": new_user.id})


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    full_name: str = Form(...),
    username: str = Form(...),
    role: str = Form(...),
    matricula: str = Form(""),
    birth_date: str = Form(""),
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, detail={"message": "Usuário não encontrado."})
    if username != user.username:
        if db.query(User).filter(User.username == username).first():
            raise HTTPException(409, detail={"message": f"Login '{username}' já está em uso."})
    if role not in ("VIEWER", "MEDICO", "ADMIN"):
        raise HTTPException(422, detail={"message": "Perfil inválido."})
    user.full_name = full_name.strip().upper()
    user.username = username.strip().lower()
    user.role = role
    user.matricula = matricula.strip() or None
    user.birth_date = birth_date or None
    db.commit()
    log_audit(db, current.username, "USER_UPDATE", user.username, f"Role: {role}")
    return JSONResponse({"status": "success"})


@router.put("/{user_id}/status")
async def toggle_user_status(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, detail={"message": "Usuário não encontrado."})
    if user.id == current.id:
        raise HTTPException(400, detail={"message": "Você não pode inativar sua própria conta."})
    user.is_active = not user.is_active
    db.commit()
    action = "ACTIVATE_USER" if user.is_active else "DEACTIVATE_USER"
    log_audit(db, current.username, action, user.username)
    return JSONResponse({"status": "success", "is_active": user.is_active})


@router.post("/{user_id}/password")
async def admin_reset_password(
    user_id: int,
    password: str = Form(...),
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, detail={"message": "Usuário não encontrado."})
    validate_password_complexity(password)
    user.hashed_password = get_password_hash(password)
    db.commit()
    log_audit(db, current.username, "PWD_RESET_ADMIN", user.username)
    return JSONResponse({"status": "success", "message": "Senha redefinida com sucesso."})


@router.post("/me/password")
async def change_my_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if not verify_password(current_password, current.hashed_password):
        raise HTTPException(401, detail={"message": "Senha atual incorreta."})
    validate_password_complexity(new_password)
    current.hashed_password = get_password_hash(new_password)
    db.commit()
    log_audit(db, current.username, "PWD_CHANGE_SELF", current.username)
    return JSONResponse({"status": "success", "message": "Senha alterada com sucesso."})
