import os
import shutil
import sys
from sqlalchemy.orm import Session

# Garante que o Python encontre os módulos locais
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, Base, SessionLocal, STORAGE_DIR
from models import User, Patient, ExamSession, ExamFile, AuditLog
from security import get_password_hash

def reset_system():
    print("--- INICIANDO RESET DO SISTEMA NEXUS ---")

    # 1. LIMPEZA DE ARQUIVOS (STORAGE)
    print(f"[1/3] Limpando diretório de arquivos: {STORAGE_DIR}")
    if os.path.exists(STORAGE_DIR):
        try:
            shutil.rmtree(STORAGE_DIR)
            print("      Diretório antigo removido.")
        except Exception as e:
            print(f"      Erro ao remover diretório: {e}")
    
    # Recria a pasta vazia
    os.makedirs(STORAGE_DIR, exist_ok=True)
    print("      Diretório de storage recriado.")

    # 2. LIMPEZA DO BANCO DE DADOS
    print("[2/3] Resetando Banco de Dados (SQLite)...")
    try:
        # Dropa todas as tabelas
        Base.metadata.drop_all(bind=engine)
        print("      Tabelas antigas excluídas.")
        
        # Cria todas as tabelas novamente
        Base.metadata.create_all(bind=engine)
        print("      Novas tabelas criadas.")
    except Exception as e:
        print(f"      Erro no banco de dados: {e}")
        return

    # 3. CRIAÇÃO DE USUÁRIO PADRÃO
    print("[3/3] Criando Usuário Administrador Padrão...")
    db: Session = SessionLocal()
    try:
        # Senha "admin123" atende aos requisitos de complexidade (Letra + Número + 8 chars)
        admin_user = User(
            username="admin",
            full_name="ADMINISTRADOR",
            matricula="0001",
            role="ADMIN",
            is_active=True,
            hashed_password=get_password_hash("admin123") 
        )
        
        db.add(admin_user)
        db.commit()
        print("      Usuário 'admin' criado com sucesso.")
        
    except Exception as e:
        print(f"      Erro ao criar usuário: {e}")
    finally:
        db.close()

    print("\n--- RESET CONCLUÍDO ---")
    print("Acesse o sistema com:")
    print("Usuário: admin")
    print("Senha:   admin123")
    print("-----------------------")

if __name__ == "__main__":
    # Confirmação de segurança para evitar acidentes em produção
    confirm = input("ATENÇÃO: Isso apagará TODOS os dados e arquivos. Digite 'RESET' para confirmar: ")
    if confirm == "RESET":
        reset_system()
    else:
        print("Operação cancelada.")