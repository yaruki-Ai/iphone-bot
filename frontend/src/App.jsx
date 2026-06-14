/**
 * App.jsx — Coquille de l'application : navigation entre les 5 pages,
 * bandeau d'état (services + compteurs) et bouton de scan manuel.
 */
import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import Market from "./pages/Market.jsx";
import Opportunities from "./pages/Opportunities.jsx";
import Stock from "./pages/Stock.jsx";
import History from "./pages/History.jsx";
import Predictions from "./pages/Predictions.jsx";

const PAGES = [
  { id: "marche", label: "Marché", composant: Market },
  { id: "opportunites", label: "Opportunités", composant: Opportunities },
  { id: "stock", label: "Stock", composant: Stock },
  { id: "historique", label: "Historique", composant: History },
  { id: "predictions", label: "Prédictions", composant: Predictions },
];

/** Logo de l'application (cohérent avec le favicon et l'icône de l'exe). */
function Logo() {
  return (
    <svg width="34" height="34" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg" aria-label="Arbitrage iPhone">
      <rect width="512" height="512" rx="112" fill="#2f6df0" />
      <polyline points="116,344 210,256 298,306 398,176" fill="none"
        stroke="#ffffff" strokeWidth="38" strokeLinecap="round" strokeLinejoin="round" />
      <polygon points="356,160 416,150 412,212" fill="#ffffff" />
    </svg>
  );
}

/** Petit compteur affiché dans le bandeau. */
function Compteur({ label, valeur, accent = "text-ink" }) {
  return (
    <div className="text-center px-1">
      <div className={`text-lg font-semibold ${accent}`}>{valeur}</div>
      <div className="text-[11px] text-muted">{label}</div>
    </div>
  );
}

/** Indicateur d'état d'un service (point + libellé). */
function Service({ actif, label }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted">
      <span className={`h-1.5 w-1.5 rounded-full ${actif ? "bg-positif" : "bg-gray-300"}`} />
      {label}
    </span>
  );
}

export default function App() {
  const [page, setPage] = useState("marche");
  const [status, setStatus] = useState(null);
  const [scanEnCours, setScanEnCours] = useState(false);
  const [toast, setToast] = useState("");

  /** Recharge le bandeau d'état. */
  function rafraichirStatus() {
    api.get("/status").then(setStatus).catch(() => {});
  }

  useEffect(() => {
    rafraichirStatus();
    const t = setInterval(rafraichirStatus, 30000); // rafraîchit toutes les 30 s
    return () => clearInterval(t);
  }, []);

  /** Lance un scan manuel puis rafraîchit après un court délai. */
  async function lancerScan() {
    setScanEnCours(true);
    setToast("");
    try {
      await api.post("/scan");
      setToast("Scan lancé — les résultats arrivent dans quelques secondes.");
      setTimeout(rafraichirStatus, 6000);
    } catch (e) {
      setToast("Erreur lors du lancement du scan.");
    } finally {
      setTimeout(() => setScanEnCours(false), 6000);
      // Le message disparaît automatiquement au bout de 5 s.
      setTimeout(() => setToast(""), 5000);
    }
  }

  const PageActive = PAGES.find((p) => p.id === page).composant;
  const c = status?.compteurs || {};
  const s = status?.services || {};

  return (
    <div className="min-h-full">
      {/* En-tête */}
      <header className="border-b border-line bg-surface/90 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <Logo />
            <div>
              <h1 className="font-semibold text-ink leading-tight tracking-tight text-[17px]">
                Arbitrage iPhone
              </h1>
              <div className="flex items-center gap-3 mt-1">
                {status?.simulation_mode ? (
                  <span className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded">
                    Mode démonstration
                  </span>
                ) : (
                  <span className="text-[11px] text-positif bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded">
                    Données réelles
                  </span>
                )}
                <Service actif={true} label="Vinted" />
                <Service actif={true} label="eBay" />
              </div>
            </div>
          </div>

          {/* Compteurs */}
          <div className="flex items-center gap-5">
            <Compteur label="Annonces" valeur={c.annonces_actives ?? "—"} />
            <Compteur label="Cassés" valeur={c.cassees ?? "—"} />
            <Compteur label="Opportunités" valeur={c.opportunites ?? "—"} accent="text-positif" />
            <Compteur label="Stock" valeur={c.stock ?? "—"} />
            <button
              onClick={lancerScan}
              disabled={scanEnCours}
              className="px-4 py-2 rounded-lg bg-accent hover:bg-accentdark text-white text-sm font-medium disabled:opacity-50"
            >
              {scanEnCours ? "Scan en cours…" : "Scanner"}
            </button>
          </div>
        </div>

        {/* Navigation */}
        <nav className="max-w-7xl mx-auto px-6 flex gap-6 overflow-x-auto">
          {PAGES.map((p) => (
            <button
              key={p.id}
              onClick={() => setPage(p.id)}
              className={`py-3 text-sm font-medium border-b-2 -mb-px whitespace-nowrap ${
                page === p.id
                  ? "border-accent text-accent"
                  : "border-transparent text-muted hover:text-ink"
              }`}
            >
              {p.label}
            </button>
          ))}
        </nav>
      </header>

      {/* Toast */}
      {toast ? (
        <div className="max-w-7xl mx-auto px-6 pt-4">
          <div className="text-sm text-accent bg-blue-50 border border-blue-200 rounded-lg px-3 py-2">
            {toast}
          </div>
        </div>
      ) : null}

      {/* Contenu de la page */}
      <main className="max-w-7xl mx-auto px-6 py-7">
        <PageActive />
      </main>

      <footer className="max-w-7xl mx-auto px-6 py-8 text-center text-xs text-gray-400">
        Arbitrage iPhone · usage personnel · montants en euros
      </footer>
    </div>
  );
}
