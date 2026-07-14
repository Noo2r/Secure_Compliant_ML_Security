@echo off
REM ==============================================================================
REM  start.bat  -  Daily-use, one-click launcher for the whole Fraud Detection
REM  platform: the secure FastAPI inference API AND the frontend, together.
REM ==============================================================================
REM
REM  Double-click this file to start the whole system. It will:
REM    1. Verify setup.bat has already been run for both the API (.venv) and
REM       the frontend (frontend\node_modules).
REM    2. Start the secure FastAPI inference service with Uvicorn on
REM       http://127.0.0.1:8000, streaming its logs in THIS window.
REM    3. Start the frontend's Vite dev server on http://localhost:5173 in a
REM       SECOND window (a new console), so both sets of logs stay visible
REM       and readable at the same time.
REM    4. Automatically open the frontend in your browser once both are up.
REM    5. Press CTRL+C in this window (or just close it) to stop the API.
REM       Close the second "SecureML Frontend" window to stop the frontend.
REM
REM  First time using this project? Run setup.bat once before using this script.
REM ==============================================================================

REM Always run from the folder this script lives in, so it works no matter
REM where it's launched from (double-click, shortcut, another directory, etc).
cd /d "%~dp0"

echo.
echo ================================================================
echo   Fraud Detection Platform -- Starting
echo ================================================================
echo.

REM --- Step 1: Make sure setup.bat has been run for the backend ----------------
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No virtual environment found at .venv
    echo.
    echo         This looks like your first time running the project.
    echo         Please double-click setup.bat first ^(one-time step^), then
    echo         run start.bat again.
    echo.
    pause
    exit /b 1
)

REM --- Step 2: Make sure local backend configuration exists ---------------------
if not exist ".env" (
    echo [ERROR] No .env configuration file found.
    echo.
    echo         Please run setup.bat first - it creates .env for you
    echo         automatically from .env.example.
    echo.
    pause
    exit /b 1
)

REM --- Step 3: Sanity-check the trained model artifact is present --------------
if not exist "artifacts_m3\lightgbm_inference_bundle.joblib" (
    echo [WARNING] Trained model artifact not found:
    echo           artifacts_m3\lightgbm_inference_bundle.joblib
    echo.
    echo           The API will still start, but ModelService will fall back
    echo           to a placeholder scorer instead of the real LightGBM model.
    echo.
)

REM --- Step 4: Check the frontend was set up, and start it in its own window ---
set "FRONTEND_READY=0"
if exist "frontend\node_modules" (
    if exist "frontend\package.json" (
        set "FRONTEND_READY=1"
    )
)

if "%FRONTEND_READY%"=="1" (
    echo Starting frontend at:    http://localhost:5173   ^(new window, opens automatically^)
    start "SecureML Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"
) else (
    echo [WARNING] Frontend is not set up ^(frontend\node_modules missing^).
    echo           Run setup.bat first to install its dependencies. Continuing
    echo           with the API only.
    echo.
)

echo Starting server at:      http://127.0.0.1:8000
echo Interactive API docs at: http://127.0.0.1:8000/docs
echo.
echo Demo login ^(local development only^):
echo     username: svc-ml-engineer
echo     password: CHANGE_ME_IN_PRODUCTION
echo.
echo Press CTRL+C in this window to stop the API.
if "%FRONTEND_READY%"=="1" echo Close the "SecureML Frontend" window to stop the frontend.
echo ----------------------------------------------------------------
echo.

REM --- Step 5: Open the frontend (or the API docs as a fallback) automatically -
REM     Runs in a separate background command so it doesn't block Uvicorn's log
REM     output below. The delay gives both dev servers time to bind their ports.
if "%FRONTEND_READY%"=="1" (
    start "" cmd /c "timeout /t 4 /nobreak >nul & start "" http://localhost:5173"
) else (
    start "" cmd /c "timeout /t 3 /nobreak >nul & start "" http://127.0.0.1:8000/docs"
)

REM --- Step 6: Launch the API server in THIS window -----------------------------
REM     Running it in the foreground (not a new window) means all of Uvicorn's
REM     request logs and any errors are always visible right here.
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

echo.
echo ----------------------------------------------------------------
echo   API server stopped.
if "%FRONTEND_READY%"=="1" echo   ^(The frontend window, if still open, keeps running independently.^)
echo ----------------------------------------------------------------
pause
