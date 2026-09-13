@echo off
cd /d "%~dp0"
echo 正在安装打包工具 PyInstaller ...
python -m pip install --upgrade pyinstaller
echo.
echo 正在打包 exe ...
python -m PyInstaller --onefile --windowed --name "专注时间" focus_timer.py
echo.
echo ============================================
echo 完成！在 dist 文件夹里找到 "专注时间.exe"
echo ============================================
pause
