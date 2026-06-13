/**
 * Predictions.jsx — Prédictions basées sur l'historique personnel.
 * Affiche "Données insuffisantes" tant qu'il y a moins de 10 ventes (GLOBAL).
 */
import React, { useEffect, useState } from "react";
import { api, euros } from "../api.js";
import { Card, TitreSection, Chargement, Vide } from "../components/ui.jsx";

/** Carte d'indicateur prédictif. */
function Indic({ titre, valeur, accent = "text-ink" }) {
  return (
    <Card>
      <div className="text-sm text-muted">{titre}</div>
      <div className={`text-2xl font-semibold mt-1 ${accent}`}>{valeur}</div>
    </Card>
  );
}

export default function Predictions() {
  const [preds, setPreds] = useState(null);

  useEffect(() => {
    api.get("/predictions").then(setPreds).catch(() => setPreds([]));
  }, []);

  if (preds === null) return <Chargement />;

  const global = preds.find((p) => p.modele === "GLOBAL");
  const parModele = preds.filter((p) => p.modele !== "GLOBAL");
  const suffisant = global && global.donnees_suffisantes;

  return (
    <>
      <TitreSection
        titre="Prédictions"
        sous="Statistiques issues uniquement de votre historique de ventes (sans IA externe)."
      />

      {!global || global.nb_entrees === 0 ? (
        <Vide texte="Aucune vente enregistrée. Saisissez vos ventes dans l'onglet Historique." />
      ) : !suffisant ? (
        <Card className="border-amber-200 bg-amber-50/40">
          <div className="text-amber-700 font-semibold text-lg">Données insuffisantes</div>
          <p className="text-muted mt-2">
            {global.nb_entrees} vente(s) enregistrée(s). Il en faut au moins{" "}
            <span className="text-ink font-semibold">10</span> pour des prédictions fiables.
          </p>
          <div className="h-2 w-full rounded-full bg-gray-100 mt-3 overflow-hidden">
            <div className="h-full bg-amber-500"
              style={{ width: `${Math.min(100, (global.nb_entrees / 10) * 100)}%` }} />
          </div>
        </Card>
      ) : (
        <>
          {/* Prédiction globale */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <Indic titre="Ventes analysées" valeur={global.nb_entrees} />
            <Indic titre="Marge probable (médiane)" valeur={euros(global.marge_mediane)}
              accent="text-positif" />
            <Indic titre="Délai moyen de revente"
              valeur={`${global.delai_moyen_revente_jours ?? "—"} j`} />
            <Indic titre="Risque retour SAV"
              valeur={`${global.taux_retour_sav ?? 0}%`} />
          </div>

          <Card className="mb-6">
            <div className="text-sm text-muted">
              Marge moyenne : <span className="text-ink font-semibold">{euros(global.marge_moyenne)}</span>
              {"  ·  "}Écart-type : <span className="text-ink font-semibold">{euros(global.marge_ecart_type)}</span>
            </div>
            <p className="text-xs text-muted mt-1">
              L'écart-type mesure la régularité de vos marges : plus il est faible, plus vos résultats sont stables.
            </p>
          </Card>
        </>
      )}

      {/* Détail par modèle (toujours affiché s'il existe) */}
      {parModele.length ? (
        <>
          <h3 className="text-lg font-semibold text-ink mb-3">Par modèle</h3>
          <Card className="overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted border-b border-line text-xs uppercase tracking-wide">
                  <th className="py-3 px-4">Modèle</th>
                  <th className="py-3 px-2">Ventes</th>
                  <th className="py-3 px-2">Marge méd.</th>
                  <th className="py-3 px-2">Délai moy.</th>
                  <th className="py-3 px-2">Retour SAV</th>
                  <th className="py-3 px-2">Fiabilité</th>
                </tr>
              </thead>
              <tbody>
                {parModele.map((p, i) => (
                  <tr key={i} className="border-b border-line/70 hover:bg-app">
                    <td className="py-3 px-4 font-medium text-ink">{p.modele}</td>
                    <td className="py-3 px-2">{p.nb_entrees}</td>
                    <td className="py-3 px-2 text-positif">{euros(p.marge_mediane)}</td>
                    <td className="py-3 px-2">
                      {p.delai_moyen_revente_jours != null ? `${p.delai_moyen_revente_jours} j` : "—"}
                    </td>
                    <td className="py-3 px-2">{p.taux_retour_sav ?? 0}%</td>
                    <td className="py-3 px-2">
                      {p.donnees_suffisantes ? (
                        <span className="text-positif text-xs font-medium">Fiable</span>
                      ) : (
                        <span className="text-muted text-xs">Insuffisant</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      ) : null}
    </>
  );
}
