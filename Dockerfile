# Étape 1 : installation des dépendances
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Étape 2 : image finale légère
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /srv/backend

COPY --from=builder /install /usr/local
RUN useradd --create-home appuser && chown appuser:appuser /srv/backend
COPY --chown=appuser:appuser . .
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health/')" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "app:create_app()"]
