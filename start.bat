@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo   AI Resume Screening System - Starting...
echo ================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat
echo [OK] Virtual environment activated.

echo [2/3] Ensuring dependencies are installed...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies. Check your internet connection.
    pause
    exit /b 1
)

echo [3/3] Downloading NLTK data...
python -c "import nltk; [nltk.download(r, quiet=True) for r in ['punkt','stopwords','wordnet','averaged_perceptron_tagger','punkt_tab']]"

echo.
echo Starting Flask server...
echo Open your browser at: http://localhost:5000
echo Press Ctrl+C to stop the server.
echo.
start "" "http://localhost:5000"
python app.py
pause
