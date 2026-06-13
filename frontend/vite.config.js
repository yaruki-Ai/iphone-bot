/**
 * vite.config.js — Configuration du build frontend.
 * base './' : les chemins d'assets sont relatifs (compatible service par FastAPI / .exe).
 * proxy : en développement, /api est redirigé vers le backend FastAPI (port 8000).
 */
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "./",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
