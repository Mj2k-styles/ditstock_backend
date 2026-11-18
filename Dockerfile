# Étape 1 : installation des dépendances
FROM python:3.15-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Étape 2 : image finale légère
FROM python:3.15-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    LOG_FORMAT=json \
    PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
WORKDIR /srv/backend

COPY --from=builder /install /usr/local
RUN useradd --create-home appuser && chown appuser:appuser /srv/backend
COPY --chown=appuser:appuser . .
RUN chmod +x docker-entrypoint.sh
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health/')" || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:create_app()"]
