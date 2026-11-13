#!/bin/sh
# Point d'entrée du conteneur backend.
# RUN_MIGRATIONS=1 : applique les migrations avant de démarrer (docker compose en local).
# SEED_DEMO=1      : ajoute les données de démonstration (jamais en production).
set -e

# Dossier des métriques Prometheus partagées entre les workers Gunicorn
mkdir -p "${PROMETHEUS_MULTIPROC_DIR:-/tmp/prometheus}"

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  flask db upgrade
fi

if [ "${SEED_DEMO:-0}" = "1" ]; then
  ALLOW_DEMO_SEED=1 flask seed-demo
fi

exec "$@"
