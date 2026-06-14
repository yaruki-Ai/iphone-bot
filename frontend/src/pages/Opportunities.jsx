/**
 * Opportunities.jsx — Annonces cassées rentables, triées par score.
 * Par défaut on affiche TOUT (pas de filtre). Les filtres sont optionnels.
 */
import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import PhoneCard from "../components/PhoneCard.jsx";
import { TitreSection, Chargement, Vide, Bouton, Card } from "../components/ui.jsx";

export default function Opportunities() {
  const [annonces, setAnnonces] = useState(null);
  const [scoreMin, setScoreMin] = useState(0);
  const [prixMin, setPrixMin] = useState("");
  const [prixMax, setPrixMax] = useState("");

  /** Charge les opportunités selon les filtres (tous par défaut). */
  function charger() {
    setAnnonces(null);
    const params = new URLSearchParams({
      score_min: String(scoreMin),
      prix_min: String(prixMin || 0),
      prix_max: String(prixMax || 0),
      limit: "100",
    });
    api.get(`/opportunites?${params}`).then(setAnnonces).catch(() => setAnnonces([]));
  }

  // Au premier affichage : tout charger (sans filtre).
  useEffect(() => {
    charger();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function reinitialiser() {
    setScoreMin(0);
    setPrixMin("");
    setPrixMax("");
    setTimeout(charger, 0);
  }

  return (
    <>
      <TitreSection
        titre="Opportunités"
        sous="Annonces cassées rentables (bénéfice estimé positif), triées par score d'achat."
      />

      {/* Légende explicative (pour comprendre les cartes) */}
      <Card className="mb-4 text-sm text-muted">
        <span className="text-ink font-medium">Comment lire une carte :</span>{" "}
        <b className="text-ink">Score</b> = note d'achat /100 ·{" "}
        <b className="text-ink">Achat max</b> = prix à ne pas dépasser pour viser ta marge ·{" "}
        <b className="text-ink">Bénéfice estimé</b> = revente estimée − achat − pièces − frais (livraison/protection).
      </Card>

      {/* Filtres optionnels */}
      <div className="flex flex-wrap items-end gap-4 mb-6 bg-surface border border-line rounded-xl shadow-carte px-4 py-3">
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted">Score min</span>
          <input type="range" min="0" max="90" step="10" value={scoreMin}
            onChange={(e) => setScoreMin(Number(e.target.value))} className="accent-accent" />
          <span className="text-sm font-semibold text-ink w-8">{scoreMin}</span>
        </div>
        <label className="flex items-center gap-2 text-sm text-muted">
          Prix min
          <input type="number" min="0" value={prixMin} onChange={(e) => setPrixMin(e.target.value)}
            placeholder="0" className="w-20 bg-white border border-line rounded-lg px-2 py-1 text-ink" />€
        </label>
        <label className="flex items-center gap-2 text-sm text-muted">
          Prix max
          <input type="number" min="0" value={prixMax} onChange={(e) => setPrixMax(e.target.value)}
            placeholder="∞" className="w-20 bg-white border border-line rounded-lg px-2 py-1 text-ink" />€
        </label>
        <Bouton onClick={charger}>Appliquer</Bouton>
        <Bouton variante="ghost" onClick={reinitialiser}>Tout afficher</Bouton>
      </div>

      {annonces === null ? (
        <Chargement />
      ) : !annonces.length ? (
        <Vide texte="Aucune opportunité pour l'instant. Lancez un scan ou élargissez les filtres." />
      ) : (
        <>
          <div className="text-sm text-muted mb-3">{annonces.length} opportunité(s)</div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {annonces.map((a) => (
              <PhoneCard key={a.id} annonce={a} />
            ))}
          </div>
        </>
      )}
    </>
  );
}
