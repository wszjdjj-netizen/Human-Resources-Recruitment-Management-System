@echo off
title Recruitment Backend
cd /d "%~dp0backend"

if not exist ".venv\Scripts\uvicorn.exe" (
  echo [ERROR] Backend virtual environment not found: %cd%\.venv\Scripts\uvicorn.exe
  pause
  exit /b 1
)

echo Starting backend on http://127.0.0.1:8000
".venv\Scripts\uvicorn.exe" app.main:app --reload --port 8000 --env-file .env
