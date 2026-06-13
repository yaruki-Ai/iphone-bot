/**
 * AlertBadge.jsx — Badge sobre indiquant le niveau d'opportunité (sans emoji).
 */
import React from "react";

export default function AlertBadge({ score = 0 }) {
  let texte = "À étudier";
  let classe = "bg-gray-50 text-gray-600 border-line";
  if (score >= 80) {
    texte = "Excellente";
    classe = "bg-emerald-50 text-emerald-700 border-emerald-200";
  } else if (score >= 70) {
    texte = "Opportunité";
    classe = "bg-blue-50 text-blue-700 border-blue-200";
  } else if (score >= 50) {
    texte = "Correcte";
    classe = "bg-amber-50 text-amber-700 border-amber-200";
  }
  return (
    <span className={`text-xs font-medium px-2.5 py-1 rounded-full border ${classe}`}>
      {texte}
    </span>
  );
}
