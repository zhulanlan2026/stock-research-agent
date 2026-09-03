FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/apps/backend/src

WORKDIR /app

COPY apps/backend /app/apps/backend

RUN pip install --no-cache-dir --upgrade pip setuptools wheel "jaraco.context>=6.1.0" \
    && pip install --no-cache-dir /app/apps/backend \
    && pip install --no-cache-dir --upgrade "msgpack>=1.2.1" "setuptools>=78.1.1" \
    && chmod +x /app/apps/backend/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/apps/backend/docker-entrypoint.sh"]
