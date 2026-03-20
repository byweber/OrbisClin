"""
security.py — Autenticação JWT via httponly cookie (+ bearer token como fallback).

Mudanças:
  - Token JWT em cookie httponly/samesite=lax (não exposto via localStorage/XSS).
  - Bearer token ainda aceito como fallback (API direta, /view?token=, worker).
  - validate_password_complexity() centralizada aqui.
  - require_admin() extraído para reutilização nos routers.
"""
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
import models

settings = get_settings()
SECRET_KEY = settings.get_secret_key()
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

COOKIE_NAME = "orbisclin_session"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/token", auto_error=False)


# ── Senha ─────────────────────────────────────────────────────────────────────

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def validate_password_complexity(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(422, detail={"message": "Senha deve ter no mínimo 8 caracteres."})
    if not any(c.isalpha() for c in password):
        raise HTTPException(422, detail={"message": "Senha deve conter pelo menos uma letra."})
    if not any(c.isdigit() for c in password):
        raise HTTPException(422, detail={"message": "Senha deve conter pelo menos um número."})


# ── Token ─────────────────────────────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")
        return username
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado.")


# ── Extração do token (cookie > bearer > query param) ─────────────────────────

def _extract_token(request: Request, bearer: str | None) -> str:
    if token := request.cookies.get(COOKIE_NAME):
        return token
    if bearer:
        return bearer
    if token := request.query_params.get("token"):
        return token
    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado.",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ── Dependências ──────────────────────────────────────────────────────────────

def get_current_user(
    request: Request,
    bearer: str | None = Depends(_oauth2_bearer),
    db: Session = Depends(get_db),
) -> models.User:
    token = _extract_token(request, bearer)
    username = decode_token(token)
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário inativo.")
    return user

def require_admin(current: models.User = Depends(get_current_user)) -> models.User:
    if current.role != "ADMIN":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Acesso restrito a administradores.")
    return current


# ── Cookie helpers ────────────────────────────────────────────────────────────

def set_auth_cookie(response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,           # ← True em produção com HTTPS
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

def clear_auth_cookie(response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")


# ── Auditoria ─────────────────────────────────────────────────────────────────

def log_audit(db: Session, username: str, action: str, target: str, details: str = "") -> None:
    db.add(models.AuditLog(username=username, action=action, target=target, details=details))
    db.commit()
