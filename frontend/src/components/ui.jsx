/**
 * ui.jsx — Composants d'interface réutilisables (sobres, thème clair).
 */
import React from "react";

/** Carte conteneur générique. */
export function Card({ children, className = "" }) {
  return (
    <div className={`rounded-xl border border-line bg-surface shadow-carte p-5 ${className}`}>
      {children}
    </div>
  );
}

/** Titre de section avec sous-titre optionnel. */
export function TitreSection({ titre, sous }) {
  return (
    <div className="mb-5">
      <h2 className="text-xl font-semibold text-ink tracking-tight">{titre}</h2>
      {sous ? <p className="text-sm text-muted mt-1">{sous}</p> : null}
    </div>
  );
}

/** Bouton stylé (variantes : primary, ghost, danger, success). */
export function Bouton({ children, variante = "primary", className = "", ...props }) {
  const styles = {
    primary: "bg-accent hover:bg-accentdark text-white",
    ghost: "bg-app hover:bg-line text-ink border border-line",
    danger: "bg-white hover:bg-red-50 text-negatif border border-line",
    success: "bg-positif hover:opacity-90 text-white",
  };
  return (
    <button
      className={`px-3.5 py-2 rounded-lg text-sm font-medium disabled:opacity-50 ${styles[variante]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

/** Champ de formulaire (label + contrôle). */
export function Champ({ label, children }) {
  return (
    <label className="flex flex-col gap-1.5 text-sm">
      <span className="text-muted font-medium">{label}</span>
      {children}
    </label>
  );
}

/** Input texte/nombre/date stylé. */
export function Input(props) {
  return (
    <input
      className="bg-white border border-line rounded-lg px-3 py-2 text-ink placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
      {...props}
    />
  );
}

/** Select stylé. */
export function Select({ children, ...props }) {
  return (
    <select
      className="bg-white border border-line rounded-lg px-3 py-2 text-ink focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
      {...props}
    >
      {children}
    </select>
  );
}

/** État de chargement. */
export function Chargement({ texte = "Chargement…" }) {
  return <div className="text-muted text-sm py-10 text-center">{texte}</div>;
}

/** État vide. */
export function Vide({ texte = "Aucune donnée." }) {
  return (
    <div className="text-muted text-sm py-12 text-center border border-dashed border-line rounded-xl bg-surface">
      {texte}
    </div>
  );
}

/** Pastille colorée pour un statut de stock. */
export function StatutBadge({ statut }) {
  const map = {
    en_reparation: "bg-amber-50 text-amber-700 border-amber-200",
    repare: "bg-blue-50 text-blue-700 border-blue-200",
    en_vente: "bg-violet-50 text-violet-700 border-violet-200",
    vendu: "bg-emerald-50 text-emerald-700 border-emerald-200",
  };
  const libelle = {
    en_reparation: "En réparation",
    repare: "Réparé",
    en_vente: "En vente",
    vendu: "Vendu",
  };
  return (
    <span className={`text-xs font-medium px-2.5 py-1 rounded-full border ${map[statut] || "bg-gray-50 text-gray-600 border-line"}`}>
      {libelle[statut] || statut}
    </span>
  );
}
