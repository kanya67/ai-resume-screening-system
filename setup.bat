@echo off
echo ================================================
echo   AI Resume Screening System - Setup Script
echo ================================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.9+ from https://python.org
    echo         Make sure to check "Add Python to PATH" during installation!
    pause
    exit /b 1
)

echo [OK] Python found.
echo.
echo [1/3] Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

echo [OK] Virtual environment created.
echo.
echo [2/3] Installing dependencies (this may take a few minutes)...
call venv\Scripts\activate.bat
pip install --upgrade pip --quiet
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install some packages. Check your internet connection.
    pause
    exit /b 1
)

echo.
echo [3/3] Downloading NLTK data...
python -c "import nltk; [nltk.download(r, quiet=True) for r in ['punkt','stopwords','wordnet','averaged_perceptron_tagger','punkt_tab']]"

echo.
echo ================================================
echo   Setup Complete!
echo   Run 'start.bat' to launch the application.
echo ================================================
pause
