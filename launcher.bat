@echo off
if not "%1"=="admin" (
    PowerShell -Command "Start-Process cmd -ArgumentList '/c %~s0 admin' -Verb RunAs"
    exit
)
cd /d "%~dp0"
python "voice_trigger_admin.py"
pause