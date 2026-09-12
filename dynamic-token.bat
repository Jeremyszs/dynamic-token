@echo off
setlocal

cd /d "%~dp0"

REM 1. Prefer local venv pythonw if present
if exist "%~dp0venv\Scripts\pythonw.exe" (
    start "" "%~dp0venv\Scripts\pythonw.exe" -m app.main
    exit /b 0
)

REM 2. Prefer hermes-agent venv pythonw if present
if exist "%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\pythonw.exe" (
    start "" "%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\pythonw.exe" -m app.main
    exit /b 0
)

REM 3. Fallback to system pythonw or python
where pythonw >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "" pythonw -m app.main
    exit /b 0
)

where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "" python -m app.main
    exit /b 0
)

echo [ERROR] Python not found. Please install Python 3.10+ and add it to PATH.
pause
exit /b 1
