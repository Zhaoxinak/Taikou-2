@echo off
rem 太阁2 常驻崩溃监控器 —— 双击后挂着别关, 然后正常开游戏; 崩了看 .rev\tkmon.log
cd /d "%~dp0"
"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe" tkmon.py
pause
