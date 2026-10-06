@echo off
rem PURE ASCII + CRLF - see StartTaikou2.bat for why.
rem FIX3 = clean rebuild of TAIK2W95_big.exe (no post-patch needed anymore):
rem   - 5 debug trampolines removed (they were killing the world map with EIP=0)
rem   - stack-local memset stays 370 (was blown up to CAP=1024)
rem   - debug_log is stdcall ret 4: no add esp,4 after the 4 call sites
rem   - child name render: EDI = row buffer pointer, not row index (AV at row 0)
rem   - kid_panel KD_CODE quota 0x500 -> 0x700 (kd_row got truncated -> AV)
call "%~dp0StartTaikou2.bat" "%~dp0TAIK2W95_big_fix3.exe"
