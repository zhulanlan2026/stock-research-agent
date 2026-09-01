FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/apps/backend/src

WORKDIR /app

COPY apps/backend /app/apps/backend

RUN pip install --no-cache-dir /app/apps/backend \
    && chmod +x /app/apps/backend/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/apps/backend/docker-entrypoint.sh"]
