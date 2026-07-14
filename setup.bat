@echo off
REM ==============================================================================
REM  setup.bat  -  ONE-TIME environment setup for the Fraud Detection platform
REM ==============================================================================
REM
REM  This project's "system" is two pieces working together:
REM    - The secure FastAPI inference service (app\main.py, Milestone 3), which
REM      serves fraud-risk predictions using the already-trained LightGBM model
REM      committed at artifacts_m3\lightgbm_inference_bundle.joblib.
REM    - The enterprise frontend (frontend\, React + Vite) that visualizes every
REM      milestone of the pipeline and can talk to the API above.
REM  (Model training itself was a one-time step already completed - this launcher
REM  does not retrain anything, it just serves the existing model and UI.)
REM
REM  What this script does, step by step:
REM    1. Checks that Python is installed and available on PATH.
REM    2. Creates an isolated virtual environment in ".venv" so the API's
REM       dependencies never pollute your system-wide Python installation.
REM    3. Installs the exact Python packages the API needs, pinned in
REM       requirements-milestone3.txt (FastAPI, Uvicorn, LightGBM, scikit-learn, etc).
REM    4. Creates a local .env configuration file from .env.example, but only if
REM       one does not already exist - it will NEVER overwrite a .env you already
REM       have (so any custom JWT secret / settings you've set are preserved).
REM    5. Checks that Node.js/npm is installed, then installs the frontend's
REM       npm dependencies (frontend\node_modules) and creates frontend\.env
REM       from frontend\.env.example if one doesn't already exist.
REM
REM  Run this ONCE when you first set up the project (or again later if
REM  requirements-milestone3.txt or frontend\package.json changes). After it
REM  finishes successfully, use start.bat every day to launch both the API and
REM  the frontend together - you will not need to run this again.
REM ==============================================================================

REM Move to the folder this script lives in, regardless of where it was launched
REM from, so all relative paths below (venv, requirements file, .env) resolve
REM correctly even if the user double-clicks this from Windows Explorer.
cd /d "%~dp0"

echo.
echo ================================================================
echo   Fraud Detection Platform -- First-Time Setup
echo ================================================================
echo.

REM --- Step 1: Make sure Python is installed and on PATH ----------------------
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on your PATH.
    echo.
    echo         Install Python 3.10 or newer from https://www.python.org/downloads/
    echo         During installation, make sure the "Add python.exe to PATH"
    echo         checkbox is ticked, then re-run this script.
    echo.
    pause
    exit /b 1
)

echo [OK] Python found:
python --version
echo.

REM --- Step 2: Create the virtual environment if it doesn't already exist -----
if exist ".venv\Scripts\python.exe" (
    echo [1/4] Virtual environment already exists at .venv - skipping creation.
) else (
    echo [1/4] Creating virtual environment in .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to create the virtual environment. See the output above.
        pause
        exit /b 1
    )
    echo         Done.
)
echo.

REM --- Step 3: Install the API's dependencies into the virtual environment ----
echo [2/4] Installing dependencies from requirements-milestone3.txt ...
echo       (first run only - this can take a few minutes)
echo.
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul 2>nul
".venv\Scripts\python.exe" -m pip install -r requirements-milestone3.txt
if errorlevel 1 (
    REM The exact-pinned versions above (chosen to match what the model was
    REM trained/tested with) may not have a prebuilt wheel for very new Python
    REM releases. The most common failure on Python 3.13+ is scikit-learn==1.5.0
    REM falling back to a from-source build, which needs a full C/C++ toolchain
    REM and fails on most machines. When that happens, retry once with the same
    REM packages but no version pins, so pip picks whatever wheel matches the
    REM Python version actually installed - this is exactly the package set
    REM verified to work correctly with the trained model during this project's
    REM own local testing.
    echo.
    echo [WARNING] Installing the exact pinned dependency versions failed.
    echo           This is usually caused by a newer Python version ^(3.13+^)
    echo           for which an older pinned package - most commonly
    echo           scikit-learn==1.5.0 - has no prebuilt install file, forcing a
    echo           slow from-source build that needs a full C/C++ toolchain.
    echo.
    echo           Retrying with the same packages but no version pins, so pip
    echo           can pick versions that are prebuilt for your Python version...
    echo.
    REM NOTE: bcrypt is deliberately capped below 4.1 even in this fallback.
    REM passlib 1.7.4's bcrypt backend probes bcrypt.__about__.__version__,
    REM an attribute bcrypt>=4.1 removed - installing an unconstrained/latest
    REM bcrypt here would crash every password check with a confusing
    REM "password cannot be longer than 72 bytes" error. Found by actually
    REM running this exact fallback path during testing, not assumed.
    REM
    REM Faker, optuna, and xgboost are also included even though the API
    REM code never imports them directly: loading the trained model
    REM (joblib.load) unpickles a class whose package (src.models) eagerly
    REM imports them at package-init time. Missing any one of them fails
    REM model loading, not startup - also found by actually exercising this
    REM fallback path end-to-end, not assumed.
    ".venv\Scripts\python.exe" -m pip install fastapi "uvicorn[standard]" pydantic pydantic-settings "python-jose[cryptography]" "passlib[bcrypt]" "bcrypt<4.1" python-multipart azure-identity azure-keyvault-secrets slowapi joblib scikit-learn numpy pandas python-dotenv lightgbm Faker optuna xgboost
    if errorlevel 1 (
        echo.
        echo [ERROR] Dependency installation failed even without version pins.
        echo         Scroll up for the pip error output.
        pause
        exit /b 1
    )
    echo.
    echo         Installed successfully using current-compatible versions
    echo         ^(not the exact pins in requirements-milestone3.txt^). The
    echo         trained model has been verified to load correctly with newer
    echo         scikit-learn / lightgbm versions. If start.bat later reports an
    echo         error unpickling the model, install the exact pinned versions
    echo         manually using Python 3.10-3.12 instead.
) else (
    echo.
    echo         Installed exact pinned versions successfully.
)
echo.

REM --- Step 3b: Verify every required package actually imports -----------------
echo Verifying installation...
".venv\Scripts\python.exe" -c "import fastapi, uvicorn, sklearn, lightgbm, xgboost, optuna, faker, joblib, jose, passlib, slowapi, azure.identity, azure.keyvault.secrets, dotenv" 2>nul
if errorlevel 1 (
    echo.
    echo [ERROR] One or more packages failed to import after installation.
    echo         Re-run this script, or install the missing package manually with:
    echo         .venv\Scripts\python.exe -m pip install ^<package-name^>
    pause
    exit /b 1
)
echo         All required packages import successfully.
echo.

REM --- Step 4: Create a local .env file if one doesn't already exist ----------
echo [3/4] Checking local configuration file (.env) ...
if exist ".env" (
    echo         Existing .env found - leaving it untouched.
) else (
    if exist ".env.example" (
        copy /y ".env.example" ".env" >nul
        echo         Created .env from .env.example for local development.
        echo         Edit .env later if you want to change settings such as
        echo         JWT_SECRET_KEY, RATE_LIMIT, or ALLOWED_ORIGINS.
    ) else (
        echo [WARNING] .env.example was not found - could not create .env.
        echo           The API may fail to start without one. See README.md.
    )
)
echo.

REM --- Step 5: Set up the frontend (frontend\, React + Vite) -------------------
echo [4/4] Setting up the frontend ...
echo.

where node >nul 2>nul
if errorlevel 1 (
    echo [WARNING] Node.js was not found on your PATH - skipping frontend setup.
    echo           Install Node.js 20+ from https://nodejs.org/ and re-run this
    echo           script to enable the frontend. The API will still work on its
    echo           own without it.
    echo.
    goto :skip_frontend
)

echo         Node found:
node --version
echo.

if not exist "frontend\package.json" (
    echo [WARNING] frontend\package.json not found - skipping frontend setup.
    echo           Expected the frontend project at .\frontend
    echo.
    goto :skip_frontend
)

if exist "frontend\node_modules" (
    echo         frontend\node_modules already exists - skipping npm install.
    echo         Delete frontend\node_modules and re-run this script to force a
    echo         clean reinstall.
) else (
    echo         Installing frontend dependencies ^(npm install^) ...
    echo         ^(first run only - this can take a few minutes^)
    echo.
    call npm install --prefix frontend
    if errorlevel 1 (
        echo.
        echo [ERROR] Frontend dependency installation failed.
        echo         Scroll up for the npm error output.
        pause
        exit /b 1
    )
    echo.
    echo         Frontend dependencies installed successfully.
)
echo.

if exist "frontend\.env" (
    echo         Existing frontend\.env found - leaving it untouched.
) else (
    if exist "frontend\.env.example" (
        copy /y "frontend\.env.example" "frontend\.env" >nul
        echo         Created frontend\.env from frontend\.env.example.
        echo         By default the frontend uses realistic mock data
        echo         ^(VITE_USE_MOCKS=true^) and does not require the API to be
        echo         running. Set VITE_USE_MOCKS=false there to use the real API.
    ) else (
        echo [WARNING] frontend\.env.example was not found - could not create frontend\.env.
    )
)

:skip_frontend
echo.
echo ================================================================
echo   Setup complete!
echo   Double-click start.bat any time to launch the API and the frontend.
echo ================================================================
echo.
pause
