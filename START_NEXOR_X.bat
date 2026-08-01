@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)
if not exist .venv (
  echo [NEXOR X] Creating virtual environment...
  %PY% -m venv .venv || goto :error
)
call .venv\Scripts\activate.bat || goto :error
python -m pip install --upgrade pip >nul || goto :error
python -m pip install -e . || goto :error
if not exist .env copy .env.example .env >nul
echo [NEXOR X] Command Center: http://127.0.0.1:8809
python -m nexor_x.main
goto :eof
:error
echo [NEXOR X] Startup failed.
pause
exit /b 1
