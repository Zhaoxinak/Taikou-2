@echo off
rem ============================================================
rem  mk_page2.bat -- build the PAGING DEMO exe (2 kids per page)
rem
rem  Why a separate build: the shipped page size is 10 kids, and the
rem  biggest child city in the current batch (fam13, castle 66 = Kiyosu)
rem  holds only 6 kids, so no "next/prev page" row is ever created and
rem  the paging code cannot be seen in game. Building with
rem  TKID_PAGE_KIDS=2 makes that same city show 3 pages (2+2+2 kids),
rem  so the nav rows and the PAGE_ROWS / PAGE_NAV counters become
rem  manually testable.
rem
rem  Order matters: .rev\_big_layout.json keeps ONE build's layout, so
rem  each build is verified right after it is made and the SHIPPED
rem  default is rebuilt LAST. End state on disk:
rem    TAIK2W95_big.exe      = shipped default (10 kids per page)
rem    TAIK2W95_big_m5.exe   = same bytes (the name the user launches)
rem    TAIK2W95_big_p2.exe   = paging demo (2 kids per page)
rem    _big_layout.json      = default build (matches TAIK2W95_big.exe)
rem  Verify the demo with TKID_PAGE_KIDS set (child_menu reads it at
rem  import time), otherwise the harness compares a 2-per-page exe
rem  against 10-per-page expectations and reports false failures.
rem
rem  KEEP THIS FILE PURE ASCII WITH CRLF LINE ENDINGS (see
rem  StartTaikou2.bat for the reason). Pass "auto" to skip the pause.
rem ============================================================
setlocal
cd /d "%~dp0"

echo [1/5] demo build: TKID_PAGE_KIDS=2 --^> ..\TAIK2W95_big_p2.exe
set TKID_PAGE_KIDS=2
set TKID_DST=..\TAIK2W95_big_p2.exe
set TKID_EXE=TAIK2W95_big_p2.exe
python build_big.py
if errorlevel 1 exit /b 1

echo [2/5] verify the demo build (static only, game is NOT started)
python verify_children.py
if errorlevel 1 exit /b 1

echo [3/5] default build for the m5 name (10 kids per page)
set TKID_PAGE_KIDS=10
set TKID_DST=..\TAIK2W95_big_m5.exe
set TKID_EXE=TAIK2W95_big_m5.exe
python build_big.py
if errorlevel 1 exit /b 1
python verify_children.py
if errorlevel 1 exit /b 1

echo [4/5] restore shipped default LAST (layout json must match it)
set TKID_DST=..\TAIK2W95_big.exe
set TKID_EXE=TAIK2W95_big.exe
python build_big.py
if errorlevel 1 exit /b 1

echo [5/5] verify the default build
python verify_children.py
if errorlevel 1 exit /b 1

echo.
echo OK   ..\TAIK2W95_big_p2.exe  paging demo  (2 kids per page, Kiyosu pages 3x)
echo OK   ..\TAIK2W95_big_m5.exe  shipped build (10 kids per page)
echo OK   ..\TAIK2W95_big.exe     shipped build (10 kids per page, layout json matches)
echo      Launch the demo with CD mount:  StartTaikou2.bat TAIK2W95_big_p2.exe
if /i "%~1" neq "auto" pause
