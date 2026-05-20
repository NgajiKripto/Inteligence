# ============================================
# MemeCoin Intelligence - Multi-stage Dockerfile
# ============================================

# Stage 1: Build frontend
FROM node:18-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Production image
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend code
COPY backend/ /app/backend/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# Create data directories
RUN mkdir -p /app/backend/data/tokens \
             /app/backend/data/signals \
             /app/backend/data/sessions \
             /app/backend/uploads

# Expose ports
EXPOSE 5001 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5001/health || exit 1

# Start backend (frontend served via nginx or directly)
WORKDIR /app/backend
CMD ["python", "run.py"]
