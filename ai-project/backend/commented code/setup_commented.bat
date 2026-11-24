REM Stop the command prompt echoing every command so the output stays readable.
@echo off
REM Keep environment changes local to this script so they do not leak into the shell.
setlocal
REM Change to the folder containing this script so every relative path resolves correctly.
cd /d "%~dp0"
REM (blank line separates logical blocks)

REM Note for readers: the next block reuses a virtual environment that already exists.
REM Reuse the working venv if it already exists.
REM Check whether a working Python interpreter exists inside the virtual environment.
if exist ".venv\Scripts\python.exe" (
    REM Tell the user that no new environment needs to be created.
    echo Using existing virtual environment.
    REM Activate that existing environment so pip installs into it.
    call .venv\Scripts\activate.bat
    REM Install or refresh every declared dependency from the requirements file.
    python -m pip install -r requirements.txt
    REM Skip environment creation and jump straight to the final instructions.
    goto :done
REM Close the existing-environment block.
)
REM (blank line separates logical blocks)

REM Note for readers: first try the Windows Python launcher.
REM Try the py launcher.
REM Look for the py launcher on PATH while hiding the search output.
where py >nul 2>nul
REM Proceed only if the launcher was found.
if %errorlevel%==0 (
    REM Verify the launcher can start Python 3.10 or newer, suppressing all output.
    py -3 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
    REM Proceed only if that version check passed.
    if %errorlevel%==0 (
        REM Remember the launcher command in a variable for environment creation later.
        set "PY=py -3"
        REM Jump to the shared environment creation block.
        goto :create
    REM Close the version check block.
    )
REM Close the launcher found block.
)
REM (blank line separates logical blocks)

REM Note for readers: next try python on PATH.
REM Try python on PATH.
REM Look for a python executable on PATH while hiding the search output.
where python >nul 2>nul
REM Proceed only if that python executable was found.
if %errorlevel%==0 (
    REM Verify that python is version 3.10 or newer, suppressing all output.
    python -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
    REM Proceed only if that version check passed.
    if %errorlevel%==0 (
        REM Remember the plain python command in a variable for environment creation later.
        set "PY=python"
        REM Jump to the shared environment creation block.
        goto :create
    REM Close the version check block.
    )
REM Close the python found block.
)
REM (blank line separates logical blocks)

REM Note for readers: fall back to the Anaconda install present on this machine.
REM Fallback for this machine: Anaconda.
REM Check the known Anaconda location as a last resort.
if exist "C:\anaconda\python.exe" (
    REM Store that Anaconda interpreter as the Python command to use.
    set "PY=C:\anaconda\python.exe"
    REM Jump to the shared environment creation block.
    goto :create
REM Close the Anaconda fallback block.
)
REM (blank line separates logical blocks)

REM Print a blank line to visually separate the error message.
echo.
REM Report that no suitable Python installation was found.
echo [ERROR] Python 3.10+ was not found.
REM Give the user the download link and the PATH setup instruction.
echo Install it from https://www.python.org/downloads/ and tick "Add Python to PATH".
REM Print another blank line after the error message.
echo.
REM Wait for a keypress so the message stays visible when double-clicked.
pause
REM Exit the script with a failure code so callers can detect the problem.
exit /b 1
REM (blank line separates logical blocks)

REM Label the shared environment creation block used by each detected Python.
:create
REM Show which interpreter will create the environment.
echo Creating virtual environment with %PY% ...
REM Create the virtual environment, allowing access to installed system packages.
%PY% -m venv --system-site-packages .venv
REM Activate the newly created environment so pip targets it.
call .venv\Scripts\activate.bat
REM Install all project dependencies into the new environment.
python -m pip install -r requirements.txt
REM (blank line separates logical blocks)

REM Label the common finishing section reached from every success path.
:done
REM Print a blank line before the next steps.
echo.
REM Draw a visual separator line in the console output.
echo ============================================================
REM Announce that setup completed successfully.
echo  Setup finished. Next steps:
REM Instruct the user to download the training datasets first.
echo    1) python download_data.py
REM Instruct the user to train the model second.
echo    2) python train.py
REM Instruct the user to start the backend last.
echo    3) .\run_backend.bat
REM Draw a closing separator line.
echo ============================================================
REM Print a blank line after the instructions.
echo.
REM Hold the console window open so the student can read the next steps.
pause
