-- =============================================================================
-- schema.sql — Schéma complet de la base SQLite du bot d'arbitrage iPhone.
-- Définit les 6 tables obligatoires, leurs index et leurs relations.
-- Ordre imposé : annonces -> marche_stats -> stock_personnel -> historique
--                -> predictions -> alertes
-- Tous les prix sont en euros (€). Les dates sont stockées en texte ISO 8601.
-- =============================================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- -----------------------------------------------------------------------------
-- 1) annonces : toutes les annonces collectées (LBC + Vinted + eBay confondues)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS annonces (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    plateforme           TEXT    NOT NULL,                 -- 'leboncoin' | 'vinted' | 'ebay'
    plateforme_id        TEXT    NOT NULL,                 -- identifiant de l'annonce sur la plateforme (dédup)
    url                  TEXT,
    titre                TEXT,
    modele               TEXT,                             -- ex : 'iPhone 13'
    stockage             TEXT,                             -- ex : '128 Go'
    couleur              TEXT,
    etat                 TEXT,                             -- 'casse' | 'fonctionnel'
    panne                TEXT,                             -- 'ecran' | 'vitre_arriere' | 'batterie' | 'faceid'
                                                           -- | 'camera' | 'charge' | 'ne_sallume_plus'
                                                           -- | 'pour_pieces' | 'inconnue' | NULL
    prix                 REAL,                             -- prix affiché en €
    ville                TEXT,
    code_postal          TEXT,
    description          TEXT,

    date_publication     TEXT,                             -- date de mise en ligne sur la plateforme (si dispo)
    premiere_detection   TEXT    NOT NULL,                 -- 1re fois que le bot l'a vue (ISO)
    derniere_detection   TEXT    NOT NULL,                 -- dernière fois vue active (ISO)
    active               INTEGER NOT NULL DEFAULT 1,       -- 1 = encore en ligne, 0 = disparue (vendue)
    date_disparition     TEXT,                             -- ISO, renseigné quand active passe à 0
    temps_rotation_heures REAL,                            -- date_disparition - premiere_detection (heures)

    -- Score d'achat /100 et son détail (voir analysis/scoring.py)
    score                INTEGER,
    score_liquidite      REAL,                             -- /30
    score_rentabilite    REAL,                             -- /30
    score_reparation     REAL,                             -- /20
    score_risque         REAL,                             -- /20
    prix_max_achat       REAL,                             -- seuil d'achat conseillé (opportunité)
    roi_estime           REAL,                             -- marge estimée en € (revente - achat - pièces)
    icloud_detecte       INTEGER DEFAULT 0,                -- 1 si verrouillage iCloud suspecté
    batterie_pct         INTEGER,                          -- santé batterie détectée (%) si indiquée

    created_at           TEXT    NOT NULL,
    updated_at           TEXT    NOT NULL,

    UNIQUE (plateforme, plateforme_id)
);

CREATE INDEX IF NOT EXISTS idx_annonces_modele      ON annonces (modele, stockage);
CREATE INDEX IF NOT EXISTS idx_annonces_active      ON annonces (active);
CREATE INDEX IF NOT EXISTS idx_annonces_etat        ON annonces (etat);
CREATE INDEX IF NOT EXISTS idx_annonces_score       ON annonces (score DESC);
CREATE INDEX IF NOT EXISTS idx_annonces_detection   ON annonces (premiere_detection);

-- -----------------------------------------------------------------------------
-- 2) marche_stats : statistiques de marché calculées par modèle + stockage
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS marche_stats (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    modele                    TEXT NOT NULL,
    stockage                  TEXT,

    -- Statistiques de prix calculées sur les annonces FONCTIONNELLES
    prix_min                  REAL,
    prix_moyen                REAL,
    prix_median               REAL,
    prix_premium              REAL,                         -- top 10 % (prix haut de gamme)

    -- Délais de vente (rotation) en heures
    delai_moyen_vente_heures  REAL,
    delai_median_vente_heures REAL,

    -- Volumétrie
    nb_annonces_cassees       INTEGER DEFAULT 0,
    nb_annonces_fonctionnelles INTEGER DEFAULT 0,

    -- Tendances de prix
    evolution_prix_7j         REAL,                         -- variation en % sur 7 jours
    evolution_prix_30j        REAL,                         -- variation en % sur 30 jours

    score_liquidite           REAL,                         -- indice de liquidité du modèle (0-100)
    calcule_le                TEXT NOT NULL,

    UNIQUE (modele, stockage)
);

CREATE INDEX IF NOT EXISTS idx_marche_modele ON marche_stats (modele, stockage);

-- -----------------------------------------------------------------------------
-- 3) stock_personnel : téléphones achetés et en cours de traitement
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stock_personnel (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    modele              TEXT NOT NULL,
    stockage            TEXT,
    couleur             TEXT,
    panne_achat         TEXT,                               -- panne au moment de l'achat
    prix_achat          REAL NOT NULL,
    date_achat          TEXT NOT NULL,
    plateforme_achat    TEXT,
    annonce_id          INTEGER,                            -- lien éventuel vers l'annonce d'origine

    pieces_remplacees   TEXT,                               -- saisie libre (ex : 'écran + batterie')
    cout_pieces         REAL DEFAULT 0,                     -- saisi manuellement
    statut              TEXT NOT NULL DEFAULT 'en_reparation', -- en_reparation | repare | en_vente | vendu
    notes               TEXT,

    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,

    FOREIGN KEY (annonce_id) REFERENCES annonces (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_stock_statut ON stock_personnel (statut);
CREATE INDEX IF NOT EXISTS idx_stock_modele ON stock_personnel (modele, stockage);

-- -----------------------------------------------------------------------------
-- 4) historique : téléphones vendus, avec marge réelle calculée
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS historique (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id            INTEGER,                            -- lien vers la fiche stock d'origine
    modele              TEXT NOT NULL,
    stockage            TEXT,
    couleur             TEXT,
    panne_achat         TEXT,

    prix_achat          REAL NOT NULL,
    date_achat          TEXT NOT NULL,
    pieces_remplacees   TEXT,
    cout_pieces         REAL DEFAULT 0,

    prix_vente          REAL NOT NULL,
    date_vente          TEXT NOT NULL,
    plateforme_vente    TEXT,

    retour_sav          INTEGER DEFAULT 0,                  -- 1 si retour SAV
    cout_sav            REAL DEFAULT 0,

    -- Champs calculés automatiquement (analysis/prediction + endpoints)
    marge_reelle        REAL,                               -- prix_vente - prix_achat - cout_pieces - cout_sav
    delai_revente_jours REAL,                               -- date_vente - date_achat (jours)
    notes               TEXT,

    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,

    FOREIGN KEY (stock_id) REFERENCES stock_personnel (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_historique_modele ON historique (modele, stockage);
CREATE INDEX IF NOT EXISTS idx_historique_vente  ON historique (date_vente);

-- -----------------------------------------------------------------------------
-- 5) predictions : statistiques personnelles générées depuis 'historique'
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS predictions (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    modele                      TEXT NOT NULL,              -- modèle précis ou 'GLOBAL'
    nb_entrees                  INTEGER DEFAULT 0,

    delai_moyen_revente_jours   REAL,
    marge_moyenne               REAL,
    marge_mediane               REAL,
    marge_ecart_type            REAL,
    taux_retour_sav             REAL,                       -- en %

    donnees_suffisantes         INTEGER DEFAULT 0,          -- 1 si nb_entrees >= 10
    calcule_le                  TEXT NOT NULL,

    UNIQUE (modele)
);

CREATE INDEX IF NOT EXISTS idx_predictions_modele ON predictions (modele);

-- -----------------------------------------------------------------------------
-- 6) alertes : journal de toutes les notifications envoyées
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alertes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    type          TEXT NOT NULL,                            -- 'opportunite' | 'rapport'
    annonce_id    INTEGER,
    canal         TEXT NOT NULL,                            -- 'discord' | 'telegram'
    message       TEXT,
    score         INTEGER,
    envoye        INTEGER NOT NULL DEFAULT 0,               -- 1 si envoi réussi
    erreur        TEXT,                                     -- message d'erreur éventuel
    created_at    TEXT NOT NULL,

    FOREIGN KEY (annonce_id) REFERENCES annonces (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_alertes_type ON alertes (type, created_at);
CREATE INDEX IF NOT EXISTS idx_alertes_annonce ON alertes (annonce_id);
