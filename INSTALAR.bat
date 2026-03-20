@echo off
:: Atalho para rodar o setup do Nexus
cd /d "%~dp0"
echo Solicitando permissoes de Administrador...
PowerShell -NoProfile -ExecutionPolicy Bypass -Command "& {Start-Process PowerShell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File ""%~dp0setup_nexus.ps1""' -Verb RunAs}"