@echo off
title Recruitment Frontend
cd /d "%~dp0frontend"

if not exist "package.json" (
  echo [ERROR] Frontend package.json not found in %cd%
  pause
  exit /b 1
)

echo Starting frontend on http://127.0.0.1:5173
cmd /c npm run dev
