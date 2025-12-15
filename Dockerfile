# Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend

# Build-time env vars for Vite (passed as Docker build args)
ARG VITE_CLERK_PUBLISHABLE_KEY

COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./

# Create .env file from build arg before building
RUN echo "VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY" > .env.local && \
    echo "Building with VITE_CLERK_PUBLISHABLE_KEY=${VITE_CLERK_PUBLISHABLE_KEY:0:20}..." && \
    npm run build

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
