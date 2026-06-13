/**
 * PhoneCard.jsx — Carte d'une annonce / opportunité d'achat (sobre, sans emoji).
 * Affiche modèle, panne, prix, score, prix max conseillé et ROI estimé.
 */
import React from "react";
import ScoreBar from "./ScoreBar.jsx";
import AlertBadge from "./AlertBadge.jsx";
import { euros, libellePanne } from "../api.js";

/** Pastille de plateforme discrète. */
function Plateforme({ nom }) {
  const couleurs = {
    leboncoin: "text-orange-700 bg-orange-50 border-orange-200",
    vinted: "text-teal-700 bg-teal-50 border-teal-200",
    ebay: "text-blue-700 bg-blue-50 border-blue-200",
  };
  return (
    <span className={`text-[11px] font-medium px-2 py-0.5 rounded border ${couleurs[nom] || "text-gray-600 bg-gray-50 border-line"}`}>
      {nom}
    </span>
  );
}

export default function PhoneCard({ annonce }) {
  const a = annonce;
  const bonAchat = a.prix_max_achat && a.prix && a.prix <= a.prix_max_achat;

  return (
    <div className="rounded-xl border border-line bg-surface shadow-carte p-5 flex flex-col gap-4 hover:border-accent/50 transition">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold text-ink leading-tight">
            {a.modele || "iPhone"} <span className="text-muted font-normal">{a.stockage || ""}</span>
          </h3>
          <div className="flex items-center gap-2 mt-1.5">
            <Plateforme nom={a.plateforme} />
            <span className="text-xs text-muted">{a.ville || "France"}</span>
          </div>
        </div>
        <AlertBadge score={a.score} />
      </div>

      <div className="flex items-center gap-2 text-sm">
        <span className="px-2 py-0.5 rounded border border-line bg-app text-ink text-xs">
          {libellePanne(a.panne)}
        </span>
        {a.icloud_detecte ? (
          <span className="px-2 py-0.5 rounded border border-violet-200 bg-violet-50 text-violet-700 text-xs">
            iCloud à vérifier
          </span>
        ) : null}
      </div>

      <ScoreBar score={a.score} />

      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="rounded-lg bg-app py-2.5">
          <div className="text-[11px] text-muted">Prix</div>
          <div className="font-semibold text-ink">{euros(a.prix)}</div>
        </div>
        <div className="rounded-lg bg-app py-2.5">
          <div className="text-[11px] text-muted">Max conseillé</div>
          <div className={`font-semibold ${bonAchat ? "text-positif" : "text-ink"}`}>
            {euros(a.prix_max_achat)}
          </div>
        </div>
        <div className="rounded-lg bg-app py-2.5">
          <div className="text-[11px] text-muted">ROI estimé</div>
          <div className="font-semibold text-positif">{euros(a.roi_estime)}</div>
        </div>
      </div>

      {a.url ? (
        <a
          href={a.url}
          target="_blank"
          rel="noreferrer"
          className="text-center text-sm font-medium text-accent hover:text-accentdark"
        >
          Voir l'annonce
        </a>
      ) : null}
    </div>
  );
}
