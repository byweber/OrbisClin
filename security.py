import os
import re
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from database import get_db
from models import User, AuditLog

# Configuração de Ambiente
SECRET_KEY = os.getenv("SECRET_KEY", "hmsj_secret_2025")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 600))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- CONFIGURAÇÃO DE LOGS (COM ROTAÇÃO) ---
# Evita que o arquivo nexus.log cresça infinitamente
logger = logging.getLogger("Nexus")
logger.setLevel(logging.INFO)

# Handler para rotação: Max 5MB por arquivo, mantém últimos 3 backups
handler = RotatingFileHandler("nexus.log", maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
# -------------------------------------------

def verify_password(plain, hashed): return pwd_context.verify(plain, hashed)
def get_password_hash(password): return pwd_context.hash(password)

def validate_password_complexity(password: str):
    if len(password) < 8: return False
    if not re.search(r"[a-zA-Z]", password): return False
    if not re.search(r"\d", password): return False
    return True

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError: raise HTTPException(status_code=401, detail="Token inválido")
    user = db.query(User).filter(User.username == username).first()
    if user is None: raise HTTPException(status_code=401, detail="Usuário não encontrado")
    if not user.is_active: raise HTTPException(status_code=401, detail="Usuário desativado.")
    return user

def log_audit(db: Session, username: str, action: str, target: str = None, details: str = None):
    try:
        log_entry = AuditLog(username=username, action=action, target=target, details=details)
        db.add(log_entry); db.commit()
    except Exception as e: logger.error(f"FALHA AUDIT: {e}")