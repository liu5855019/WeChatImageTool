@echo off
setlocal
cd /d "%~dp0"

net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Please run this file as administrator.
    echo Right-click it and choose "Run as administrator".
    pause
    exit /b 1
)

echo Relabeling .venv to Medium integrity...
icacls ".venv" /setintegritylevel (OI)(CI)Medium /T /C /Q
echo Relabeling dist to Medium integrity...
icacls "dist" /setintegritylevel (OI)(CI)Medium /T /C /Q

echo.
echo Done. Close this window and double-click WeChatImageTool.exe again.
pause
