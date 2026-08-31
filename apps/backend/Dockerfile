FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/apps/backend/src

WORKDIR /app

COPY apps/backend /app/apps/backend

RUN pip install --no-cache-dir /app/apps/backend

EXPOSE 8000

CMD ["uvicorn", "stock_research.main:app", "--host", "0.0.0.0", "--port", "8000"]
