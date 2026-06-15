"""test_image.py — Vérifie la capture d'image et envoie une alerte avec photo."""
import asyncio
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")

from backend.notifier import discord


async def main():
    c = sqlite3.connect("data/iphone_arbitrage.db")
    c.row_factory = sqlite3.Row
    n = c.execute("SELECT COUNT(*) FROM annonces WHERE image_url IS NOT NULL").fetchone()[0]
    par_plat = c.execute(
        "SELECT plateforme, COUNT(*) FROM annonces WHERE image_url IS NOT NULL GROUP BY plateforme"
    ).fetchall()
    print(f"Annonces avec image : {n}  | par plateforme : {[tuple(r) for r in par_plat]}")

    row = c.execute(
        "SELECT * FROM annonces WHERE image_url IS NOT NULL AND roi_estime > 0 "
        "ORDER BY score DESC LIMIT 1"
    ).fetchone()
    if not row:
        print("Aucune annonce avec image + rentable pour le test.")
        return
    a = dict(row)
    print(f"Test alerte -> {a['modele']} {a.get('stockage') or ''} | "
          f"etat={a['etat']} | image={str(a['image_url'])[:70]}")
    ok = await discord.alerter_opportunite(a)
    print("Alerte envoyée :", ok)


if __name__ == "__main__":
    asyncio.run(main())
