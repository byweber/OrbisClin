import os
import zipfile
from datetime import datetime

# Configurações
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
MAX_BACKUPS = 7

# Lista Negra: O que NÃO deve entrar no backup
IGNORE_DIRS = {
    "backups",       # Evita recursão (backup do backup)
    "__pycache__",   # Arquivos temporários do Python
    "venv",          # Ambiente virtual (pode ser recriado)
    ".git",          # Histórico de versão (opcional, economiza espaço)
    ".idea",         # Configuração de IDE (JetBrains)
    ".vscode"        # Configuração de IDE (VSCode)
}

IGNORE_EXTENSIONS = {
    ".pyc",          # Bytecode Python
    ".log",          # Logs de execução
    ".tmp"           # Temporários
}

def create_backup():
    """
    Gera um backup FULL (Código + Banco + Storage) 
    e retorna o caminho do arquivo zip gerado.
    """
    print("--- INICIANDO BACKUP COMPLETO DO SISTEMA ---")
    
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    zip_filename = f"nexus_full_structure_{timestamp}.zip"
    zip_path = os.path.join(BACKUP_DIR, zip_filename)

    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Caminha por toda a árvore de diretórios
            for root, dirs, files in os.walk(BASE_DIR):
                # Filtra diretórios ignorados 'in-place' para o os.walk não entrar neles
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                
                for file in files:
                    # Filtra extensões ignoradas
                    if any(file.endswith(ext) for ext in IGNORE_EXTENSIONS):
                        continue
                    
                    file_abs_path = os.path.join(root, file)
                    
                    # Evita tentar zipar o próprio arquivo zip que está sendo criado
                    # (caso o script esteja salvando dentro da mesma árvore)
                    if file_abs_path == zip_path:
                        continue
                    
                    # Calcula o caminho relativo para manter a estrutura de pastas dentro do zip
                    rel_path = os.path.relpath(file_abs_path, BASE_DIR)
                    
                    zipf.write(file_abs_path, arcname=rel_path)
                    
        print(f"Backup criado com sucesso: {zip_path}")
        print(f"Tamanho: {os.path.getsize(zip_path) / (1024*1024):.2f} MB")
        
        # Rotaciona backups antigos
        clean_old_backups()
        
        return zip_path

    except Exception as e:
        print(f"ERRO CRÍTICO no backup: {e}")
        return None

def clean_old_backups():
    try:
        if not os.path.exists(BACKUP_DIR): return
        
        files = []
        for f in os.listdir(BACKUP_DIR):
            if f.endswith(".zip"):
                full_path = os.path.join(BACKUP_DIR, f)
                files.append(full_path)
        
        # Ordena por data (mais antigo primeiro)
        files.sort(key=os.path.getmtime)

        # Remove excedentes
        if len(files) > MAX_BACKUPS:
            to_delete = len(files) - MAX_BACKUPS
            print(f"Removendo {to_delete} backups antigos...")
            for i in range(to_delete):
                try:
                    os.remove(files[i])
                    print(f" - Removido: {os.path.basename(files[i])}")
                except OSError as e:
                    print(f"Erro ao remover {files[i]}: {e}")
                    
    except Exception as e:
        print(f"Erro na limpeza de backups: {e}")

if __name__ == "__main__":
    create_backup()