@echo off
echo(%1| findstr /I Username >nul && echo %GIT_ASKPASS_USER% && exit /b 0
echo %GIT_ASKPASS_PASS%
