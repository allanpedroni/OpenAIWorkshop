# Multi-stage Dockerfile for OpenAI Workshop Application
# Stage 1: Build React Frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY applications/react-frontend/package*.json ./

# Install ALL dependencies (including dev deps needed for build)
RUN npm ci

# Copy frontend source
COPY applications/react-frontend/ ./

# Build React app
RUN npm run build

# Stage 2: Python Backend with Frontend Assets
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS backend

WORKDIR /app

# Copy backend requirements
COPY applications/requirements.txt applications/pyproject.toml ./

# Set UV environment variables
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install Python dependencies with uv (exclude Windows-specific packages)
RUN --mount=type=cache,target=/root/.cache/uv \
    grep -v "pywin32" requirements.txt > requirements-linux.txt && \
    uv pip install --system -r requirements-linux.txt

# Copy backend source
COPY applications/backend.py applications/utils.py ./

# Copy ONLY agent_framework directory (not all agents)
COPY agents/__init__.py /app/agents/__init__.py
COPY agents/agent_framework /app/agents/agent_framework
COPY agents/base_agent.py /app/agents/base_agent.py

# Copy observability module
COPY observability /app/observability

# Copy built frontend from previous stage (Vite outputs to 'dist')
COPY --from=frontend-builder /app/frontend/dist ./static

# Expose ports
# Port 7000: Backend API
# Port 3000: Frontend (served by backend)
EXPOSE 3000

# Environment variables (overridden at runtime)
ENV PYTHONUNBUFFERED=1
ENV PORT=3000

# Run backend with uvicorn
CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "3000"]
