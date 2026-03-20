<#
.SYNOPSIS
    Script de Instalação Automatizada do Nexus para Windows.
.DESCRIPTION
    Realiza o setup do ambiente Python, instala dependências, configura firewall
    e cria a persistência via Agendador de Tarefas.
#>

# Força execução como Administrador
if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "Este script precisa de privilégios de Administrador!"
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$VenvDir = "$ScriptDir\venv"
$PythonExe = "$VenvDir\Scripts\python.exe"
$PipExe = "$VenvDir\Scripts\pip.exe"
$ReqFile = "$ScriptDir\requirements.txt"
$EnvFile = "$ScriptDir\.env"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   NEXUS - INSTALAÇÃO AUTOMATIZADA (WIN)  " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Verificar Python Base
Write-Host "`n[1/6] Verificando Python..."
try {
    $sysPython = (Get-Command python).Source
    Write-Host "   Python encontrado: $sysPython" -ForegroundColor Green
} catch {
    Write-Error "Python não encontrado! Instale o Python 3.9+ e adicione ao PATH."
    exit
}

# 2. Criar Ambiente Virtual (Venv)
Write-Host "`n[2/6] Configurando Ambiente Virtual..."
if (!(Test-Path $VenvDir)) {
    Write-Host "   Criando pasta venv..."
    python -m venv $VenvDir
} else {
    Write-Host "   Venv já existe."
}

# 3. Instalar Dependências
Write-Host "`n[3/6] Instalando Bibliotecas..."
if (Test-Path $ReqFile) {
    & $PipExe install --upgrade pip | Out-Null
    & $PipExe install -r $ReqFile
    Write-Host "   Dependências instaladas com sucesso." -ForegroundColor Green
} else {
    Write-Warning "   Arquivo requirements.txt não encontrado!"
}

# 4. Configurar .env (Se não existir)
Write-Host "`n[4/6] Configurando Variáveis de Ambiente..."
if (!(Test-Path $EnvFile)) {
    $EnvContent = @"
# CONFIGURAÇÃO AUTOMÁTICA NEXUS
SECRET_KEY=$( -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 50 | % {[char]$_}) )
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=sqlite:///./database.db
"@
    Set-Content -Path $EnvFile -Value $EnvContent
    Write-Host "   Arquivo .env criado com chave segura gerada." -ForegroundColor Green
} else {
    Write-Host "   Arquivo .env já existe. Mantendo configurações atuais."
}

# 5. Configurar Firewall (Porta 8000)
Write-Host "`n[5/6] Liberando Firewall (Porta 8000)..."
$RuleName = "Nexus_Hospitalar_Web"
Remove-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName $RuleName -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow | Out-Null
Write-Host "   Tráfego liberado na porta 8000." -ForegroundColor Green

# 6. Criar Serviço (Tarefa Agendada)
Write-Host "`n[6/6] Criando Serviço de Inicialização..."
$TaskName = "NexusService"
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "main.py" -WorkingDirectory $ScriptDir
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Description "Servidor Nexus Hospitalar" | Out-Null

Write-Host "   Serviço instalado! O Nexus iniciará automaticamente com o Windows." -ForegroundColor Green

# --- FIM ---
Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "   INSTALAÇÃO CONCLUÍDA COM SUCESSO!      " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Para iniciar agora sem reiniciar o PC, rodando o serviço..."
Start-ScheduledTask -TaskName $TaskName
Write-Host "Acesse: http://localhost:8000" -ForegroundColor Yellow
Write-Host "Pressione qualquer tecla para sair..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")