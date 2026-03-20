"""
reset_system.py — Reseta banco e storage para estado limpo.
Localização: raiz do projeto.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import Base, SessionLocal, STORAGE_DIR, engine
from app.core.models import User
from app.core.security import get_password_hash


def reset_system() -> None:
    print("--- INICIANDO RESET DO SISTEMA ORBISCLIN ---")

    print(f"[1/3] Limpando storage: {STORAGE_DIR}")
    if STORAGE_DIR.exists():
        shutil.rmtree(STORAGE_DIR)
        print("      Diretório removido.")
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    print("      Storage recriado.")

    print("[2/3] Resetando banco de dados...")
    Base.metadata.drop_all(bind=engine)
    print("      Tabelas removidas.")
    Base.metadata.create_all(bind=engine)
    print("      Tabelas criadas.")

    print("[3/3] Criando usuário administrador...")
    db = SessionLocal()
    try:
        db.add(User(
            username="admin",
            full_name="ADMINISTRADOR",
            matricula="0001",
            birth_date="1990-01-01",
            role="ADMIN",
            is_active=True,
            hashed_password=get_password_hash("admin123"),
        ))
        db.commit()
        print("      Usuário 'admin' criado.")
    except Exception as e:
        print(f"      Erro: {e}")
    finally:
        db.close()

    print("\n--- RESET CONCLUÍDO ---")
    print("Login: admin | Senha: admin123")
    print("⚠️  Altere a senha imediatamente após o primeiro acesso.")
    print("-" * 40)


if __name__ == "__main__":
    confirm = input("⚠️  ATENÇÃO: Apagará TODOS os dados. Digite 'RESET' para confirmar: ")
    if confirm.strip() == "RESET":
        reset_system()
    else:
        print("Operação cancelada.")
