"""
repository.py — Accès haut-niveau à la table 'annonces'.

Centralise l'insertion/mise à jour des annonces (dédoublonnage par
plateforme + identifiant), le marquage des annonces disparues (= vendues)
et quelques requêtes partagées par les scrapers, le scheduler et l'analyse.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from backend.database.db import execute, fetch_all, fetch_one, maintenant_iso
from backend.logger import log


async def upsert_annonce(data: dict[str, Any]) -> Optional[int]:
    """
    Insère une annonce ou la met à jour si elle existe déjà
    (clé unique : plateforme + plateforme_id).

    En cas de mise à jour, on rafraîchit le prix et 'derniere_detection',
    on réactive l'annonce (active=1) et on efface une éventuelle disparition.
    'premiere_detection' est préservée pour calculer la rotation.
    """
    now = maintenant_iso()
    requete = """
        INSERT INTO annonces (
            plateforme, plateforme_id, url, titre, modele, stockage, couleur,
            etat, panne, prix, ville, code_postal, description, date_publication,
            premiere_detection, derniere_detection, active, icloud_detecte,
            created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?)
        ON CONFLICT(plateforme, plateforme_id) DO UPDATE SET
            prix              = excluded.prix,
            titre             = excluded.titre,
            url               = excluded.url,
            modele            = excluded.modele,
            stockage          = excluded.stockage,
            couleur           = excluded.couleur,
            etat              = excluded.etat,
            panne             = excluded.panne,
            ville             = excluded.ville,
            code_postal       = excluded.code_postal,
            description       = excluded.description,
            icloud_detecte    = excluded.icloud_detecte,
            derniere_detection= excluded.derniere_detection,
            active            = 1,
            date_disparition  = NULL,
            temps_rotation_heures = NULL,
            updated_at        = excluded.updated_at
    """
    params = (
        data.get("plateforme"),
        str(data.get("plateforme_id")),
        data.get("url"),
        data.get("titre"),
        data.get("modele"),
        data.get("stockage"),
        data.get("couleur"),
        data.get("etat"),
        data.get("panne"),
        data.get("prix"),
        data.get("ville"),
        data.get("code_postal"),
        data.get("description"),
        data.get("date_publication"),
        data.get("premiere_detection", now),
        now,                       # derniere_detection
        data.get("icloud_detecte", 0),
        now,                       # created_at
        now,                       # updated_at
    )
    await execute(requete, params)
    # On récupère l'id (fiable aussi bien en INSERT qu'en UPDATE).
    ligne = await fetch_one(
        "SELECT id FROM annonces WHERE plateforme = ? AND plateforme_id = ?",
        (data.get("plateforme"), str(data.get("plateforme_id"))),
    )
    return ligne["id"] if ligne else None


async def upsert_plusieurs(annonces: list[dict[str, Any]]) -> int:
    """Insère/maj une liste d'annonces. Retourne le nombre traité avec succès."""
    ok = 0
    for a in annonces:
        if not a.get("plateforme_id"):
            continue
        if await upsert_annonce(a) is not None:
            ok += 1
    log.info(f"{ok}/{len(annonces)} annonces enregistrées en base.")
    return ok


async def marquer_disparues(seuil_heures: float = 24.0) -> int:
    """
    Marque comme vendues (active=0) les annonces actives non revues depuis
    'seuil_heures'. Calcule le temps de rotation (disparition - 1re détection).
    Retourne le nombre d'annonces nouvellement marquées disparues.
    """
    now = datetime.now(timezone.utc)
    actives = await fetch_all(
        "SELECT id, premiere_detection, derniere_detection FROM annonces WHERE active = 1"
    )
    nb = 0
    for a in actives:
        try:
            derniere = datetime.fromisoformat(a["derniere_detection"])
        except (ValueError, TypeError):
            continue
        # Heures écoulées depuis la dernière fois où l'annonce était visible.
        ecart_h = (now - derniere).total_seconds() / 3600.0
        if ecart_h < seuil_heures:
            continue
        try:
            premiere = datetime.fromisoformat(a["premiere_detection"])
            rotation_h = (now - premiere).total_seconds() / 3600.0
        except (ValueError, TypeError):
            rotation_h = None
        await execute(
            """UPDATE annonces
               SET active = 0, date_disparition = ?, temps_rotation_heures = ?, updated_at = ?
               WHERE id = ?""",
            (now.isoformat(), rotation_h, now.isoformat(), a["id"]),
        )
        nb += 1
    if nb:
        log.info(f"{nb} annonces marquées vendues (disparues depuis > {seuil_heures}h).")
    return nb


async def annonces_par_modele(modele: str, stockage: str | None = None,
                              etat: str | None = None, actives_seulement: bool = True) -> list[dict]:
    """Retourne les annonces d'un modèle, filtrables par stockage / état."""
    conditions = ["modele = ?"]
    params: list[Any] = [modele]
    if stockage:
        conditions.append("stockage = ?")
        params.append(stockage)
    if etat:
        conditions.append("etat = ?")
        params.append(etat)
    if actives_seulement:
        conditions.append("active = 1")
    where = " AND ".join(conditions)
    return await fetch_all(f"SELECT * FROM annonces WHERE {where}", tuple(params))


async def tous_les_modeles() -> list[dict]:
    """Liste les couples (modele, stockage) présents en base avec un volume."""
    return await fetch_all(
        """SELECT modele, stockage, COUNT(*) AS nb
           FROM annonces
           WHERE modele IS NOT NULL
           GROUP BY modele, stockage
           ORDER BY nb DESC"""
    )
