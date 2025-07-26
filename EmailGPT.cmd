@echo off
 title Email GPT
cd /d "%~dp0"
call .venv\Scripts\activate.bat
start "" /b cmd /c "timeout /t 1 >nul && start http://127.0.0.1:5001/"
python backend/api_server.py
if %ERRORLEVEL% neq 0 (
    pause
)
EXIT /B %ERRORLEVEL%