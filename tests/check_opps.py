"""check_opps.py — Vérifie le filtre anti-prix-absurde sur les opportunités."""
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect("data/iphone_arbitrage.db")
print("Top opportunités FONCTIONNELLES (rentables) :")
for r in c.execute("SELECT modele,prix,roi_estime,score FROM annonces "
                   "WHERE active=1 AND etat='fonctionnel' AND roi_estime>0 "
                   "ORDER BY score DESC LIMIT 8"):
    print(f"   {r[0]} | prix {r[1]}€ | ROI {r[2]}€ | score {r[3]}")
n = c.execute("SELECT COUNT(*) FROM annonces WHERE active=1 AND etat='fonctionnel' "
              "AND roi_estime>0 AND prix<25").fetchone()[0]
print(f"Opportunités fonctionnelles à prix < 25€ (doit être ~0) : {n}")
