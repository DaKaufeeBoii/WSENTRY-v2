@echo off
REM W-SENTRY laptop A (detector) - one-time setup on a new laptop.
REM Needs: Python 3.11 and Node.js (LTS) installed and on PATH.
REM Double-click this file, or from cmd in the project folder:  setup_laptopA.cmd
REM Then start the demo with:  scripts\run_laptopA.cmd

cd /d "%~dp0"

REM Prefer Python 3.11 (the version these pins were tested on); fall back to python.
set "PY=python"
py -3.11 --version >nul 2>&1 && set "PY=py -3.11"
echo Using: %PY%
%PY% --version || (echo Python not found. Install Python 3.11 and tick "Add to PATH". & pause & exit /b 1)

if not exist ".venv\Scripts\python.exe" (
  echo Creating .venv ...
  %PY% -m venv .venv || (echo venv creation failed & pause & exit /b 1)
)

echo Installing Python packages (torch CUDA build is ~2.5 GB, this takes a while) ...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt || (echo pip install failed & pause & exit /b 1)

echo Installing dashboard packages ...
where npm >nul 2>&1 || (echo Node.js/npm not found. Install Node.js LTS from nodejs.org. & pause & exit /b 1)
call npm ci --prefix frontend || (echo npm ci failed & pause & exit /b 1)

echo Checking the model loads ...
.venv\Scripts\python.exe -c "from src.live.inference import InferenceEngine; InferenceEngine(); print('model OK')" || (echo model check failed & pause & exit /b 1)

echo.
echo Setup done. Start the demo with:  scripts\run_laptopA.cmd
echo (run it once as Administrator so it can add the firewall rules)
pause
