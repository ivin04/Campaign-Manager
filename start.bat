@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo No se ha encontrado el entorno virtual.
  echo Ejecuta primero:
  echo python -m venv .venv
  echo .venv\Scripts\activate
  echo pip install -r requirements.txt
  pause
  exit /b 1
)
echo Iniciando D-D Campaign Manager...
".venv\Scripts\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 8765
pause
