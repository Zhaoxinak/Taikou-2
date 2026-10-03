@echo off
rem ============================================================
rem  Taikou Risshiden II (Win95) launcher
rem
rem  KEEP THIS FILE PURE ASCII WITH CRLF LINE ENDINGS.
rem  cmd.exe reads .bat using the OEM codepage (936 / GBK here).
rem  UTF-8 Chinese comments become mojibake, and the stray bytes can
rem  inject '\' or '"' which silently breaks the quoting of later
rem  lines -> bogus "Missing taikou2_cd.iso" even though it exists.
rem ============================================================
setlocal
cd /d "%~dp0"

set "ISO=%~dp0taikou2_cd.iso"
set "EXE=%~dp0TAIK2W95_zoom.exe"
if not exist "%EXE%" set "EXE=%~dp0TAIK2W95_clean.exe"

if not exist "%EXE%" (
    echo [ERROR] Game executable not found.
    echo         Expected TAIK2W95_zoom.exe or TAIK2W95_clean.exe in this folder.
    pause
    exit /b 1
)

rem ---- virtual CD (optional) -------------------------------------
rem  The ISO is a placeholder image, only needed to satisfy the
rem  game's GetDriveTypeA probe. Mounting needs admin rights and may
rem  fail; that must NOT block the game, so warn and carry on.
if exist "%ISO%" (
    echo Mounting virtual CD...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0mount_cd.ps1" -IsoPath "%ISO%"
    if errorlevel 1 (
        echo [WARN] Could not mount the virtual CD. Starting anyway.
    )
) else (
    echo [WARN] taikou2_cd.iso not found. Starting anyway.
)

echo Starting %~nx0 ...
start "" "%EXE%"
endlocal
