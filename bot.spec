# -*- mode: python ; coding: utf-8 -*-
"""
bot.spec — Spécification PyInstaller pour générer l'exécutable Windows unique.

Bundle : backend Python + frontend React buildé (frontend/dist) + schéma SQL.
Le résultat est un seul .exe (mode onefile) que le client double-clique.
La base de données, les logs et le .env restent À CÔTÉ de l'exécutable.

Build :  .venv\\Scripts\\pyinstaller.exe bot.spec
"""

import os
from PyInstaller.utils.hooks import collect_submodules

# --- Données embarquées ---------------------------------------------------
datas = [
    ("backend/database/schema.sql", "backend/database"),
    (".env.example", "."),
]

# Frontend buildé : on embarque chaque fichier de frontend/dist en conservant
# l'arborescence (reconstruite sous frontend/dist dans le bundle).
for racine, _dirs, fichiers in os.walk(os.path.join("frontend", "dist")):
    for f in fichiers:
        chemin = os.path.join(racine, f)
        cible = os.path.relpath(racine, ".")
        datas.append((chemin, cible))

# --- Imports cachés (modules chargés dynamiquement) -----------------------
hiddenimports = (
    collect_submodules("uvicorn")
    + collect_submodules("apscheduler")
    + ["aiosqlite", "anyio", "httpx", "loguru", "dotenv", "bs4", "soupsieve",
       "uvicorn.lifespan.on", "uvicorn.loops.asyncio",
       "uvicorn.protocols.http.h11_impl"]
)

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["playwright", "tkinter", "matplotlib", "numpy", "PIL"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="iPhoneArbitrageBot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=True,          # garde une fenêtre console (logs visibles au client)
    disable_windowed_traceback=False,
    icon="assets/icon.ico",
)
