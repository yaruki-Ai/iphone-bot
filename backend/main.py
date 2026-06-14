"""
main.py — Point d'entrée FastAPI du bot d'arbitrage iPhone.

Expose l'API REST (marché, opportunités, stock, historique, prédictions,
alertes, scan manuel), sert le frontend React buildé (mode .exe / production),
initialise la base, démarre le scheduler et ouvre le navigateur au lancement.
"""

import threading
import webbrowser
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.analysis import market, opportunity, prediction
from backend.config import settings
from backend.database.db import execute, fetch_all, fetch_one, maintenant_iso
from backend.logger import log
from backend.models import HistoriqueCreate, StockCreate, StockUpdate, VenteCreate
from backend.scheduler import arreter as arreter_scheduler
from backend.scheduler import demarrer as demarrer_scheduler
from backend.scraper import simulator
from backend.scraper.runner import scan_complet


# ---------------------------------------------------------------------------
# Utilitaires de calcul (marge réelle, délai de revente)
# ---------------------------------------------------------------------------
def _to_date(valeur: str | None) -> datetime | None:
    """Convertit une chaîne ISO ou 'YYYY-MM-DD' en datetime (ou None)."""
    if not valeur:
        return None
    try:
        return datetime.fromisoformat(valeur)
    except ValueError:
        try:
            return datetime.strptime(valeur, "%Y-%m-%d")
        except ValueError:
            return None


def _delai_jours(date_achat: str, date_vente: str) -> float | None:
    """Nombre de jours entre l'achat et la vente."""
    a, v = _to_date(date_achat), _to_date(date_vente)
    if not a or not v:
        return None
    return round((v - a).total_seconds() / 86400.0, 1)


def _marge_reelle(prix_vente: float, prix_achat: float,
                  cout_pieces: float, cout_sav: float) -> float:
    """Marge réelle = prix de vente - achat - pièces - SAV."""
    return round((prix_vente or 0) - (prix_achat or 0) - (cout_pieces or 0) - (cout_sav or 0), 2)


# ---------------------------------------------------------------------------
# Cycle de vie de l'application
# ---------------------------------------------------------------------------
def _ouvrir_navigateur() -> None:
    """Ouvre le dashboard dans le navigateur par défaut (au lancement)."""
    url = f"http://{settings.APP_HOST}:{settings.APP_PORT}"
    try:
        webbrowser.open(url)
    except Exception as exc:  # l'échec d'ouverture ne doit pas bloquer le serveur
        log.warning(f"Ouverture du navigateur impossible : {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise la base, amorce la démo, lance le scheduler au démarrage."""
    log.info("Démarrage du bot d'arbitrage iPhone…")
    from backend.database.db import init_db
    await init_db()

    # Sauvegarde automatique des données au lancement (sécurité client).
    from backend.backup import creer_sauvegarde
    creer_sauvegarde()

    # Amorçage des données de démonstration si la base est vide et mode simulation.
    if settings.SIMULATION_MODE:
        await simulator.amorcer_si_vide()

    # Premiers calculs pour que le dashboard affiche des données dès l'ouverture.
    try:
        await market.recalculer_tout()
        await opportunity.recalculer_scores()
        await prediction.recalculer_predictions()
    except Exception as exc:
        log.error(f"Calculs initiaux en erreur : {exc}")

    demarrer_scheduler()

    # En données réelles, on lance un premier scan en arrière-plan dès le démarrage
    # pour remplir le dashboard sans attendre le prochain cycle planifié.
    if not settings.SIMULATION_MODE:
        import asyncio

        async def _scan_initial() -> None:
            """Premier scan au lancement (capture toute exception)."""
            try:
                await scan_complet()
            except Exception as exc:
                log.error(f"Scan initial en erreur : {exc}")

        asyncio.create_task(_scan_initial())

    # Ouverture du navigateur après un court délai (laisse le serveur démarrer).
    # Désactivable via BOT_NO_BROWSER=1 (utile pour les tests / serveurs).
    import os
    if os.getenv("BOT_NO_BROWSER") != "1" and not getattr(app.state, "no_browser", False):
        threading.Timer(1.5, _ouvrir_navigateur).start()

    yield

    log.info("Arrêt du bot…")
    arreter_scheduler()


app = FastAPI(title="iPhone Arbitrage Bot", version="1.0.0", lifespan=lifespan)

# CORS large : usage local (frontend Vite en dev sur :5173, ou servi par l'API).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===========================================================================
#  ENDPOINTS API
# ===========================================================================
@app.get("/api/health")
async def health() -> dict:
    """Vérifie que l'API répond."""
    return {"status": "ok", "heure": maintenant_iso()}


@app.get("/api/status")
async def status() -> dict:
    """État global : services configurés + compteurs (pour le bandeau du dashboard)."""
    async def _compte(sql: str, params: tuple = ()) -> int:
        ligne = await fetch_one(sql, params)
        return ligne["n"] if ligne else 0

    return {
        "simulation_mode": settings.SIMULATION_MODE,
        "scan_interval_minutes": settings.SCAN_INTERVAL_MINUTES,
        "seuil_alerte_score": settings.SEUIL_ALERTE_SCORE,
        "marge_cible_pourcent": settings.MARGE_CIBLE_POURCENT,
        "services": {
            "ebay": settings.ebay_actif,
            "discord_alertes": settings.discord_alertes_actif,
            "discord_rapport": settings.discord_rapport_actif,
        },
        "compteurs": {
            "annonces_actives": await _compte("SELECT COUNT(*) AS n FROM annonces WHERE active=1"),
            "cassees": await _compte("SELECT COUNT(*) AS n FROM annonces WHERE active=1 AND etat='casse'"),
            "fonctionnelles": await _compte("SELECT COUNT(*) AS n FROM annonces WHERE active=1 AND etat='fonctionnel'"),
            "opportunites": await _compte(
                "SELECT COUNT(*) AS n FROM annonces WHERE active=1 AND score >= ?",
                (settings.SEUIL_ALERTE_SCORE,)),
            "stock": await _compte("SELECT COUNT(*) AS n FROM stock_personnel WHERE statut != 'vendu'"),
            "historique": await _compte("SELECT COUNT(*) AS n FROM historique"),
        },
    }


@app.post("/api/scan")
async def lancer_scan(background: BackgroundTasks) -> dict:
    """Déclenche un scan complet en arrière-plan (ne bloque pas la requête)."""
    background.add_task(scan_complet)
    return {"lance": True, "message": "Scan lancé en arrière-plan."}


# --- Marché ---------------------------------------------------------------
@app.get("/api/marche")
async def marche() -> list[dict]:
    """Stats de marché par modèle, triées par liquidité décroissante."""
    return await fetch_all(
        "SELECT * FROM marche_stats ORDER BY score_liquidite DESC, nb_annonces_fonctionnelles DESC"
    )


# --- Annonces -------------------------------------------------------------
@app.get("/api/annonces")
async def annonces(etat: str | None = None, modele: str | None = None,
                   actives: int = 1, limit: int = 200) -> list[dict]:
    """Liste les annonces, filtrables par état / modèle / activité."""
    conditions, params = [], []
    if actives:
        conditions.append("active = 1")
    if etat:
        conditions.append("etat = ?")
        params.append(etat)
    if modele:
        conditions.append("modele = ?")
        params.append(modele)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.append(min(limit, 500))
    return await fetch_all(
        f"SELECT * FROM annonces {where} ORDER BY premiere_detection DESC LIMIT ?",
        tuple(params),
    )


# --- Opportunités ---------------------------------------------------------
@app.get("/api/opportunites")
async def opportunites(score_min: int = 0, prix_min: float = 0, prix_max: float = 0,
                       rentables: int = 1, etat: str | None = None,
                       limit: int = 100) -> list[dict]:
    """Opportunités d'achat (cassées et/ou fonctionnelles), filtrables (facultatif)."""
    return await opportunity.top_opportunites(
        limite=min(limit, 200), score_min=score_min, prix_min=prix_min,
        prix_max=prix_max, rentables_seulement=bool(rentables), etat=etat,
    )


# --- Stock ----------------------------------------------------------------
@app.get("/api/stock")
async def liste_stock() -> list[dict]:
    """Liste le stock personnel (téléphones non encore vendus en tête)."""
    return await fetch_all(
        "SELECT * FROM stock_personnel ORDER BY (statut='vendu'), date_achat DESC"
    )


@app.post("/api/stock")
async def creer_stock(item: StockCreate) -> dict:
    """Ajoute un téléphone au stock personnel."""
    now = maintenant_iso()
    new_id = await execute(
        """INSERT INTO stock_personnel (
               modele, stockage, couleur, panne_achat, prix_achat, date_achat,
               plateforme_achat, annonce_id, pieces_remplacees, cout_pieces,
               statut, notes, created_at, updated_at
           ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (item.modele, item.stockage, item.couleur, item.panne_achat, item.prix_achat,
         item.date_achat, item.plateforme_achat, item.annonce_id, item.pieces_remplacees,
         item.cout_pieces, item.statut, item.notes, now, now),
    )
    if new_id is None:
        raise HTTPException(500, "Échec de l'ajout au stock.")
    return await fetch_one("SELECT * FROM stock_personnel WHERE id = ?", (new_id,))


@app.put("/api/stock/{stock_id}")
async def maj_stock(stock_id: int, item: StockUpdate) -> dict:
    """Met à jour une fiche stock (champs fournis uniquement)."""
    existant = await fetch_one("SELECT id FROM stock_personnel WHERE id = ?", (stock_id,))
    if not existant:
        raise HTTPException(404, "Fiche stock introuvable.")
    champs = item.model_dump(exclude_none=True)
    if not champs:
        raise HTTPException(400, "Aucun champ à mettre à jour.")
    champs["updated_at"] = maintenant_iso()
    set_clause = ", ".join(f"{k} = ?" for k in champs)
    await execute(
        f"UPDATE stock_personnel SET {set_clause} WHERE id = ?",
        tuple(champs.values()) + (stock_id,),
    )
    return await fetch_one("SELECT * FROM stock_personnel WHERE id = ?", (stock_id,))


@app.delete("/api/stock/{stock_id}")
async def supprimer_stock(stock_id: int) -> dict:
    """Supprime une fiche stock."""
    await execute("DELETE FROM stock_personnel WHERE id = ?", (stock_id,))
    return {"supprime": True}


@app.post("/api/stock/{stock_id}/vendre")
async def vendre_stock(stock_id: int, vente: VenteCreate) -> dict:
    """
    Enregistre la vente d'un téléphone du stock : crée une entrée d'historique
    (avec marge réelle + délai), marque la fiche stock comme vendue, puis
    recalcule les prédictions.
    """
    s = await fetch_one("SELECT * FROM stock_personnel WHERE id = ?", (stock_id,))
    if not s:
        raise HTTPException(404, "Fiche stock introuvable.")

    marge = _marge_reelle(vente.prix_vente, s["prix_achat"], s["cout_pieces"], vente.cout_sav)
    delai = _delai_jours(s["date_achat"], vente.date_vente)
    now = maintenant_iso()

    hist_id = await execute(
        """INSERT INTO historique (
               stock_id, modele, stockage, couleur, panne_achat, prix_achat,
               date_achat, pieces_remplacees, cout_pieces, prix_vente, date_vente,
               plateforme_vente, retour_sav, cout_sav, marge_reelle,
               delai_revente_jours, notes, created_at, updated_at
           ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (stock_id, s["modele"], s["stockage"], s["couleur"], s["panne_achat"],
         s["prix_achat"], s["date_achat"], s["pieces_remplacees"], s["cout_pieces"],
         vente.prix_vente, vente.date_vente, vente.plateforme_vente, vente.retour_sav,
         vente.cout_sav, marge, delai, vente.notes, now, now),
    )
    await execute(
        "UPDATE stock_personnel SET statut = 'vendu', updated_at = ? WHERE id = ?",
        (now, stock_id),
    )
    # Mise à jour automatique des prédictions à chaque nouvelle vente.
    await prediction.recalculer_predictions()
    return await fetch_one("SELECT * FROM historique WHERE id = ?", (hist_id,))


# --- Historique -----------------------------------------------------------
@app.get("/api/historique")
async def liste_historique() -> list[dict]:
    """Liste l'historique des ventes (plus récentes d'abord)."""
    return await fetch_all("SELECT * FROM historique ORDER BY date_vente DESC")


@app.post("/api/historique")
async def creer_historique(item: HistoriqueCreate) -> dict:
    """Saisie manuelle complète d'une vente passée (achat + vente)."""
    marge = _marge_reelle(item.prix_vente, item.prix_achat, item.cout_pieces, item.cout_sav)
    delai = _delai_jours(item.date_achat, item.date_vente)
    now = maintenant_iso()
    hist_id = await execute(
        """INSERT INTO historique (
               stock_id, modele, stockage, couleur, panne_achat, prix_achat,
               date_achat, pieces_remplacees, cout_pieces, prix_vente, date_vente,
               plateforme_vente, retour_sav, cout_sav, marge_reelle,
               delai_revente_jours, notes, created_at, updated_at
           ) VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (item.modele, item.stockage, item.couleur, item.panne_achat, item.prix_achat,
         item.date_achat, item.pieces_remplacees, item.cout_pieces, item.prix_vente,
         item.date_vente, item.plateforme_vente, item.retour_sav, item.cout_sav,
         marge, delai, item.notes, now, now),
    )
    if hist_id is None:
        raise HTTPException(500, "Échec de l'enregistrement.")
    await prediction.recalculer_predictions()
    return await fetch_one("SELECT * FROM historique WHERE id = ?", (hist_id,))


@app.delete("/api/historique/{hist_id}")
async def supprimer_historique(hist_id: int) -> dict:
    """Supprime une entrée d'historique puis recalcule les prédictions."""
    await execute("DELETE FROM historique WHERE id = ?", (hist_id,))
    await prediction.recalculer_predictions()
    return {"supprime": True}


# --- Prédictions ----------------------------------------------------------
@app.get("/api/predictions")
async def predictions() -> list[dict]:
    """Prédictions personnelles (GLOBAL en tête, puis par modèle)."""
    return await fetch_all(
        "SELECT * FROM predictions ORDER BY (modele != 'GLOBAL'), nb_entrees DESC"
    )


# --- Alertes --------------------------------------------------------------
@app.get("/api/alertes")
async def alertes(limit: int = 100) -> list[dict]:
    """Journal des notifications envoyées."""
    return await fetch_all(
        "SELECT * FROM alertes ORDER BY created_at DESC LIMIT ?", (min(limit, 500),)
    )


# ===========================================================================
#  SERVICE DU FRONTEND BUILDÉ (mode production / .exe)
# ===========================================================================
if settings.DOSSIER_FRONT.exists() and (settings.DOSSIER_FRONT / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(settings.DOSSIER_FRONT), html=True), name="frontend")
    log.info(f"Frontend servi depuis {settings.DOSSIER_FRONT}")
else:
    @app.get("/")
    async def racine() -> JSONResponse:
        """Message d'attente si le frontend n'est pas encore buildé."""
        return JSONResponse({
            "message": "API en ligne. Frontend non buildé : lancez 'npm run build' dans /frontend.",
            "docs": "/docs",
        })


if __name__ == "__main__":
    # Lancement direct (python -m backend.main) et base du futur .exe.
    import uvicorn
    log.info(f"Serveur sur http://{settings.APP_HOST}:{settings.APP_PORT}")
    uvicorn.run(app, host=settings.APP_HOST, port=settings.APP_PORT, log_level="info")
