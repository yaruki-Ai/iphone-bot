"""check_batt.py — Vérifie batterie % et stockage récupérés sur Vinted."""
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = sqlite3.connect("data/iphone_arbitrage.db")
tot = c.execute("SELECT COUNT(*) FROM annonces WHERE plateforme='vinted'").fetchone()[0]
batt = c.execute("SELECT COUNT(*) FROM annonces WHERE plateforme='vinted' AND batterie_pct IS NOT NULL").fetchone()[0]
stock = c.execute("SELECT COUNT(*) FROM annonces WHERE plateforme='vinted' AND stockage IS NOT NULL").fetchone()[0]
print(f"Vinted: {tot} annonces | avec batterie %: {batt} | avec stockage: {stock}")
print("Exemples :")
for r in c.execute("SELECT modele,stockage,batterie_pct FROM annonces "
                   "WHERE plateforme='vinted' AND batterie_pct IS NOT NULL LIMIT 6"):
    print(f"   {r[0]} {r[1] or ''} -> batterie {r[2]} %")
