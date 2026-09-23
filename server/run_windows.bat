@echo off
cd /d "%~dp0\.."

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: "python" was not found on PATH.
    echo Install Python from https://www.python.org/downloads/ and check
    echo "Add python.exe to PATH" during install, then run this file again.
    echo.
    pause
    exit /b 1
)

python server\run_local.py

echo.
echo === Done. A full copy of everything above is saved in server\run_log.txt ===
echo === Press any key to close this window ===
pause >nul
