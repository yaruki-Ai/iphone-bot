"""
make_icon.py — Génère l'icône Windows (.ico) de l'exécutable à partir du logo.

Dessine le même logo que le favicon (carré arrondi bleu + flèche montante
blanche) et l'enregistre en multi-résolutions dans assets/icon.ico.
À lancer une fois (build) :  .venv\\Scripts\\python.exe -m scripts.make_icon
Nécessite Pillow (utilisé uniquement au build, pas embarqué dans l'exe).
"""

from pathlib import Path

from PIL import Image, ImageDraw

ACCENT = (47, 109, 240, 255)   # #2f6df0
BLANC = (255, 255, 255, 255)
TAILLE = 512


def dessiner() -> Image.Image:
    """Dessine le logo en 512x512 (fond transparent + tuile arrondie + flèche)."""
    img = Image.new("RGBA", (TAILLE, TAILLE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Tuile arrondie bleue.
    d.rounded_rectangle([0, 0, TAILLE, TAILLE], radius=112, fill=ACCENT)
    # Courbe montante (chart) blanche.
    d.line([(116, 344), (210, 256), (298, 306), (398, 176)],
           fill=BLANC, width=38, joint="curve")
    # Tête de flèche.
    d.polygon([(356, 160), (416, 150), (412, 212)], fill=BLANC)
    return img


def main() -> None:
    """Enregistre l'icône multi-tailles."""
    assets = Path(__file__).resolve().parent.parent / "assets"
    assets.mkdir(exist_ok=True)
    img = dessiner()
    chemin = assets / "icon.ico"
    img.save(chemin, format="ICO",
             sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    img.save(assets / "icon.png")
    print(f"Icône générée : {chemin}")


if __name__ == "__main__":
    main()
