@echo off
REM W-SENTRY attacker menu - laptop B. Double-click this file, or run it from cmd.
REM It opens the text menu; pick an attack by number.

cd /d "%~dp0"
title W-SENTRY attacker (laptop B)

REM Use py if present, else python.
where py >nul 2>&1
if %errorlevel%==0 (
  py menu.py %*
) else (
  python menu.py %*
)

echo.
pause
