/**
 * Stock.jsx — Stock personnel : téléphones achetés / en réparation, avec
 * ajout, mise à jour du statut, vente (passage en historique) et suppression.
 */
import React, { useEffect, useState } from "react";
import { api, euros, libellePanne } from "../api.js";
import {
  Card, TitreSection, Chargement, Vide, Bouton, Champ, Input, Select, StatutBadge,
} from "../components/ui.jsx";

const PANNES = ["ecran", "vitre_arriere", "batterie", "faceid", "camera", "charge",
  "ne_sallume_plus", "pour_pieces", "inconnue"];
const STATUTS = ["en_reparation", "repare", "en_vente", "vendu"];

/** Date du jour au format YYYY-MM-DD. */
function aujourdhui() {
  return new Date().toISOString().slice(0, 10);
}

export default function Stock() {
  const [items, setItems] = useState(null);
  const [form, setForm] = useState({
    modele: "", stockage: "", couleur: "", panne_achat: "ecran",
    prix_achat: "", date_achat: aujourdhui(), plateforme_achat: "leboncoin",
    pieces_remplacees: "", cout_pieces: "0", statut: "en_reparation", notes: "",
  });
  const [venteId, setVenteId] = useState(null);
  const [vente, setVente] = useState({
    prix_vente: "", date_vente: aujourdhui(), plateforme_vente: "leboncoin",
    retour_sav: false, cout_sav: "0",
  });
  const [erreur, setErreur] = useState("");

  /** Recharge la liste du stock. */
  function charger() {
    api.get("/stock").then(setItems).catch(() => setItems([]));
  }
  useEffect(charger, []);

  /** Ajoute un téléphone au stock. */
  async function ajouter(e) {
    e.preventDefault();
    setErreur("");
    try {
      await api.post("/stock", {
        ...form,
        prix_achat: Number(form.prix_achat),
        cout_pieces: Number(form.cout_pieces || 0),
      });
      setForm({ ...form, modele: "", stockage: "", couleur: "", prix_achat: "",
        pieces_remplacees: "", cout_pieces: "0", notes: "" });
      charger();
    } catch (err) {
      setErreur(err.message);
    }
  }

  /** Met à jour le statut d'une fiche. */
  async function changerStatut(item, statut) {
    await api.put(`/stock/${item.id}`, { statut });
    charger();
  }

  /** Supprime une fiche. */
  async function supprimer(id) {
    await api.del(`/stock/${id}`);
    charger();
  }

  /** Valide la vente d'un téléphone. */
  async function validerVente(e) {
    e.preventDefault();
    setErreur("");
    try {
      await api.post(`/stock/${venteId}/vendre`, {
        prix_vente: Number(vente.prix_vente),
        date_vente: vente.date_vente,
        plateforme_vente: vente.plateforme_vente,
        retour_sav: vente.retour_sav ? 1 : 0,
        cout_sav: Number(vente.cout_sav || 0),
      });
      setVenteId(null);
      setVente({ ...vente, prix_vente: "", cout_sav: "0", retour_sav: false });
      charger();
    } catch (err) {
      setErreur(err.message);
    }
  }

  const enCours = (items || []).filter((i) => i.statut !== "vendu");

  return (
    <>
      <TitreSection titre="Stock personnel" sous="Téléphones achetés et en cours de traitement." />

      {erreur ? (
        <div className="mb-4 text-sm text-negatif bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {erreur}
        </div>
      ) : null}

      {/* Formulaire d'ajout */}
      <Card className="mb-6">
        <h3 className="font-semibold text-ink mb-4">Ajouter un achat</h3>
        <form onSubmit={ajouter} className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Champ label="Modèle">
            <Input required value={form.modele}
              onChange={(e) => setForm({ ...form, modele: e.target.value })}
              placeholder="iPhone 13" />
          </Champ>
          <Champ label="Stockage">
            <Input value={form.stockage}
              onChange={(e) => setForm({ ...form, stockage: e.target.value })}
              placeholder="128 Go" />
          </Champ>
          <Champ label="Couleur">
            <Input value={form.couleur}
              onChange={(e) => setForm({ ...form, couleur: e.target.value })} />
          </Champ>
          <Champ label="Panne">
            <Select value={form.panne_achat}
              onChange={(e) => setForm({ ...form, panne_achat: e.target.value })}>
              {PANNES.map((p) => <option key={p} value={p}>{libellePanne(p)}</option>)}
            </Select>
          </Champ>
          <Champ label="Prix achat (€)">
            <Input required type="number" min="0" value={form.prix_achat}
              onChange={(e) => setForm({ ...form, prix_achat: e.target.value })} />
          </Champ>
          <Champ label="Date achat">
            <Input type="date" value={form.date_achat}
              onChange={(e) => setForm({ ...form, date_achat: e.target.value })} />
          </Champ>
          <Champ label="Coût pièces (€)">
            <Input type="number" min="0" value={form.cout_pieces}
              onChange={(e) => setForm({ ...form, cout_pieces: e.target.value })} />
          </Champ>
          <Champ label="Pièces remplacées">
            <Input value={form.pieces_remplacees}
              onChange={(e) => setForm({ ...form, pieces_remplacees: e.target.value })}
              placeholder="écran, batterie…" />
          </Champ>
          <div className="col-span-2 md:col-span-4">
            <Champ label="Description (pour reconnaître l'iPhone)">
              <Input value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                placeholder="ex : iPhone 13 noir, petite rayure coin haut, vendeur Lyon, lien annonce…" />
            </Champ>
          </div>
          <div className="col-span-2 md:col-span-4">
            <Bouton type="submit" variante="success">Ajouter au stock</Bouton>
          </div>
        </form>
      </Card>

      {/* Liste du stock */}
      {items === null ? (
        <Chargement />
      ) : !enCours.length ? (
        <Vide texte="Stock vide. Ajoutez un téléphone acheté ci-dessus." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {enCours.map((item) => (
            <Card key={item.id} className="flex flex-col gap-4">
              <div className="flex justify-between items-start">
                <div>
                  <div className="font-semibold text-ink">
                    {item.modele} <span className="text-muted font-normal">{item.stockage}</span>
                  </div>
                  <div className="text-xs text-muted mt-1">
                    {libellePanne(item.panne_achat)} · acheté le {item.date_achat}
                  </div>
                </div>
                <StatutBadge statut={item.statut} />
              </div>

              <div className="grid grid-cols-3 gap-2 text-center text-sm">
                <div className="rounded-lg bg-app py-2.5">
                  <div className="text-[11px] text-muted">Achat</div>
                  <div className="font-semibold text-ink">{euros(item.prix_achat)}</div>
                </div>
                <div className="rounded-lg bg-app py-2.5">
                  <div className="text-[11px] text-muted">Pièces</div>
                  <div className="font-semibold text-ink">{euros(item.cout_pieces)}</div>
                </div>
                <div className="rounded-lg bg-app py-2.5">
                  <div className="text-[11px] text-muted">Prix de revient</div>
                  <div className="font-semibold text-ink">
                    {euros((item.prix_achat || 0) + (item.cout_pieces || 0))}
                  </div>
                </div>
              </div>

              {venteId === item.id ? (
                <form onSubmit={validerVente} className="grid grid-cols-2 gap-3 bg-app p-4 rounded-lg">
                  <Champ label="Prix vente (€)">
                    <Input required type="number" min="0" value={vente.prix_vente}
                      onChange={(e) => setVente({ ...vente, prix_vente: e.target.value })} />
                  </Champ>
                  <Champ label="Date vente">
                    <Input type="date" value={vente.date_vente}
                      onChange={(e) => setVente({ ...vente, date_vente: e.target.value })} />
                  </Champ>
                  <Champ label="Coût SAV (€)">
                    <Input type="number" min="0" value={vente.cout_sav}
                      onChange={(e) => setVente({ ...vente, cout_sav: e.target.value })} />
                  </Champ>
                  <label className="flex items-center gap-2 text-sm text-ink mt-7">
                    <input type="checkbox" checked={vente.retour_sav}
                      onChange={(e) => setVente({ ...vente, retour_sav: e.target.checked })} />
                    Retour SAV
                  </label>
                  <div className="col-span-2 flex gap-2">
                    <Bouton type="submit" variante="success">Valider la vente</Bouton>
                    <Bouton type="button" variante="ghost" onClick={() => setVenteId(null)}>
                      Annuler
                    </Bouton>
                  </div>
                </form>
              ) : (
                <div className="flex flex-wrap items-center gap-2">
                  <Bouton variante="success" onClick={() => setVenteId(item.id)}>
                    Marquer vendu
                  </Bouton>
                  <Select value={item.statut} onChange={(e) => changerStatut(item, e.target.value)}>
                    {STATUTS.filter((s) => s !== "vendu").map((s) => (
                      <option key={s} value={s}>{s.replace("_", " ")}</option>
                    ))}
                  </Select>
                  <Bouton variante="danger" onClick={() => supprimer(item.id)}>
                    Supprimer
                  </Bouton>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
