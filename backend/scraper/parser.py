"""
parser.py — Identification des iPhone et détection des pannes depuis le texte.

À partir du titre + description d'une annonce, ce module déduit :
  - le modèle (ex : 'iPhone 13 Pro Max')
  - le stockage (ex : '128 Go')
  - l'état ('casse' ou 'fonctionnel')
  - la panne principale (la plus sévère détectée)
  - un éventuel verrouillage iCloud
  - le rejet des accessoires / pièces détachées (modele = None)

Précisions clés :
  - La détection de panne exige des formulations EXPLICITES ('batterie HS',
    'écran cassé'…) et non le simple nom du composant : un reconditionné
    ('nouvelle batterie 100%') n'est donc pas classé cassé.
  - Les pannes/états sont détectés par RACINE ('cass' -> cassé/cassés/casser…)
    pour gérer pluriels/féminins, mais avec une frontière de MOT au début
    (ainsi 'débloqué' ne matche pas 'bloqué', 'incassable' ne matche pas 'cass').
  - Les accessoires sont détectés en MOTS ENTIERS (ainsi 'support' ne matche pas
    'supporte').
Aucune dépendance externe : uniquement des expressions régulières.
"""

import re
import unicodedata

# Pannes par sévérité DÉCROISSANTE. Racines explicites (matchées en début de mot).
_PANNES: list[tuple[str, tuple[str, ...]]] = [
    ("pour_pieces", ("pour piece", "pieces detach", "piece detach",
                     "pour reparation", "pour bricoleur", "pour reparateur")),
    ("ne_sallume_plus", ("ne sallume plus", "ne s allume plus", "ne sallume pas",
                         "ne demarre plus", "ne demarre pas", "demarre pas",
                         "ne sallume", "ne demarre", "reste eteint")),
    ("faceid", ("face id hs", "faceid hs", "face id ne fonctionne", "face id ne marche",
                "probleme de face id", "probleme face id", "face id ko",
                "face id a reparer", "face id defectu")),
    ("charge", ("ne charge plus", "ne charge pas", "probleme de charge",
                "connecteur de charge hs", "souci de charge", "ne se recharge plus",
                "port de charge hs", "prise de charge hs")),
    ("camera", ("camera hs", "camera cass", "camera ne fonctionne", "appareil photo hs",
                "camera floue", "objectif cass", "camera defectu", "camera arriere hs")),
    ("batterie", ("batterie hs", "batterie a changer", "batterie mort",
                  "probleme de batterie", "batterie gonfl", "batterie defectu",
                  "batterie a remplacer", "change la batterie", "batterie faible",
                  "batterie fatigu", "batterie naze")),
    ("vitre_arriere", ("vitre arriere cass", "vitre arriere fissur", "dos cass",
                       "dos fissur", "verre arriere cass", "arriere cass",
                       "vitre arriere a changer", "arriere fissur", "dos bris")),
    ("ecran", ("ecran cass", "ecran fissur", "ecran hs", "ecran abim", "vitre cass",
               "vitre fissur", "tactile hs", "lcd hs", "ecran a changer", "ecran ray",
               "ecran tach", "ecran noir", "pixels morts", "ecran ne fonctionne",
               "ecran bris", "tactile ne fonctionne", "ecran defectu", "affichage hs")),
    ("inconnue", ("en panne", "defectu", "ne fonctionne pas", "ne fonctionne plus",
                  "ne marche pas", "ne marche plus", "a reparer", "probleme inconnu", "hs")),
]

# Racines indiquant un appareil cassé (si aucune panne précise trouvée).
_MOTS_CASSE = ("cass", "fissur", "hs", "en panne", "defectu", "pour piece", "abim",
               "ne fonctionne", "ne marche pas", "a reparer", "endommag", "bris")

# Verrouillage iCloud / blocage de compte (drapeau de risque, matché en début de mot).
_MOTS_ICLOUD = ("icloud", "verrouillage activation", "compte verrouille", "id bloque",
                "localiser active", "find my", "compte apple bloque", "bloque icloud")

# Modèles à variantes (numéro + suffixe). 'pro max' testé avant 'pro'.
_NUMS = ("16", "15", "14", "13", "12", "11", "8", "7", "6s", "6")
_VARIANTES = ("pro max", "pro", "plus", "mini")

# Mots indiquant un ACCESSOIRE (jamais un téléphone) : mots entiers, n'importe où.
_ACCESSOIRES = (
    "protection", "protecteur", "verre trempe", "tempered", "glass", "film",
    "coque", "etui", "housse", "pochette", "bumper", "silicone", "chargeur",
    "cable", "adaptateur", "dock", "station", "cordon", "qdos", "spigen", "otterbox",
    "stylet", "embout", "antichoc", "screen protector", "vitre de protection",
    "manette", "lot de", "sticker", "skin", "autocollant", "coffret vide", "boite vide",
)

# Noms de PIÈCES détachées : si présents AVANT 'iphone' dans le titre => rejet.
_PIECES = (
    "ecran", "vitre", "camera", "batterie", "nappe", "connecteur", "chassis",
    "carte mere", "bouton", "haut parleur", "haut-parleur", "ecouteur", "lentille",
    "capot", "face avant", "face arriere", "vibreur", "tiroir sim", "lcd", "oled",
    "dalle", "micro", "port de charge", "bloc photo", "module",
)


def _normaliser(texte: str) -> str:
    """Passe en minuscules, retire les accents, neutralise apostrophes et espaces."""
    if not texte:
        return ""
    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = texte.lower()
    texte = re.sub(r"['’`´]", " ", texte)  # "s'allume" -> "s allume"
    return re.sub(r"\s+", " ", texte).strip()


def _contient_mot(t: str, mots) -> bool:
    """Vrai si l'un des mots est présent en MOT ENTIER (pluriel 's' toléré)."""
    return any(re.search(r"\b" + re.escape(m) + r"s?\b", t) for m in mots)


def _contient_racine(t: str, racines) -> bool:
    """
    Vrai si l'une des racines est présente AU DÉBUT D'UN MOT.
    Gère pluriels/féminins ('cass' -> cassé/cassés/cassée) sans matcher en
    milieu de mot ('débloqué' ne matche pas 'bloque', 'incassable' pas 'cass').
    """
    return any(re.search(r"\b" + re.escape(r), t) for r in racines)


def detect_modele(texte: str) -> str | None:
    """Identifie le modèle d'iPhone à partir du texte normalisé (ou None)."""
    t = _normaliser(texte)
    if "iphone" not in t and "apple" not in t:
        return None

    if re.search(r"iphone\s*se", t) or re.search(r"\bse\b.*iphone", t):
        if "2022" in t or "se 3" in t or "3eme" in t or "(3" in t:
            return "iPhone SE 2022"
        if "2020" in t or "se 2" in t or "2eme" in t or "(2" in t:
            return "iPhone SE 2020"
        return "iPhone SE"

    motif_num = r"iphone\s*(" + "|".join(_NUMS) + r")\s*(pro max|pro|plus|mini)?"
    m = re.search(motif_num, t)
    if m:
        num = m.group(1).upper()
        variante = m.group(2)
        if variante:
            suffixe = "mini" if variante == "mini" else variante.title()
            return f"iPhone {num} {suffixe}"
        return f"iPhone {num}"

    if re.search(r"iphone\s*xs\s*max", t):
        return "iPhone XS Max"
    if re.search(r"iphone\s*xs", t):
        return "iPhone XS"
    if re.search(r"iphone\s*xr", t):
        return "iPhone XR"
    if re.search(r"iphone\s*x\b", t):
        return "iPhone X"
    return None


def detect_stockage(texte: str) -> str | None:
    """Identifie la capacité de stockage (ex : '128 Go' ou '1 To')."""
    t = _normaliser(texte)
    m = re.search(r"(\d)\s*(to|tb)\b", t)
    if m:
        return f"{m.group(1)} To"
    for capacite in (512, 256, 128, 64, 32, 16):
        if re.search(rf"\b{capacite}\s*(go|gb)\b", t):
            return f"{capacite} Go"
    return None


def detect_panne(texte: str) -> str | None:
    """Retourne la panne la plus sévère détectée (formulation explicite), ou None."""
    t = _normaliser(texte)
    for panne, racines in _PANNES:
        if _contient_racine(t, racines):
            return panne
    return None


def detect_etat(texte: str, panne: str | None) -> str:
    """Détermine si l'annonce est 'casse' ou 'fonctionnel'."""
    if panne is not None:
        return "casse"
    return "casse" if _contient_racine(_normaliser(texte), _MOTS_CASSE) else "fonctionnel"


def detect_icloud(texte: str) -> bool:
    """Vrai si un verrouillage iCloud / blocage de compte est suspecté."""
    return _contient_racine(_normaliser(texte), _MOTS_ICLOUD)


def difficulte_reparation(panne: str | None) -> str:
    """Convertit une panne en difficulté : facile|moyen|difficile|impossible|aucune."""
    table = {
        None: "aucune", "ecran": "facile", "batterie": "facile",
        "vitre_arriere": "moyen", "camera": "moyen", "charge": "moyen",
        "faceid": "difficile", "ne_sallume_plus": "difficile",
        "inconnue": "difficile", "pour_pieces": "impossible",
    }
    return table.get(panne, "difficile")


def est_accessoire(titre: str) -> bool:
    """
    Détecte un accessoire ou une pièce détachée (et non un iPhone à vendre).
    Ex : 'Écran iPhone 12 Pro Max', 'Protection écran QDOS iPhone 15'.
    - mot d'accessoire n'importe où (coque, protection, glass, chargeur…) => oui ;
    - nom de pièce (écran, vitre, caméra…) AVANT 'iphone' => sujet = la pièce => oui.
    """
    t = _normaliser(titre)
    if not t:
        return False
    if _contient_mot(t, _ACCESSOIRES):
        return True
    ref = t.find("iphone")
    if ref < 0:
        ref = t.find("apple")
    for piece in _PIECES:
        p = t.find(piece)
        if p >= 0 and (ref < 0 or p < ref):
            return True
    return False


def analyser_texte(titre: str, description: str = "") -> dict:
    """
    Analyse complète d'une annonce : modele, stockage, etat, panne, icloud_detecte.
    Si c'est un accessoire / une pièce détachée, modele=None (ignoré par les scrapers).
    """
    if est_accessoire(titre):
        return {"modele": None, "stockage": None, "etat": "fonctionnel",
                "panne": None, "icloud_detecte": 0}

    texte = f"{titre or ''} {description or ''}"
    panne = detect_panne(texte)
    etat = detect_etat(texte, panne)
    if etat == "casse" and panne is None:
        panne = "inconnue"
    return {
        "modele": detect_modele(texte),
        "stockage": detect_stockage(texte),
        "etat": etat,
        "panne": panne,
        "icloud_detecte": 1 if detect_icloud(texte) else 0,
    }
