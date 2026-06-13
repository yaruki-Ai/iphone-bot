"""
models.py — Schémas Pydantic pour les entrées/sorties de l'API.

Définit les structures attendues par les endpoints d'écriture (stock, ventes,
historique). Les prix sont en euros, les dates en texte ISO ('YYYY-MM-DD').
"""

from typing import Optional

from pydantic import BaseModel, Field


class StockCreate(BaseModel):
    """Saisie d'un téléphone acheté qui entre en stock."""
    modele: str = Field(..., description="Ex : 'iPhone 13'")
    stockage: Optional[str] = Field(None, description="Ex : '128 Go'")
    couleur: Optional[str] = None
    panne_achat: Optional[str] = Field(None, description="Panne au moment de l'achat")
    prix_achat: float = Field(..., ge=0)
    date_achat: str = Field(..., description="Date d'achat ISO (YYYY-MM-DD)")
    plateforme_achat: Optional[str] = None
    annonce_id: Optional[int] = None
    pieces_remplacees: Optional[str] = None
    cout_pieces: float = Field(0, ge=0)
    statut: str = Field("en_reparation")
    notes: Optional[str] = None


class StockUpdate(BaseModel):
    """Mise à jour partielle d'une fiche stock."""
    modele: Optional[str] = None
    stockage: Optional[str] = None
    couleur: Optional[str] = None
    panne_achat: Optional[str] = None
    prix_achat: Optional[float] = Field(None, ge=0)
    date_achat: Optional[str] = None
    plateforme_achat: Optional[str] = None
    pieces_remplacees: Optional[str] = None
    cout_pieces: Optional[float] = Field(None, ge=0)
    statut: Optional[str] = None
    notes: Optional[str] = None


class VenteCreate(BaseModel):
    """Saisie de la vente d'un téléphone du stock (passe en historique)."""
    prix_vente: float = Field(..., ge=0)
    date_vente: str = Field(..., description="Date de vente ISO (YYYY-MM-DD)")
    plateforme_vente: Optional[str] = None
    retour_sav: int = Field(0, ge=0, le=1)
    cout_sav: float = Field(0, ge=0)
    notes: Optional[str] = None


class HistoriqueCreate(BaseModel):
    """Saisie manuelle complète d'une vente passée (achat + vente d'un coup)."""
    modele: str
    stockage: Optional[str] = None
    couleur: Optional[str] = None
    panne_achat: Optional[str] = None
    prix_achat: float = Field(..., ge=0)
    date_achat: str
    pieces_remplacees: Optional[str] = None
    cout_pieces: float = Field(0, ge=0)
    prix_vente: float = Field(..., ge=0)
    date_vente: str
    plateforme_vente: Optional[str] = None
    retour_sav: int = Field(0, ge=0, le=1)
    cout_sav: float = Field(0, ge=0)
    notes: Optional[str] = None
