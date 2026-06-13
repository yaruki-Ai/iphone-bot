@echo off
REM ============================================================================
REM BUILD_EXE.bat - Construit l'executable Windows unique (iPhoneArbitrageBot.exe)
REM Etapes : venv + dependances Python + build frontend React + PyInstaller.
REM Resultat : dist\iPhoneArbitrageBot.exe (a livrer au client avec un .env).
REM ============================================================================
cd /d "%~dp0"
setlocal

echo [1/5] Creation de l'environnement Python...
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
)

echo [2/5] Installation des dependances Python...
.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller --quiet
if errorlevel 1 (
    echo [ERREUR] Echec de l'installation des dependances Python.
    pause
    exit /b 1
)

echo [3/5] Build du frontend React...
pushd frontend
call npm install --no-fund --no-audit --loglevel=error
call npm run build
popd
if not exist "frontend\dist\index.html" (
    echo [ERREUR] Le build frontend a echoue.
    pause
    exit /b 1
)

echo [4/5] Generation de l'executable (PyInstaller)...
.venv\Scripts\pyinstaller.exe bot.spec --noconfirm
if not exist "dist\iPhoneArbitrageBot.exe" (
    echo [ERREUR] La generation de l'exe a echoue.
    pause
    exit /b 1
)

echo [5/5] Copie du modele de configuration a cote de l'exe...
if not exist "dist\.env" copy ".env.example" "dist\.env" >nul

echo.
echo ============================================================
echo  BUILD TERMINE !
echo  Executable : dist\iPhoneArbitrageBot.exe
echo  N'oubliez pas de completer dist\.env (cles eBay, Discord...).
echo ============================================================
pause
