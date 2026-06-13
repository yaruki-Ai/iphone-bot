@echo off
REM ============================================================================
REM START.bat - Lance le bot depuis les sources (sans .exe).
REM Suppose que le venv et les dependances sont installes (sinon lancer BUILD_EXE.bat).
REM ============================================================================
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [ERREUR] Environnement Python introuvable. Lancez d'abord BUILD_EXE.bat.
    pause
    exit /b 1
)
echo Demarrage du bot d'arbitrage iPhone...
echo Le navigateur va s'ouvrir sur http://127.0.0.1:8000
.venv\Scripts\python.exe -m backend.main
pause
