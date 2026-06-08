FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-cloudrun.txt .
RUN pip install --no-cache-dir -r requirements-cloudrun.txt

COPY . .

RUN mkdir -p uploads logs \
    && useradd -m appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["sh", "-c", "python -c \"from app.config import get_settings; s=get_settings(); print(f'ENV={s.environment} DB={s.database_url[:50]}...')\" && uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info 2>&1"
