"""Configuration Gunicorn (production et docker compose)."""
import os
import shutil

from prometheus_client import multiprocess

bind = "0.0.0.0:5000"
workers = int(os.getenv("GUNICORN_WORKERS", "3"))
timeout = 60

# Logs d'accès en JSON sur la sortie standard (lus avec docker compose logs)
accesslog = "-"
errorlog = "-"
access_log_format = (
    '{"time": "%(t)s", "level": "INFO", "logger": "gunicorn.access", '
    '"method": "%(m)s", "path": "%(U)s", "status": %(s)s, '
    '"duration_ms": %(M)s, "remote_ip": "%({x-real-ip}i)s", "user_agent": "%(a)s"}'
)


def on_starting(server):
    # Compteurs Prometheus partagés entre les workers : dossier vidé au démarrage
    path = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if path:
        shutil.rmtree(path, ignore_errors=True)
        os.makedirs(path, exist_ok=True)


def child_exit(server, worker):
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        multiprocess.mark_process_dead(worker.pid)
