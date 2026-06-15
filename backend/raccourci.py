"""
raccourci.py — Crée automatiquement un raccourci sur le Bureau (Windows, mode .exe).

Au premier lancement de l'exécutable, un raccourci « Arbitrage iPhone » (avec
l'icône) est posé sur le Bureau du client, pour qu'il puisse relancer l'app d'un
clic. Ne s'exécute qu'une fois (fichier témoin) et uniquement en mode .exe.
"""

import os
import subprocess
import sys

from backend.config import settings
from backend.logger import log

CREATE_NO_WINDOW = 0x08000000  # lance PowerShell sans fenêtre visible


def creer_raccourci_bureau() -> None:
    """Pose un raccourci sur le Bureau au 1er lancement (no-op si déjà fait)."""
    # Uniquement en exécutable Windows.
    if not getattr(sys, "frozen", False) or sys.platform != "win32":
        return

    marqueur = settings.DOSSIER_DATA / ".raccourci_cree"
    if marqueur.exists():
        return  # déjà créé une fois, on ne refait rien

    exe = sys.executable.replace("'", "''")
    dossier = os.path.dirname(sys.executable).replace("'", "''")
    script = (
        "$ErrorActionPreference='SilentlyContinue';"
        "$d=[Environment]::GetFolderPath('Desktop');"
        "$l=Join-Path $d 'Arbitrage iPhone.lnk';"
        "if(-not (Test-Path $l)){"
        "$w=New-Object -ComObject WScript.Shell;"
        "$s=$w.CreateShortcut($l);"
        f"$s.TargetPath='{exe}';"
        f"$s.WorkingDirectory='{dossier}';"
        f"$s.IconLocation='{exe},0';"
        "$s.Description='Arbitrage iPhone';"
        "$s.Save()}"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script],
            creationflags=CREATE_NO_WINDOW, timeout=25,
        )
        marqueur.write_text("ok", encoding="utf-8")
        log.info("Raccourci Bureau créé.")
    except Exception as exc:  # ne jamais bloquer le démarrage pour ça
        log.warning(f"Création du raccourci Bureau impossible : {exc}")
