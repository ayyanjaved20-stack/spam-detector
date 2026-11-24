@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment missing. Run setup.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
echo Starting backend at http://127.0.0.1:8000
echo API docs: http://127.0.0.1:8000/docs
python -m uvicorn main:app --reload
pause
