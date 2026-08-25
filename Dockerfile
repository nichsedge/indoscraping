# Multi-stage Enterprise Production Dockerfile for IndoScraping

FROM mcr.microsoft.com/playwright/python:v1.62.0-noble AS base

WORKDIR /app

# Install Astral uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PATH="/app/.venv/bin:$PATH"

# Copy dependency definition manifests
COPY pyproject.toml uv.lock ./
COPY packages/ packages/
COPY src/ src/

# Sync all workspace dependencies
RUN uv sync --frozen --no-cache

# Run non-root user for security compliance
USER pwuser

ENTRYPOINT ["uv", "run", "indoscraping"]
CMD ["--help"]
