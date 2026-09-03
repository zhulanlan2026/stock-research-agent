FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/apps/backend/src

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
COPY apps/backend /app/apps/backend
COPY apps/xtquant-collector /app/apps/xtquant-collector

RUN uv sync --frozen --no-dev \
    && chmod +x /app/apps/backend/docker-entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

ENTRYPOINT ["/app/apps/backend/docker-entrypoint.sh"]
