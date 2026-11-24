@echo off
setlocal
cd /d "%~dp0"

REM Reuse the working venv if it already exists.
if exist ".venv\Scripts\python.exe" (
    echo Using existing virtual environment.
    call .venv\Scripts\activate.bat
    python -m pip install -r requirements.txt
    goto :done
)

REM Try the py launcher.
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
    if %errorlevel%==0 (
        set "PY=py -3"
        goto :create
    )
)

REM Try python on PATH.
where python >nul 2>nul
if %errorlevel%==0 (
    python -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
    if %errorlevel%==0 (
        set "PY=python"
        goto :create
    )
)

REM Fallback for this machine: Anaconda.
if exist "C:\anaconda\python.exe" (
    set "PY=C:\anaconda\python.exe"
    goto :create
)

echo.
echo [ERROR] Python 3.10+ was not found.
echo Install it from https://www.python.org/downloads/ and tick "Add Python to PATH".
echo.
pause
exit /b 1

:create
echo Creating virtual environment with %PY% ...
%PY% -m venv --system-site-packages .venv
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt

:done
echo.
echo ============================================================
echo  Setup finished. Next steps:
echo    1) python download_data.py
echo    2) python train.py
echo    3) .\run_backend.bat
echo ============================================================
echo.
pause
