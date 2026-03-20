"""
reset_system.py — Reseta banco e storage para estado limpo.

Correção: birth_date agora incluído no usuário admin criado.
"""
import os
import shutil
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Base, SessionLocal, STORAGE_DIR, engine
from models import User
from security import get_password_hash


def reset_system() -> None:
    print("--- INICIANDO RESET DO SISTEMA ORBISCLIN ---")

    # 1. Storage
    from database import STORAGE_DIR
    print(f"[1/3] Limpando storage: {STORAGE_DIR}")
    if STORAGE_DIR.exists():
        shutil.rmtree(STORAGE_DIR)
        print("      Diretório removido.")
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    print("      Storage recriado.")

    # 2. Banco
    print("[2/3] Resetando banco de dados...")
    Base.metadata.drop_all(bind=engine)
    print("      Tabelas removidas.")
    Base.metadata.create_all(bind=engine)
    print("      Tabelas criadas.")

    # 3. Admin
    print("[3/3] Criando usuário administrador...")
    db = SessionLocal()
    try:
        admin = User(
            username="admin",
            full_name="ADMINISTRADOR",
            matricula="0001",
            birth_date="1990-01-01",   # ← corrigido: campo estava ausente
            role="ADMIN",
            is_active=True,
            hashed_password=get_password_hash("admin123"),
        )
        db.add(admin)
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
