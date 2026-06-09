FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements-cloudrun.txt .
RUN pip install --no-cache-dir -r requirements-cloudrun.txt

COPY backend/ .

COPY start-local-runner.bat .
COPY register-runner-protocol.bat .
COPY register-runner-protocol.ps1 .

RUN ln -sfn /app /app/backend \
    && mkdir -p uploads logs \
    && useradd -m appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
