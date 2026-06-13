"""check_titres.py — Affiche des titres réels en base pour vérifier le filtre accessoires."""
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect("data/iphone_arbitrage.db")
print("--- Annonces CASSÉES (par score) ---")
for r in c.execute("SELECT score, modele, titre FROM annonces WHERE etat='casse' ORDER BY score DESC LIMIT 15"):
    print(f"  [{r[0]}] {r[1]} :: {r[2][:65]}")
print("\n--- Annonces FONCTIONNELLES (échantillon) ---")
for r in c.execute("SELECT modele, titre FROM annonces WHERE etat='fonctionnel' LIMIT 10"):
    print(f"  {r[0]} :: {r[1][:65]}")
