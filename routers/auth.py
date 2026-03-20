from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import or_ # Importação Nova
from database import get_db
from models import User
from security import verify_password, create_access_token, log_audit

router = APIRouter()

@router.post("/token")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Alteração: Busca por username OU matrícula
    user = db.query(User).filter(
        or_(
            User.username == form_data.username, 
            User.matricula == form_data.username
        )
    ).first()
    
    ip = request.client.host
    
    # Validação de senha
    if not user or not verify_password(form_data.password, user.hashed_password):
        # Log genérico para não dar dicas se foi user ou senha
        log_audit(db, form_data.username, "LOGIN_FAILED", f"IP: {ip}", "Credenciais inválidas")
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
        
    if not user.is_active:
        log_audit(db, user.username, "LOGIN_BLOCKED", f"IP: {ip}", "Usuário inativo")
        raise HTTPException(status_code=401, detail="Usuário desativado.")
        
    log_audit(db, user.username, "LOGIN_SUCCESS", f"IP: {ip}", "Sessão iniciada via " + ("Matrícula" if user.matricula == form_data.username else "Login"))
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer", "user_full_name": user.full_name, "role": user.role}