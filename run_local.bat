@echo off
echo ==== SetlistGenie Local Development Server ====

REM Check if the .env file exists and create it if it doesn't
if not exist .env (
    echo Creating .env file from example...
    copy .env.example .env
    echo Please edit the .env file with your actual credentials
    pause
    exit /b
)

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate
    echo Installing dependencies...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

REM Run the application
echo Starting SetlistGenie local server...
echo Access the application at http://localhost:8080
python app.py
