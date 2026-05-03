@echo off
REM Run the Huffman Compression web app from the web folder

echo.
echo ========================================
echo  Huffman Compression Tool - Web Edition
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

echo Python found

echo.
REM Move to this script's directory (web folder)
cd /d "%~dp0"

REM Install dependencies if needed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo Dependencies installed

echo.
echo Starting web server...
echo ========================================
echo  Server running on:
echo  http://localhost:5000
echo.
echo  Open your browser to the URL above
echo  Press CTRL+C to stop
echo ========================================
echo.

python app.py
