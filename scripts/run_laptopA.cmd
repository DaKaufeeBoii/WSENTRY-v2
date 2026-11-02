@echo off
REM W-SENTRY demo - laptop A (detector). Starts the live model server and the
REM dashboard, each in its own window. Double-click this file, or from cmd:
REM    scripts\run_laptopA.cmd
REM Close either window to stop that process.

cd /d "%~dp0.."
echo W-SENTRY laptop A
echo   repo: %cd%

REM Pick the project venv python (it has torch); fall back to system python.
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
echo   python: %PY%
echo.

REM One-time firewall rules (need admin; warns if they could not be added).
netsh advfirewall firewall add rule name="W-SENTRY model" dir=in action=allow protocol=TCP localport=8000 >nul 2>&1 || echo   WARN: firewall rule for TCP 8000 not added. Run this file as Administrator once, or laptop B cannot connect.
netsh advfirewall firewall add rule name="W-SENTRY discovery" dir=in action=allow protocol=UDP localport=50505 >nul 2>&1 || echo   WARN: firewall rule for UDP 50505 not added. Run this file as Administrator once, or laptop B cannot connect.

echo Starting detector (model server) on port 8000 ...
start "W-SENTRY detector" cmd /k ""%PY%" scripts\detector_server.py"

echo Starting dashboard on port 5173 ...
start "W-SENTRY dashboard" cmd /k "npm --prefix frontend run dev"

echo.
echo Two windows opened. Open the dashboard at http://localhost:5173
echo Close either window to stop that process.
