"""
app/routers/auth.py — Login, logout e refresh.
"""
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import User
from app.core.security import (
    clear_auth_cookie, create_access_token,
    log_audit, set_auth_cookie, verify_password,
)

limiter = Limiter(key_func=get_remote_address, enabled=not bool(os.getenv("TESTING")))
router = APIRouter(tags=["Auth"])


@router.post("/token")
@router.post("/api/auth/login")
@limiter.limit("10/minute")
async def login(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    client_ip = get_remote_address(request)

    user = db.query(User).filter(
        or_(User.username == form_data.username, User.matricula == form_data.username)
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        log_audit(db, form_data.username, "LOGIN_FAILED", form_data.username,
                  f"IP: {client_ip} — Credenciais inválidas")
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")

    if not user.is_active:
        log_audit(db, user.username, "LOGIN_BLOCKED", user.username, f"IP: {client_ip}")
        raise HTTPException(status_code=403, detail="Usuário inativo. Contate o administrador.")

    token = create_access_token(data={"sub": user.username})
    via = "Matrícula" if user.matricula == form_data.username else "Login"
    log_audit(db, user.username, "LOGIN_SUCCESS", user.username, f"IP: {client_ip} via {via}")

    response = JSONResponse({
        "access_token": token, "token_type": "bearer",
        "role": user.role, "user_full_name": user.full_name,
    })
    set_auth_cookie(response, token)
    return response


@router.post("/api/auth/logout")
async def logout():
    response = JSONResponse({"message": "Logout realizado."})
    clear_auth_cookie(response)
    return response
