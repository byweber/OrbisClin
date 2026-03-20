"""
app/routers/users.py — CRUD completo de usuários.

ATENÇÃO: a rota /me/password deve ser declarada ANTES de /{user_id}/password,
caso contrário o FastAPI interpreta "me" como um user_id (string → 422/403).
"""
from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import User
from app.core.security import (
    get_current_user, get_password_hash, log_audit,
    require_admin, validate_password_complexity, verify_password,
)

router = APIRouter(prefix="/api/users", tags=["Users"])


# ── Usuário atual — acessível a qualquer role autenticada ─────────────────────

@router.get("/me")
async def get_me(
    current: User = Depends(get_current_user),
):
    """Endpoint leve para verificar autenticação e obter dados do usuário logado."""
    return {
        "id": current.id,
        "username": current.username,
        "full_name": current.full_name,
        "role": current.role,
        "is_active": current.is_active,
    }


# ── Listagem ──────────────────────────────────────────────────────────────────

@router.get("")
@router.get("/")
async def list_users(
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
):
    return [
        {"id": u.id, "username": u.username, "full_name": u.full_name,
         "role": u.role, "matricula": u.matricula, "birth_date": u.birth_date,
         "is_active": u.is_active}
        for u in db.query(User).order_by(User.full_name).all()
    ]


# ── Criação ───────────────────────────────────────────────────────────────────

@router.post("")
@router.post("/")
async def create_user(
    full_name: str = Form(...), username: str = Form(...),
    password: str = Form(...), role: str = Form("VIEWER"),
    matricula: str = Form(""), birth_date: str = Form(""),
    db: Session = Depends(get_db), current: User = Depends(require_admin),
):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(409, detail={"message": f"Login '{username}' já está em uso."})
    validate_password_complexity(password)
    if role not in ("VIEWER", "MEDICO", "ADMIN"):
        raise HTTPException(422, detail={"message": "Perfil inválido."})
    u = User(username=username.strip().lower(), hashed_password=get_password_hash(password),
             full_name=full_name.strip().upper(), role=role,
             matricula=matricula.strip() or None, birth_date=birth_date or None, is_active=True)
    db.add(u); db.commit(); db.refresh(u)
    log_audit(db, current.username, "USER_CREATE", u.username, f"Role: {role}")
    return JSONResponse({"status": "success", "id": u.id})


# ── Troca de senha pelo próprio usuário (ANTES de /{user_id}) ─────────────────

@router.post("/me/password")
async def change_my_password(
    current_password: str = Form(...), new_password: str = Form(...),
    db: Session = Depends(get_db), current: User = Depends(get_current_user),
):
    if not verify_password(current_password, current.hashed_password):
        raise HTTPException(401, detail={"message": "Senha atual incorreta."})
    validate_password_complexity(new_password)
    current.hashed_password = get_password_hash(new_password)
    db.commit()
    log_audit(db, current.username, "PWD_CHANGE_SELF", current.username)
    return JSONResponse({"status": "success", "message": "Senha alterada com sucesso."})


# ── Edição ────────────────────────────────────────────────────────────────────

@router.put("/{user_id}")
async def update_user(
    user_id: int, full_name: str = Form(...), username: str = Form(...),
    role: str = Form(...), matricula: str = Form(""), birth_date: str = Form(""),
    db: Session = Depends(get_db), current: User = Depends(require_admin),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, detail={"message": "Usuário não encontrado."})
    if username != u.username:
        if db.query(User).filter(User.username == username).first():
            raise HTTPException(409, detail={"message": f"Login '{username}' já está em uso."})
    if role not in ("VIEWER", "MEDICO", "ADMIN"):
        raise HTTPException(422, detail={"message": "Perfil inválido."})
    u.full_name = full_name.strip().upper()
    u.username = username.strip().lower()
    u.role = role
    u.matricula = matricula.strip() or None
    u.birth_date = birth_date or None
    db.commit()
    log_audit(db, current.username, "USER_UPDATE", u.username, f"Role: {role}")
    return JSONResponse({"status": "success"})


# ── Status ────────────────────────────────────────────────────────────────────

@router.put("/{user_id}/status")
async def toggle_user_status(
    user_id: int,
    db: Session = Depends(get_db), current: User = Depends(require_admin),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, detail={"message": "Usuário não encontrado."})
    if u.id == current.id:
        raise HTTPException(400, detail={"message": "Você não pode inativar sua própria conta."})
    u.is_active = not u.is_active
    db.commit()
    log_audit(db, current.username, "ACTIVATE_USER" if u.is_active else "DEACTIVATE_USER", u.username)
    return JSONResponse({"status": "success", "is_active": u.is_active})


# ── Reset de senha por admin ──────────────────────────────────────────────────

@router.post("/{user_id}/password")
async def admin_reset_password(
    user_id: int, password: str = Form(...),
    db: Session = Depends(get_db), current: User = Depends(require_admin),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, detail={"message": "Usuário não encontrado."})
    validate_password_complexity(password)
    u.hashed_password = get_password_hash(password)
    db.commit()
    log_audit(db, current.username, "PWD_RESET_ADMIN", u.username)
    return JSONResponse({"status": "success", "message": "Senha redefinida com sucesso."})