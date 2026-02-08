@echo off
title Vidiolingua Launcher
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
cd /d "%ROOT%"

REM Use project venv if it exists (avoids conflicts with other apps like langflow)
if exist "%ROOT%\.venv\Scripts\python.exe" (
    set "PY_CMD=%ROOT%\.venv\Scripts\python.exe"
    set "PIP_CMD=%ROOT%\.venv\Scripts\pip.exe"
    set "UVICORN_CMD=%ROOT%\.venv\Scripts\uvicorn.exe"
) else (
    set "PY_CMD=python"
    set "PIP_CMD=pip"
    set "UVICORN_CMD=uvicorn"
)

echo Starting Vidiolingua...
echo.

REM Start backend in a new window
start "Vidiolingua Backend" cmd /k "cd /d ""%ROOT%"" && ""%PIP_CMD%"" install -r requirements.txt -q && echo. && echo Backend: http://localhost:8000 && echo. && ""%PY_CMD%"" -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"

REM Wait for backend to begin
timeout /t 3 /nobreak >nul

REM Start frontend in a new window
start "Vidiolingua Frontend" cmd /k "cd /d ""%ROOT%\frontend-next"" && npm run dev"

REM Wait for frontend to be ready, then open browser
timeout /t 10 /nobreak >nul
start http://localhost:3000

echo.
echo Two windows opened: Backend and Frontend.
echo Browser opened to http://localhost:3000
echo Close the Backend and Frontend windows to stop the app.
echo.
pause
