"""debug_ebay.py — Diagnostic rapide de la réponse eBay (statut + structure)."""
import asyncio

import httpx

from backend.scraper import antiban


async def main():
    h = antiban.entetes(referer="https://www.ebay.fr/")
    h["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    h["Accept-Language"] = "fr-FR,fr;q=0.9"
    async with httpx.AsyncClient(timeout=30, headers=h, follow_redirects=True) as c:
        await c.get("https://www.ebay.fr/")
        r = await c.get("https://www.ebay.fr/sch/i.html",
                        params={"_nkw": "iphone", "_sop": "10", "_ipg": "60", "LH_BIN": "1"})
    t = r.text
    print("status:", r.status_code, "| len:", len(t))
    print("s-card__title:", t.count("s-card__title"), "| s-item__title:", t.count("s-item__title"))
    print("/itm/:", t.count("/itm/"), "| captcha:", t.lower().count("captcha"))


if __name__ == "__main__":
    asyncio.run(main())
