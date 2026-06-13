/**
 * ScoreBar.jsx — Barre de score d'achat /100, colorée sobrement selon le niveau.
 */
import React from "react";

/** Retourne une couleur de barre selon le score (teintes maîtrisées). */
function couleur(score) {
  if (score >= 80) return "bg-emerald-600";
  if (score >= 70) return "bg-emerald-500";
  if (score >= 50) return "bg-amber-500";
  if (score >= 30) return "bg-orange-400";
  return "bg-red-400";
}

export default function ScoreBar({ score = 0, compact = false }) {
  const valeur = Math.max(0, Math.min(100, score || 0));
  return (
    <div className="w-full">
      {!compact && (
        <div className="flex justify-between text-xs text-muted mb-1.5">
          <span>Score d'achat</span>
          <span className="font-semibold text-ink">{valeur}/100</span>
        </div>
      )}
      <div className="h-2 w-full rounded-full bg-gray-100 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${couleur(valeur)}`}
          style={{ width: `${valeur}%` }}
        />
      </div>
    </div>
  );
}
