REM Stop the command prompt echoing every command so output stays readable.
@echo off
REM Keep environment changes local to this script.
setlocal
REM Change to the folder containing this script so all relative paths resolve correctly.
cd /d "%~dp0"
REM (blank line separates logical blocks)

REM Check that setup created a virtual environment before trying to use it.
if not exist ".venv\Scripts\activate.bat" (
    REM Report that the environment is missing and tell the user what to run.
    echo [ERROR] Virtual environment missing. Run setup.bat first.
    REM Wait for a keypress so an error is visible when the script is double-clicked.
    pause
    REM Exit the script with a failure code so callers can detect the problem.
    exit /b 1
REM Close the missing-environment check block.
)
REM (blank line separates logical blocks)

REM Activate the virtual environment so uvicorn and its dependencies are available.
call .venv\Scripts\activate.bat
REM Tell the user which local address serves the web app.
echo Starting backend at http://127.0.0.1:8000
REM Point the user to the automatically generated interactive API documentation.
echo API docs: http://127.0.0.1:8000/docs
REM Run the app from main.py with auto-reload so code edits take effect without a restart.
python -m uvicorn main:app --reload
REM Keep the console open after the server stops so errors remain visible.
pause
