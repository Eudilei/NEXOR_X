@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title NEXOR X - Diagnostico do Laboratorio Antigo
set "PY=python"
where python >nul 2>&1 || set "PY=py -3"
echo Cole o caminho completo do arquivo positions.jsonl antigo:
set /p "POSITIONS=> "
set "POSITIONS=%POSITIONS:"=%"
if not exist "%POSITIONS%" (
  echo ERRO: arquivo nao encontrado: %POSITIONS%
  pause
  exit /b 1
)
%PY% tools\historical_dataset_bridge.py diagnose-legacy --positions "%POSITIONS%" --output "reports\historical_dataset"
if errorlevel 1 (
  echo Diagnostico terminou com erro.
  pause
  exit /b 1
)
echo.
echo Diagnostico concluido em reports\historical_dataset
pause
