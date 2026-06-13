/**
 * History.jsx — Historique personnel : toutes les ventes + marge réelle.
 * Permet la saisie manuelle d'une vente passée et le calcul automatique des totaux.
 */
import React, { useEffect, useState } from "react";
import { api, euros, libellePanne } from "../api.js";
import {
  Card, TitreSection, Chargement, Vide, Bouton, Champ, Input, Select,
} from "../components/ui.jsx";

const PANNES = ["ecran", "vitre_arriere", "batterie", "faceid", "camera", "charge",
  "ne_sallume_plus", "pour_pieces", "inconnue"];

function aujourdhui() {
  return new Date().toISOString().slice(0, 10);
}

export default function History() {
  const [items, setItems] = useState(null);
  const [ouvert, setOuvert] = useState(false);
  const [form, setForm] = useState({
    modele: "", stockage: "", panne_achat: "ecran", prix_achat: "",
    date_achat: aujourdhui(), cout_pieces: "0", pieces_remplacees: "",
    prix_vente: "", date_vente: aujourdhui(), plateforme_vente: "vinted",
    retour_sav: false, cout_sav: "0",
  });
  const [erreur, setErreur] = useState("");

  function charger() {
    api.get("/historique").then(setItems).catch(() => setItems([]));
  }
  useEffect(charger, []);

  /** Saisie manuelle complète d'une vente. */
  async function ajouter(e) {
    e.preventDefault();
    setErreur("");
    try {
      await api.post("/historique", {
        ...form,
        prix_achat: Number(form.prix_achat),
        cout_pieces: Number(form.cout_pieces || 0),
        prix_vente: Number(form.prix_vente),
        cout_sav: Number(form.cout_sav || 0),
        retour_sav: form.retour_sav ? 1 : 0,
      });
      setForm({ ...form, modele: "", stockage: "", prix_achat: "", prix_vente: "",
        cout_pieces: "0", cout_sav: "0", pieces_remplacees: "", retour_sav: false });
      setOuvert(false);
      charger();
    } catch (err) {
      setErreur(err.message);
    }
  }

  async function supprimer(id) {
    await api.del(`/historique/${id}`);
    charger();
  }

  if (items === null) return <Chargement />;

  // Totaux calculés.
  const nb = items.length;
  const margeTotale = items.reduce((s, i) => s + (i.marge_reelle || 0), 0);
  const margeMoy = nb ? margeTotale / nb : 0;
  const nbSav = items.filter((i) => i.retour_sav).length;
  const tauxSav = nb ? (nbSav / nb) * 100 : 0;

  return (
    <>
      <TitreSection titre="Historique" sous="Téléphones vendus et marge réelle (vente − achat − pièces − SAV)." />

      {/* Totaux */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <div className="text-sm text-muted">Ventes</div>
          <div className="text-2xl font-semibold text-ink mt-1">{nb}</div>
        </Card>
        <Card>
          <div className="text-sm text-muted">Marge totale</div>
          <div className={`text-2xl font-semibold mt-1 ${margeTotale >= 0 ? "text-positif" : "text-negatif"}`}>
            {euros(margeTotale)}
          </div>
        </Card>
        <Card>
          <div className="text-sm text-muted">Marge moyenne</div>
          <div className="text-2xl font-semibold text-ink mt-1">{euros(margeMoy)}</div>
        </Card>
        <Card>
          <div className="text-sm text-muted">Taux retour SAV</div>
          <div className="text-2xl font-semibold text-ink mt-1">{tauxSav.toFixed(0)}%</div>
        </Card>
      </div>

      <div className="flex justify-end mb-4">
        <Bouton onClick={() => setOuvert(!ouvert)}>
          {ouvert ? "Fermer" : "Saisir une vente passée"}
        </Bouton>
      </div>

      {erreur ? (
        <div className="mb-4 text-sm text-negatif bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {erreur}
        </div>
      ) : null}

      {/* Formulaire de saisie manuelle */}
      {ouvert ? (
        <Card className="mb-6">
          <form onSubmit={ajouter} className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Champ label="Modèle">
              <Input required value={form.modele}
                onChange={(e) => setForm({ ...form, modele: e.target.value })} placeholder="iPhone 13" />
            </Champ>
            <Champ label="Stockage">
              <Input value={form.stockage}
                onChange={(e) => setForm({ ...form, stockage: e.target.value })} placeholder="128 Go" />
            </Champ>
            <Champ label="Panne">
              <Select value={form.panne_achat}
                onChange={(e) => setForm({ ...form, panne_achat: e.target.value })}>
                {PANNES.map((p) => <option key={p} value={p}>{libellePanne(p)}</option>)}
              </Select>
            </Champ>
            <Champ label="Pièces remplacées">
              <Input value={form.pieces_remplacees}
                onChange={(e) => setForm({ ...form, pieces_remplacees: e.target.value })} />
            </Champ>
            <Champ label="Prix achat (€)">
              <Input required type="number" min="0" value={form.prix_achat}
                onChange={(e) => setForm({ ...form, prix_achat: e.target.value })} />
            </Champ>
            <Champ label="Coût pièces (€)">
              <Input type="number" min="0" value={form.cout_pieces}
                onChange={(e) => setForm({ ...form, cout_pieces: e.target.value })} />
            </Champ>
            <Champ label="Date achat">
              <Input type="date" value={form.date_achat}
                onChange={(e) => setForm({ ...form, date_achat: e.target.value })} />
            </Champ>
            <Champ label="Prix vente (€)">
              <Input required type="number" min="0" value={form.prix_vente}
                onChange={(e) => setForm({ ...form, prix_vente: e.target.value })} />
            </Champ>
            <Champ label="Date vente">
              <Input type="date" value={form.date_vente}
                onChange={(e) => setForm({ ...form, date_vente: e.target.value })} />
            </Champ>
            <Champ label="Coût SAV (€)">
              <Input type="number" min="0" value={form.cout_sav}
                onChange={(e) => setForm({ ...form, cout_sav: e.target.value })} />
            </Champ>
            <label className="flex items-center gap-2 text-sm text-ink mt-7">
              <input type="checkbox" checked={form.retour_sav}
                onChange={(e) => setForm({ ...form, retour_sav: e.target.checked })} />
              Retour SAV
            </label>
            <div className="col-span-2 md:col-span-4">
              <Bouton type="submit" variante="success">Enregistrer la vente</Bouton>
            </div>
          </form>
        </Card>
      ) : null}

      {/* Tableau historique */}
      {!nb ? (
        <Vide texte="Aucune vente enregistrée. Saisissez vos ventes passées pour activer les prédictions." />
      ) : (
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted border-b border-line text-xs uppercase tracking-wide">
                <th className="py-3 px-4">Modèle</th>
                <th className="py-3 px-2">Panne</th>
                <th className="py-3 px-2">Achat</th>
                <th className="py-3 px-2">Pièces</th>
                <th className="py-3 px-2">Vente</th>
                <th className="py-3 px-2">SAV</th>
                <th className="py-3 px-2">Marge</th>
                <th className="py-3 px-2">Délai</th>
                <th className="py-3 px-2"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((h) => (
                <tr key={h.id} className="border-b border-line/70 hover:bg-app">
                  <td className="py-3 px-4 font-medium text-ink">
                    {h.modele} <span className="text-muted font-normal">{h.stockage}</span>
                  </td>
                  <td className="py-3 px-2 text-muted">{libellePanne(h.panne_achat)}</td>
                  <td className="py-3 px-2">{euros(h.prix_achat)}</td>
                  <td className="py-3 px-2">{euros(h.cout_pieces)}</td>
                  <td className="py-3 px-2">{euros(h.prix_vente)}</td>
                  <td className="py-3 px-2">{h.retour_sav ? `Oui (${euros(h.cout_sav)})` : "—"}</td>
                  <td className={`py-3 px-2 font-semibold ${h.marge_reelle >= 0 ? "text-positif" : "text-negatif"}`}>
                    {euros(h.marge_reelle)}
                  </td>
                  <td className="py-3 px-2 text-muted">
                    {h.delai_revente_jours != null ? `${h.delai_revente_jours} j` : "—"}
                  </td>
                  <td className="py-3 px-2">
                    <button onClick={() => supprimer(h.id)}
                      className="text-negatif hover:underline text-xs">Supprimer</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </>
  );
}
