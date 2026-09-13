@echo off
cd /d "%~dp0"
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw focus_timer.py
) else (
    python focus_timer.py
)
