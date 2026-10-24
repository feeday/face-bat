@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
if exist ".venv\Scripts\python.exe" goto install
py -3.11 -c "import sys; assert sys.maxsize > 2**32" >nul 2>&1
if not errorlevel 1 (
    py -3.11 -m venv .venv
    goto check
)
py -3.12 -c "import sys; assert sys.maxsize > 2**32" >nul 2>&1
if not errorlevel 1 (
    py -3.12 -m venv .venv
    goto check
)
python -c "import sys; assert (3,10) <= sys.version_info[:2] <= (3,12) and sys.maxsize > 2**32" >nul 2>&1
if errorlevel 1 (
    echo Please install Python 3.11 64-bit and enable Add Python to PATH.
    echo https://www.python.org/downloads/windows/
    pause
    exit /b 1
)
python -m venv .venv
:check
if not exist ".venv\Scripts\python.exe" goto fail
:install
if exist ".venv\installed-v1.ok" goto run
echo Installing packages into isolated .venv ...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -c "import flask, waitress, cv2, numpy, PIL"
if errorlevel 1 goto fail
type nul > ".venv\installed-v1.ok"
:run
".venv\Scripts\python.exe" app.py
if errorlevel 1 goto fail
exit /b 0
:fail
echo.
echo Failed. Read the error above. Fix network or Python, then run again.
echo If environment is damaged, delete only the .venv folder and retry.
pause
exit /b 1
