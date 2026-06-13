/**
 * tailwind.config.js — Palette sobre et professionnelle (claire, reposante).
 * Couleurs neutres + un seul accent bleu discret. Aucun dégradé criard.
 */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        app: "#f5f6f8", // fond général très doux
        surface: "#ffffff", // cartes
        line: "#e6e8ec", // bordures
        ink: "#1f2430", // texte principal
        muted: "#6b7280", // texte secondaire
        accent: "#2f6df0", // accent (bleu calme)
        accentdark: "#1f57c9",
        positif: "#15803d", // marges / ROI
        negatif: "#b91c1c",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
      boxShadow: {
        carte: "0 1px 2px rgba(16, 24, 40, 0.04), 0 1px 3px rgba(16, 24, 40, 0.06)",
      },
    },
  },
  plugins: [],
};
