@echo off
setlocal
cd /d "%~dp0"

:: Auto-elevate to administrator (icacls /setintegritylevel requires admin)
net session >nul 2>&1
if errorlevel 1 (
    echo Requesting administrator privileges...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo Building WeChatImageTool.exe...
call .venv\Scripts\activate.bat
python -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name WeChatImageTool ^
    --collect-all customtkinter ^
    --collect-all uiautomation ^
    --collect-all comtypes ^
    --hidden-import win32com ^
    --hidden-import pywin32 ^
    --hidden-import pyautogui ^
    --hidden-import win32clipboard ^
    --hidden-import PIL.ImageGrab ^
    main.py
if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

:: New exe inherits dist folder integrity level; relabel to Medium
:: so it can access the WeChat UI Automation tree.
echo Relabeling dist to Medium integrity level...
icacls "dist" /setintegritylevel (OI)(CI)Medium /T /C /Q
icacls "dist\WeChatImageTool.exe" /setintegritylevel Medium /C /Q

echo.
echo Done. dist\WeChatImageTool.exe is ready.
endlocal
pause