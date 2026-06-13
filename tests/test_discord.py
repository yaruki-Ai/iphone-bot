"""
test_discord.py — Test de connexion des deux webhooks Discord.

Envoie UN message de test clairement identifié sur chaque salon (alertes +
rapport) et affiche le code HTTP. But : prouver la connectivité sans inonder
les salons d'alertes fictives.
    .venv\\Scripts\\python.exe -m tests.test_discord
"""

import asyncio

import httpx

from backend.config import settings


async def _tester(nom: str, url: str, contenu: str) -> None:
    """Poste un message simple sur un webhook et affiche le résultat."""
    if not url.startswith("http"):
        print(f"[{nom}] webhook non configuré.")
        return
    payload = {"username": "Arbitrage iPhone (test)", "content": contenu}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            rep = await client.post(url, json=payload)
        etat = "OK" if rep.status_code in (200, 204) else "ECHEC"
        print(f"[{nom}] HTTP {rep.status_code} -> {etat}")
    except httpx.HTTPError as exc:
        print(f"[{nom}] erreur reseau : {exc}")


async def main() -> None:
    """Teste les deux webhooks."""
    await _tester(
        "alertes-opportunites", settings.DISCORD_WEBHOOK_ALERTES,
        "✅ Test de connexion — salon alertes opérationnel. "
        "Les opportunités (score > 70) arriveront ici automatiquement.",
    )
    await _tester(
        "rapport-quotidien", settings.DISCORD_WEBHOOK_RAPPORT,
        "✅ Test de connexion — salon rapport opérationnel. "
        "Le rapport du soir (20h) arrivera ici chaque jour.",
    )


if __name__ == "__main__":
    asyncio.run(main())
