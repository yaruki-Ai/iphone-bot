# =============================================================================
# Dockerfile — Déploiement serveur optionnel (alternative au .exe).
# Étape 1 : build du frontend React. Étape 2 : image Python servant le tout.
# =============================================================================

# --- Étape 1 : build du frontend ---
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install --no-fund --no-audit
COPY frontend/ ./
RUN npm run build

# --- Étape 2 : backend Python ---
FROM python:3.11-slim
WORKDIR /app

# Dépendances Python (scrapers via httpx + BeautifulSoup, sans Playwright).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Code backend + frontend buildé.
COPY backend/ ./backend/
COPY --from=frontend /app/frontend/dist ./frontend/dist

# Dossiers persistants (montés en volume via docker-compose).
RUN mkdir -p data logs

ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000
EXPOSE 8000

CMD ["python", "-m", "backend.main"]
