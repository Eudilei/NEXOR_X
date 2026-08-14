@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title NEXOR X - Auditoria da Base Historica
set "PY=python"
where python >nul 2>&1 || set "PY=py -3"
if exist "data_path.txt" set /p "DATA_PATH="<"data_path.txt"
if not defined DATA_PATH (
  echo Cole o caminho da pasta binance_todos_simbolos:
  set /p "DATA_PATH=> "
)
set "DATA_PATH=%DATA_PATH:"=%"
if not exist "%DATA_PATH%" (
  echo ERRO: pasta nao encontrada: %DATA_PATH%
  pause
  exit /b 1
)
>"data_path.txt" echo %DATA_PATH%
%PY% tools\historical_dataset_bridge.py audit --data "%DATA_PATH%" --output "reports\historical_dataset" --workers 4
if errorlevel 1 (
  echo Auditoria terminou com erro.
  pause
  exit /b 1
)
echo.
echo Auditoria concluida em reports\historical_dataset
pause
