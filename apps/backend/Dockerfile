FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/apps/backend/src

ARG INSTALL_TORCH=false

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
COPY apps/backend /app/apps/backend
COPY apps/xtquant-collector /app/apps/xtquant-collector

RUN uv sync --frozen --no-dev \
    && if [ "$INSTALL_TORCH" = "true" ]; then \
         uv pip install --python /app/.venv/bin/python "torch>=2.4,<3" --index-url https://download.pytorch.org/whl/cpu; \
       fi \
    && rm -rf /usr/local/lib/python3.10/site-packages/pip* \
              /usr/local/lib/python3.10/site-packages/setuptools* \
              /usr/local/lib/python3.10/site-packages/wheel* \
              /usr/local/lib/python3.10/site-packages/jaraco* \
    && chmod +x /app/apps/backend/docker-entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

ENTRYPOINT ["/app/apps/backend/docker-entrypoint.sh"]
