@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py -3"
) else (
    set "PYTHON_CMD=python"
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating local virtual environment...
    call %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :fail
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :fail

echo Installing required packages...
python -m pip install --upgrade pip
if errorlevel 1 goto :fail

python -m pip install -r requirements.txt
if errorlevel 1 goto :fail

if not defined OPEN_BROWSER set OPEN_BROWSER=1
echo Starting Sejda At Home...
python app.py
goto :eof

:fail
echo.
echo Could not start the app. Please make sure Python 3 is installed and available on PATH.
pause
exit /b 1
