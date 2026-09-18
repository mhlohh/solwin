# Solwin Backend API — production container
# Multi-stage: uv resolves from the lockfile, runtime is a slim venv-only image.

FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install dependencies into an isolated virtualenv first (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Install the application itself into the same venv
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
RUN uv sync --frozen --no-dev

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd --system app && useradd --system --ingroup app app

WORKDIR /app
COPY --from=builder /app /app
RUN mkdir -p /app/storage/attachments && chown -R app:app /app/storage

USER app

EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=3)" || exit 1

# Startup wrapper: wait for the database, apply migrations if DATABASE_URL is a
# postgres URL, then boot the API. Cloud Run / GKE set DATABASE_URL via env.
CMD ["sh", "-c", "python scripts/docker_start.py"]
