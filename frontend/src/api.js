/**
 * api.js — Petit client HTTP vers l'API FastAPI.
 * Toutes les routes sont relatives ('/api/...') : fonctionne aussi bien servi
 * par FastAPI (.exe) qu'en dev via le proxy Vite.
 */

const BASE = "/api";

/** Effectue une requête JSON générique avec gestion d'erreur. */
async function requete(chemin, options = {}) {
  const rep = await fetch(`${BASE}${chemin}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!rep.ok) {
    let detail = rep.statusText;
    try {
      const j = await rep.json();
      detail = j.detail || detail;
    } catch (e) {
      /* corps non JSON : on garde statusText */
    }
    throw new Error(detail);
  }
  if (rep.status === 204) return null;
  return rep.json();
}

export const api = {
  /** GET simple. */
  get: (chemin) => requete(chemin),
  /** POST avec corps JSON. */
  post: (chemin, corps) =>
    requete(chemin, { method: "POST", body: JSON.stringify(corps || {}) }),
  /** PUT avec corps JSON. */
  put: (chemin, corps) =>
    requete(chemin, { method: "PUT", body: JSON.stringify(corps || {}) }),
  /** DELETE. */
  del: (chemin) => requete(chemin, { method: "DELETE" }),
};

/** Formate un montant en euros (sans décimales superflues). */
export function euros(v) {
  if (v === null || v === undefined || isNaN(v)) return "—";
  return `${Math.round(v)} €`;
}

/** Formate un nombre d'heures en "Xj Yh" lisible. */
export function heuresEnDelai(h) {
  if (h === null || h === undefined) return "—";
  const jours = Math.floor(h / 24);
  const reste = Math.round(h % 24);
  if (jours <= 0) return `${reste}h`;
  return `${jours}j ${reste}h`;
}

/** Libellé lisible d'une panne. */
export function libellePanne(p) {
  const table = {
    ecran: "Écran cassé",
    vitre_arriere: "Vitre arrière",
    batterie: "Batterie",
    faceid: "Face ID",
    camera: "Caméra",
    charge: "Charge",
    ne_sallume_plus: "Ne s'allume plus",
    pour_pieces: "Pour pièces",
    inconnue: "Panne inconnue",
  };
  return table[p] || p || "—";
}
