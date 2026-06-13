/**
 * Market.jsx — Vue marché : modèles les plus liquides + rentables + tendances.
 */
import React, { useEffect, useState } from "react";
import { api, euros, heuresEnDelai } from "../api.js";
import { Card, TitreSection, Chargement, Vide } from "../components/ui.jsx";

/** Affiche une variation de prix avec indicateur coloré sobre. */
function Tendance({ valeur }) {
  if (valeur === null || valeur === undefined)
    return <span className="text-gray-400">—</span>;
  const positif = valeur >= 0;
  return (
    <span className={positif ? "text-positif" : "text-negatif"}>
      {positif ? "+" : ""}{valeur.toFixed(1)}%
    </span>
  );
}

/** Mini-barre de liquidité. */
function Liquidite({ score }) {
  const v = Math.round(score || 0);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 rounded-full bg-gray-100 overflow-hidden">
        <div className="h-full bg-accent" style={{ width: `${v}%` }} />
      </div>
      <span className="text-xs text-muted w-7">{v}</span>
    </div>
  );
}

export default function Market() {
  const [stats, setStats] = useState(null);
  const [tri, setTri] = useState("score_liquidite");

  useEffect(() => {
    api.get("/marche").then(setStats).catch(() => setStats([]));
  }, []);

  if (stats === null) return <Chargement />;
  if (!stats.length)
    return (
      <>
        <TitreSection titre="Marché" sous="Statistiques par modèle d'iPhone." />
        <Vide texte="Aucune statistique de marché pour l'instant. Lancez un scan." />
      </>
    );

  const tries = [...stats].sort((a, b) => (b[tri] || 0) - (a[tri] || 0));
  const topLiquide = tries[0];
  const topRentable = [...stats].sort(
    (a, b) => (b.prix_premium || 0) - (a.prix_premium || 0)
  )[0];

  return (
    <>
      <TitreSection
        titre="Marché"
        sous="Prix, délais de vente et tendances par modèle (annonces fonctionnelles)."
      />

      {/* Cartes résumé */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card>
          <div className="text-sm text-muted">Modèle le plus liquide</div>
          <div className="text-lg font-semibold text-ink mt-1">
            {topLiquide.modele} {topLiquide.stockage}
          </div>
          <div className="text-sm text-accent mt-1">
            Liquidité {Math.round(topLiquide.score_liquidite)}/100 ·{" "}
            {heuresEnDelai(topLiquide.delai_median_vente_heures)} de rotation
          </div>
        </Card>
        <Card>
          <div className="text-sm text-muted">Prix premium le plus élevé</div>
          <div className="text-lg font-semibold text-ink mt-1">
            {topRentable.modele} {topRentable.stockage}
          </div>
          <div className="text-sm text-positif mt-1">
            jusqu'à {euros(topRentable.prix_premium)}
          </div>
        </Card>
        <Card>
          <div className="text-sm text-muted">Modèles suivis</div>
          <div className="text-3xl font-semibold text-ink mt-1">{stats.length}</div>
          <div className="text-sm text-muted mt-1">couples modèle / stockage</div>
        </Card>
      </div>

      {/* Tableau détaillé */}
      <Card className="overflow-x-auto p-0">
        <div className="flex justify-end p-4 pb-0">
          <select
            value={tri}
            onChange={(e) => setTri(e.target.value)}
            className="bg-white border border-line rounded-lg px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
          >
            <option value="score_liquidite">Trier par liquidité</option>
            <option value="prix_median">Trier par prix médian</option>
            <option value="prix_premium">Trier par prix premium</option>
            <option value="nb_annonces_fonctionnelles">Trier par volume</option>
          </select>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-muted border-b border-line text-xs uppercase tracking-wide">
              <th className="py-3 px-4">Modèle</th>
              <th className="py-3 px-2">Min</th>
              <th className="py-3 px-2">Médian</th>
              <th className="py-3 px-2">Moyen</th>
              <th className="py-3 px-2">Premium</th>
              <th className="py-3 px-2">Rotation</th>
              <th className="py-3 px-2">Cassés / Fonct.</th>
              <th className="py-3 px-2">7j</th>
              <th className="py-3 px-2">30j</th>
              <th className="py-3 px-2">Liquidité</th>
            </tr>
          </thead>
          <tbody>
            {tries.map((s, i) => (
              <tr key={i} className="border-b border-line/70 hover:bg-app">
                <td className="py-3 px-4 font-medium text-ink">
                  {s.modele} <span className="text-muted font-normal">{s.stockage}</span>
                </td>
                <td className="py-3 px-2 text-muted">{euros(s.prix_min)}</td>
                <td className="py-3 px-2 text-ink font-semibold">{euros(s.prix_median)}</td>
                <td className="py-3 px-2 text-muted">{euros(s.prix_moyen)}</td>
                <td className="py-3 px-2 text-positif">{euros(s.prix_premium)}</td>
                <td className="py-3 px-2 text-muted">
                  {heuresEnDelai(s.delai_median_vente_heures)}
                </td>
                <td className="py-3 px-2 text-muted">
                  <span className="text-negatif">{s.nb_annonces_cassees}</span> /{" "}
                  <span className="text-accent">{s.nb_annonces_fonctionnelles}</span>
                </td>
                <td className="py-3 px-2"><Tendance valeur={s.evolution_prix_7j} /></td>
                <td className="py-3 px-2"><Tendance valeur={s.evolution_prix_30j} /></td>
                <td className="py-3 px-2"><Liquidite score={s.score_liquidite} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}
