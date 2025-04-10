@echo off
echo ==== SetlistGenie Deployment Script for Windows ====
echo This will deploy the application to Cloud Run in the pauliecee-ba4e0 project

REM Check if gcloud is installed
where gcloud >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo Error: Google Cloud SDK (gcloud) is not installed or not in PATH.
    echo Please install it from: https://cloud.google.com/sdk/docs/install
    pause
    exit /b 1
)

REM Verify we're in the right project
for /f "tokens=*" %%a in ('gcloud config get-value project') do set CURRENT_PROJECT=%%a
if not "%CURRENT_PROJECT%"=="pauliecee-ba4e0" (
    echo Switching to pauliecee-ba4e0 project...
    gcloud config set project pauliecee-ba4e0
)

REM Check if service account file exists
if not exist firebase-service-account.json (
    echo Warning: firebase-service-account.json not found.
    echo You'll need to set FIREBASE_ADMIN_CREDENTIALS manually after deployment.
    set /p CONTINUE=Continue anyway? (y/n): 
    if /i not "%CONTINUE%"=="y" exit /b 1
)

REM Check if .env file exists for local vars
if exist .env (
    echo Loading environment variables from .env file...
    for /f "tokens=*" %%a in (.env) do set %%a
    echo Environment variables loaded
) else (
    echo Warning: No .env file found. Using default or empty values.
)

REM Build the container
echo Building container image...
gcloud builds submit --tag gcr.io/pauliecee-ba4e0/setlistgenie

REM Generate a random secret key if not set
if "%FLASK_SECRET_KEY%"=="" (
    echo Generating random Flask secret key...
    for /f "tokens=*" %%a in ('powershell -Command "[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes([System.Guid]::NewGuid()))"') do set FLASK_SECRET_KEY=%%a
)

REM Deploy to Cloud Run with cost-optimized settings
echo Deploying to Cloud Run...
gcloud run deploy setlistgenie ^
  --image gcr.io/pauliecee-ba4e0/setlistgenie ^
  --platform managed ^
  --region us-east1 ^
  --memory 256Mi ^
  --cpu 1 ^
  --min-instances 0 ^
  --max-instances 2 ^
  --set-env-vars "FLASK_SECRET_KEY=%FLASK_SECRET_KEY%" ^
  --set-env-vars "SUPABASE_URL=https://cqlldqgxghuvbtmlaiec.supabase.co" ^
  --set-env-vars "SUPABASE_KEY=%SUPABASE_KEY%"

REM Set Firebase Admin credentials if available
if exist firebase-service-account.json (
    echo Setting Firebase Admin credentials...
    for /f "tokens=*" %%a in ('powershell -Command "$bytes = [System.IO.File]::ReadAllBytes('firebase-service-account.json'); [Convert]::ToBase64String($bytes)"') do set FIREBASE_CREDENTIALS=%%a
    
    gcloud run services update setlistgenie ^
      --update-env-vars "FIREBASE_ADMIN_CREDENTIALS=%FIREBASE_CREDENTIALS%"
    echo Firebase credentials set successfully
) else (
    echo Skipping Firebase credentials setup
)

REM Get the service URL
for /f "tokens=*" %%a in ('gcloud run services describe setlistgenie --platform managed --region us-east1 --format "value(status.url)"') do set SERVICE_URL=%%a

echo ==== Deployment Complete ====
echo SetlistGenie is now available at: %SERVICE_URL%
echo.
echo To map your custom domain (setlist.pauliecee.com), run:
echo gcloud beta run domain-mappings create --service setlistgenie --domain setlist.pauliecee.com --region us-east1
pause
