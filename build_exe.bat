@echo off
cd /d "%~dp0"
echo Installing PyInstaller...
python -m pip install --upgrade pyinstaller
echo.
echo Building the exe...
python -m PyInstaller --onefile --windowed --name "TimeTracker" focus_timer.py
echo.
echo ============================================
echo Done! Find "TimeTracker.exe" in the dist folder
echo ============================================
pause
