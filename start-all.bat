@echo off
cd /d "%~dp0"

start "Recruitment Backend" cmd /k "%~dp0start-backend.bat"
start "Recruitment Frontend" cmd /k "%~dp0start-frontend.bat"
start "Local Browser Runner" cmd /k "%~dp0start-local-runner.bat"

echo Started backend, frontend, and local runner in separate windows.
