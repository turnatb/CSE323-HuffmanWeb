@echo off
REM Stop the Flask server running on port 5000

echo.
echo Stopping server on port 5000...

set "PID="
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5000 ^| findstr LISTENING') do (
    set "PID=%%a"
    goto :kill
)

:kill
if not defined PID (
    echo No process found listening on port 5000.
    goto :done
)

echo Found PID %PID%. Stopping...
taskkill /F /PID %PID% >nul 2>&1
if errorlevel 1 (
    echo Failed to stop PID %PID%.
) else (
    echo Server stopped.
)

:done
echo.
