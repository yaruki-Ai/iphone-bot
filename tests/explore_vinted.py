"""explore_vinted.py — Trouve où se cache l'info batterie/stockage dans Vinted."""
import asyncio
import sys

import httpx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.scraper import antiban


def _chercher(obj, motcle, chemin=""):
    """Cherche récursivement les clés/valeurs contenant un mot-clé."""
    trouves = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{chemin}.{k}"
            if motcle in str(k).lower():
                trouves.append((p, str(v)[:80]))
            if isinstance(v, str) and motcle in v.lower():
                trouves.append((p, v[:80]))
            trouves += _chercher(v, motcle, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:5]):
            trouves += _chercher(v, motcle, f"{chemin}[{i}]")
    return trouves


async def main():
    h = antiban.entetes(referer="https://www.vinted.fr/catalog?search_text=iphone")
    h["X-Requested-With"] = "XMLHttpRequest"
    async with httpx.AsyncClient(timeout=20, headers=h, follow_redirects=True) as c:
        await c.get("https://www.vinted.fr")
        rep = await c.get("https://www.vinted.fr/api/v2/catalog/items",
                          params={"search_text": "iphone 13", "per_page": "20", "page": "1"})
        items = rep.json().get("items", [])
        if not items:
            print("aucun item")
            return
        it = items[0]
        print("size_title :", it.get("size_title"))
        print("item_box :", str(it.get("item_box"))[:300])

        # Détail de l'item
        iid = it.get("id")
        rd = await c.get(f"https://www.vinted.fr/api/v2/items/{iid}")
        print(f"\n=== Détail item {iid} : statut {rd.status_code} ===")
        if rd.status_code == 200:
            d = rd.json()
            print("Clés top:", list(d.keys()))
            for mot in ("batt", "attribut", "storage", "capac"):
                r = _chercher(d, mot)
                if r:
                    print(f"\n-- '{mot}' --")
                    for p, v in r[:8]:
                        print(f"   {p} = {v}")


if __name__ == "__main__":
    asyncio.run(main())
