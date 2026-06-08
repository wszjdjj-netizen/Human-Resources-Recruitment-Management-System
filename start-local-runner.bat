@echo off
chcp 65001 >nul
setlocal
title Local Browser Runner

if not exist "%~dp0backend\app\local_runner\main.py" (
  echo [ERROR] Local runner files were not found.
  echo Please unzip the runner package completely, then run this file again.
  pause
  exit /b 1
)

cd /d "%~dp0backend"
set "REQ_FILE=requirements.txt"
if exist "runner-requirements.txt" set "REQ_FILE=runner-requirements.txt"
set "VENV_DIR=.runner-venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

if not defined UV_CACHE_DIR set "UV_CACHE_DIR=%~dp0.uv-cache"

echo.
echo ========================================
echo  Recruitment Local Browser Runner
echo ========================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:18765/health' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } } catch { exit 1 }" >nul 2>nul
if %ERRORLEVEL%==0 (
  echo Local runner is already running on http://127.0.0.1:18765
  timeout /t 3 >nul
  exit /b 0
)

call :ensure_python
if errorlevel 1 goto :create_failed

if not exist "%VENV_DIR%\.runner-ready" (
  echo Installing local runner dependencies. This may take several minutes on first run...
  call :install_dependencies
  if errorlevel 1 goto :install_failed

  "%PYTHON_EXE%" -m playwright install chromium
  if errorlevel 1 goto :install_failed

  echo ready > "%VENV_DIR%\.runner-ready"
)

echo Starting local runner on http://127.0.0.1:18765
echo Keep this window open while using platform sourcing.
"%PYTHON_EXE%" -m app.local_runner.main
exit /b %ERRORLEVEL%

:ensure_python
if exist "%PYTHON_EXE%" (
  "%PYTHON_EXE%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
  if not errorlevel 1 exit /b 0
  echo Existing runner virtual environment is not usable. Recreating it...
  rmdir /s /q "%VENV_DIR%" >nul 2>nul
)

where uv >nul 2>nul
if not errorlevel 1 (
  echo Creating runner virtual environment with uv...
  uv venv --managed-python --python 3.12 "%VENV_DIR%"
  if not errorlevel 1 (
    "%PYTHON_EXE%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
    if not errorlevel 1 exit /b 0
  )
  echo [WARN] uv could not create a usable runner environment. Trying py/python...
  rmdir /s /q "%VENV_DIR%" >nul 2>nul
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 -m venv "%VENV_DIR%"
  if not errorlevel 1 (
    "%PYTHON_EXE%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
    if not errorlevel 1 exit /b 0
  )
  rmdir /s /q "%VENV_DIR%" >nul 2>nul
)

where python >nul 2>nul
if not errorlevel 1 (
  python -m venv "%VENV_DIR%"
  if not errorlevel 1 (
    "%PYTHON_EXE%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
    if not errorlevel 1 exit /b 0
  )
)

exit /b 1

:install_dependencies
where uv >nul 2>nul
if not errorlevel 1 (
  uv pip install --python "%PYTHON_EXE%" -r "%REQ_FILE%"
  exit /b %ERRORLEVEL%
)

"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 exit /b 1
"%PYTHON_EXE%" -m pip install -r "%REQ_FILE%"
exit /b %ERRORLEVEL%

:create_failed
echo.
echo [ERROR] Python 3.10+ was not found or the virtual environment could not be created.
echo Install Python 3.10+ from https://www.python.org/downloads/ or install uv, then run this file again.
pause
exit /b 1

:install_failed
echo.
echo [ERROR] Failed to install local runner dependencies.
echo Please check your network and Python installation, then run this file again.
pause
exit /b 1
