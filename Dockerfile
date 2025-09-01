# Multi-stage build: build React frontend, then package with Python backend.
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ .
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

# System deps (add build-essential if you later need native builds)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && pip install gunicorn

# Copy backend source
COPY backend/ ./backend

# Copy built frontend assets
COPY --from=frontend-builder /app/frontend/dist ./frontend_dist

ENV PORT=8080 \
    FLASK_ENV=production \
    FRONTEND_DIST=/app/frontend_dist

WORKDIR /app/backend
EXPOSE 8080

# Gunicorn (thread workers good for lightweight IO bound app)
# Use the runtime PORT provided by hosting platforms (e.g. Railway) falling back to 8080.
# We wrap in sh -c so the env var is expanded at container start.
CMD ["sh", "-c", "gunicorn -w 3 -k gthread --threads 4 -b 0.0.0.0:${PORT:-8080} app:app"]
