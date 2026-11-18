import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_restx import Api
from flask_sqlalchemy import SQLAlchemy

# Charger les variables du fichier .env
load_dotenv()

# Initialiser les extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


def _env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "oui")


def create_app(test_config=None):
    # Créer l'application Flask
    app = Flask(__name__)

    # Configuration
    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY", "cle-temporaire-de-developpement"
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///gestion_stock.db"
    )
    # Vérifie chaque connexion du pool avant usage : après un redémarrage de PostgreSQL
    # (pod remplacé, redéploiement), les connexions mortes sont remplacées au lieu de
    # provoquer une erreur 500.
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

    # Configuration JWT : clé de signature et durée de vie des tokens
    app.config["JWT_SECRET_KEY"] = os.getenv(
        "JWT_SECRET_KEY",
        "cle-jwt-temporaire-de-developpement-a-remplacer"
    )
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=30)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=7)

    # Nombre de tours bcrypt (12 = bon compromis sécurité / vitesse)
    app.config["BCRYPT_ROUNDS"] = 12

    # Adresse publique du frontend (liens envoyés par e-mail)
    app.config["FRONTEND_URL"] = os.getenv(
        "FRONTEND_URL", "http://localhost:8080"
    ).rstrip("/")

    # Durée de validité d'un lien de réinitialisation du mot de passe
    app.config["PASSWORD_RESET_MAX_AGE"] = 30 * 60

    # E-mails (facultatif : sans MAIL_SERVER, rien n'est envoyé)
    app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "")
    app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", "587"))
    app.config["MAIL_USE_TLS"] = _env_bool("MAIL_USE_TLS", True)
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME", "")
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD", "")
    app.config["MAIL_FROM"] = os.getenv("MAIL_FROM", "DitStock <no-reply@ditstock.sn>")

    # Import CSV : taille maximale d'un fichier envoyé
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

    # Surcharger la configuration (utilisé par les tests)
    if test_config:
        app.config.update(test_config)

    # Logs JSON sur la sortie standard (LOG_FORMAT=text pour un format lisible)
    if not app.config.get("TESTING"):
        from app.logging_config import configure_logging
        configure_logging(
            os.getenv("LOG_FORMAT", "json"), os.getenv("LOG_LEVEL", "INFO")
        )

    # Initialiser les extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Documentation Swagger (avec le bouton "Authorize")
    api = Api(
        app,
        title="API Gestion de Stock",
        version="1.0",
        description="API de DitStock : produits, référentiels, mouvements, "
                    "alertes, tableau de bord, exports et journal d'audit",
        authorizations={
            "Bearer": {
                "type": "apiKey",
                "in": "header",
                "name": "Authorization",
                "description": "Saisir : Bearer <access_token>"
            }
        }
    )

    # Charger les modèles
    with app.app_context():
        from app import models  # noqa: F401

    # Enregistrer les routes
    from app.routes.alerts import alerts_ns
    from app.routes.audit import audit_ns
    from app.routes.auth import auth_ns
    from app.routes.categories import categories_ns
    from app.routes.dashboard import dashboard_ns
    from app.routes.exports import exports_ns
    from app.routes.health import health_ns
    from app.routes.movements import movements_ns
    from app.routes.products import products_ns
    from app.routes.suppliers import suppliers_ns
    from app.routes.users import users_ns
    from app.routes.warehouse_stock import warehouse_stocks_ns
    from app.routes.warehouses import warehouses_ns

    api.add_namespace(health_ns, path="/health")
    api.add_namespace(auth_ns, path="/api/auth")
    api.add_namespace(users_ns, path="/api/users")
    api.add_namespace(products_ns, path="/api/products")
    api.add_namespace(categories_ns, path="/api/categories")
    api.add_namespace(suppliers_ns, path="/api/suppliers")
    api.add_namespace(warehouses_ns, path="/api/warehouses")
    api.add_namespace(warehouse_stocks_ns, path="/api/warehouse-stocks")
    api.add_namespace(movements_ns, path="/api/movements")
    api.add_namespace(alerts_ns, path="/api/alerts")
    api.add_namespace(dashboard_ns, path="/api/dashboard")
    api.add_namespace(exports_ns, path="/api/exports")
    api.add_namespace(audit_ns, path="/api/audit-logs")

    # Commandes CLI (flask create-admin, flask seed-demo)
    from app.cli import create_admin, seed_demo
    app.cli.add_command(create_admin)
    app.cli.add_command(seed_demo)

    # Métriques Prometheus sur /metrics (après l'enregistrement des routes).
    # Sous Gunicorn (plusieurs processus), les compteurs sont partagés via
    # PROMETHEUS_MULTIPROC_DIR (voir gunicorn.conf.py).
    if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
        from prometheus_flask_exporter.multiprocess import (
            GunicornInternalPrometheusMetrics,
        )
        GunicornInternalPrometheusMetrics(app)
    else:
        from prometheus_flask_exporter import PrometheusMetrics
        PrometheusMetrics(app)

    return app
