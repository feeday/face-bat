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
rem Scope proxy bypass to pip installation only; preserve system settings.
setlocal
set "HTTP_PROXY="
set "HTTPS_PROXY="
set "ALL_PROXY="
set "PIP_PROXY="
set "NO_PROXY=*"
set "PIP_CONFIG_FILE=NUL"
set "PIP_INDEX_URL="
set "PIP_EXTRA_INDEX_URL="
".venv\Scripts\python.exe" -m pip install --only-binary=:all: --disable-pip-version-check --index-url https://pypi.tuna.tsinghua.edu.cn/simple --timeout 20 --retries 1 -r requirements.txt
if not errorlevel 1 goto deps_ok
echo Installation failed. Trying official PyPI ...
".venv\Scripts\python.exe" -m pip install --only-binary=:all: --disable-pip-version-check --index-url https://pypi.org/simple --timeout 20 --retries 1 -r requirements.txt
if errorlevel 1 (
    endlocal
    goto fail
)
:deps_ok
endlocal
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
