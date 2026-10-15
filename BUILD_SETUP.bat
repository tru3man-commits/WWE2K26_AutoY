@echo off
setlocal
cd /d "%~dp0"
py -3 build.py --setup
if errorlevel 1 goto failed
echo Setup build completed.
pause
exit /b 0
:failed
echo BUILD FAILED. Read the error above; do not distribute an older output.
pause
exit /b 1
