@echo off
chcp 65001 >nul
setlocal
title Register Recruitment Runner Protocol

set "SCRIPT=%~dp0start-local-runner.bat"
set "REGISTER_PS1=%~dp0register-runner-protocol.ps1"

if not exist "%SCRIPT%" (
  echo [ERROR] start-local-runner.bat was not found.
  echo Please keep this file in the same folder as start-local-runner.bat.
  pause
  exit /b 1
)

if not exist "%REGISTER_PS1%" (
  echo [ERROR] register-runner-protocol.ps1 was not found.
  echo Please unzip the runner package completely, then run this file again.
  pause
  exit /b 1
)

echo Registering recruitment-runner:// protocol for current Windows user...
powershell -NoProfile -ExecutionPolicy Bypass -File "%REGISTER_PS1%" "%SCRIPT%"

if errorlevel 1 (
  echo [ERROR] Failed to register protocol.
  pause
  exit /b 1
)

echo.
echo Done. Protocol was registered:
reg query "HKCU\Software\Classes\recruitment-runner\shell\open\command" /ve
echo.
echo Important:
echo - This file only registers the browser protocol.
echo - To actually start the runner, double-click start-local-runner.bat,
echo   or click "一键唤起执行器" in the website after registration.
pause
