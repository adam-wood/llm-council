# Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend

# Clerk publishable key (safe to commit - it's meant to be public)
ENV VITE_CLERK_PUBLISHABLE_KEY=pk_test_ZG9taW5hbnQtcG9sbGl3b2ctNzMuY2xlcmsuYWNjb3VudHMuZGV2JA

COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Production image
FROM python:3.11-slim
WORKDIR /app

# Install uv for faster dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy Python project files
COPY pyproject.toml uv.lock ./
COPY backend/ ./backend/

# Install Python dependencies
RUN uv sync --frozen --no-dev

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Create data directory for persistent storage
RUN mkdir -p /app/data

# Environment variables
ENV PORT=8001
ENV DATA_DIR=/app/data

EXPOSE 8001

# Run the backend (which serves both API and static files)
CMD ["uv", "run", "python", "-m", "backend.main"]
