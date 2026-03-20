#!/bin/bash

# ==========================================
#   NEXUS - INSTALAÇÃO AUTOMATIZADA (LINUX)
# ==========================================

# 1. Verificação de Superusuário
if [ "$EUID" -ne 0 ]; then
  echo "❌ Por favor, execute como root (sudo ./install_nexus.sh)"
  exit 1
fi

# Detecta o usuário real (que chamou o sudo) para definir permissões corretas
REAL_USER=$SUDO_USER
if [ -z "$REAL_USER" ]; then
  REAL_USER=$(whoami)
fi

APP_DIR=$(pwd)
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="nexus"

echo "--- INICIANDO SETUP DO NEXUS ---"
echo "📂 Diretório de Instalação: $APP_DIR"
echo "👤 Usuário do Serviço: $REAL_USER"

# 2. Atualizar Sistema e Instalar Dependências do Python
echo -e "\n[1/6] Instalando dependências do sistema..."
apt-get update -qq
apt-get install -y python3-venv python3-pip ufw acl -qq
echo "✅ Dependências instaladas."

# 3. Configurar Ambiente Virtual
echo -e "\n[2/6] Criando Ambiente Virtual (Venv)..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    # Ajusta permissões para o usuário real não perder acesso
    chown -R $REAL_USER:$REAL_USER "$VENV_DIR"
    echo "✅ Venv criado."
else
    echo "ℹ️  Venv já existe."
fi

# 4. Instalar Bibliotecas Python
echo -e "\n[3/6] Instalando Bibliotecas Python..."
if [ -f "requirements.txt" ]; then
    sudo -u $REAL_USER "$VENV_DIR/bin/pip" install -r requirements.txt --quiet
    echo "✅ Bibliotecas instaladas."
else
    echo "⚠️  ERRO: requirements.txt não encontrado!"
    exit 1
fi

# 5. Configurar .env Seguro
echo -e "\n[4/6] Configurando Variáveis (.env)..."
ENV_FILE="$APP_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    # Gera uma chave secreta forte usando OpenSSL
    SECRET=$(openssl rand -hex 32)
    
    cat > "$ENV_FILE" <<EOF
# CONFIGURAÇÃO AUTOMÁTICA NEXUS
SECRET_KEY=$SECRET
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=sqlite:///./database.db
EOF
    chown $REAL_USER:$REAL_USER "$ENV_FILE"
    chmod 600 "$ENV_FILE" # Apenas o dono lê
    echo "✅ Arquivo .env criado com chave segura."
else
    echo "ℹ️  Arquivo .env já existe. Mantendo atual."
fi

# 6. Configurar Firewall (UFW)
echo -e "\n[5/6] Configurando Firewall..."
if command -v ufw > /dev/null; then
    ufw allow 8000/tcp > /dev/null
    echo "✅ Porta 8000 liberada no UFW."
else
    echo "⚠️  UFW não encontrado, verifique seu firewall manualmente."
fi

# 7. Criar Serviço Systemd
echo -e "\n[6/6] Criando Serviço Nexus (Systemd)..."
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Nexus - Servidor de Repositório Clínico
After=network.target

[Service]
User=$REAL_USER
Group=$REAL_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Recarrega e Inicia
systemctl daemon-reload
systemctl enable $SERVICE_NAME --now

echo -e "\n=========================================="
echo "   INSTALAÇÃO CONCLUÍDA COM SUCESSO!      "
echo "=========================================="
echo "Status do Serviço:"
systemctl status $SERVICE_NAME --no-pager | head -n 10

echo -e "\n👉 Acesse: http://$(hostname -I | awk '{print $1}'):8000"