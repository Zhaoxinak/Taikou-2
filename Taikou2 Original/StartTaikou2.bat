@echo off
cd /d "%~dp0"

set "ISO=%~dp0taikou2_cd.iso"
set "EXE=%~dp0TAIK2W95.exe"

if not exist "%ISO%" (
    echo Missing taikou2_cd.iso
    pause
    exit /b 1
)

if not exist "%EXE%" (
    echo Missing TAIK2W95.exe
    pause
    exit /b 1
)

echo Mounting virtual CD...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0mount_cd.ps1" -IsoPath "%ISO%"
if errorlevel 1 (
    echo Failed to mount virtual CD. Try running as Administrator.
    pause
    exit /b 1
)

echo Starting Taikou Risshiden II...
start "" "%EXE%"
