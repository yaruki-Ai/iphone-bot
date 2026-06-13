/**
 * Opportunities.jsx — Vue opportunités : annonces cassées intéressantes + score + ROI.
 */
import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import PhoneCard from "../components/PhoneCard.jsx";
import { TitreSection, Chargement, Vide, Bouton } from "../components/ui.jsx";

export default function Opportunities() {
  const [annonces, setAnnonces] = useState(null);
  const [scoreMin, setScoreMin] = useState(50);

  /** Charge les opportunités selon le score minimum. */
  function charger(min) {
    setAnnonces(null);
    api
      .get(`/opportunites?score_min=${min}&limit=60`)
      .then(setAnnonces)
      .catch(() => setAnnonces([]));
  }

  useEffect(() => {
    charger(scoreMin);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <TitreSection
        titre="Opportunités"
        sous="Annonces cassées classées par score d'achat et ROI estimé."
      />

      {/* Filtre score minimum */}
      <div className="flex items-center gap-4 mb-6 bg-surface border border-line rounded-xl shadow-carte px-4 py-3">
        <span className="text-sm text-muted">Score minimum</span>
        <input
          type="range"
          min="0"
          max="90"
          step="10"
          value={scoreMin}
          onChange={(e) => setScoreMin(Number(e.target.value))}
          className="accent-accent flex-1 max-w-xs"
        />
        <span className="text-sm font-semibold text-ink w-10">{scoreMin}+</span>
        <Bouton onClick={() => charger(scoreMin)}>Filtrer</Bouton>
      </div>

      {annonces === null ? (
        <Chargement />
      ) : !annonces.length ? (
        <Vide texte="Aucune opportunité à ce niveau de score. Baissez le filtre ou lancez un scan." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {annonces.map((a) => (
            <PhoneCard key={a.id} annonce={a} />
          ))}
        </div>
      )}
    </>
  );
}
