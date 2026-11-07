from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_restx import Api
from dotenv import load_dotenv
from datetime import timedelta
import os

# Charger les variables du fichier .env
load_dotenv()

# Initialiser les extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


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

    # Configuration JWT : clé de signature et durée de vie des tokens
    app.config["JWT_SECRET_KEY"] = os.getenv(
        "JWT_SECRET_KEY",
        "cle-jwt-temporaire-de-developpement-a-remplacer"
    )
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=30)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=7)

    # Nombre de tours bcrypt (12 = bon compromis sécurité / vitesse)
    app.config["BCRYPT_ROUNDS"] = 12

    # Surcharger la configuration (utilisé par les tests)
    if test_config:
        app.config.update(test_config)

    # Initialiser les extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)


    # Documentation Swagger

    # Préparer la documentation Swagger (avec le bouton "Authorize")
    api = Api(
        app,
        title="API Gestion de Stock",
        version="1.0",
        description="API de gestion des produits, catégories et fournisseurs",
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
        # Charger les modèles
       # Charger les modèles
    with app.app_context():
        from app.models import product, category, user, supplier, Warehouse, warehouse_stock

    # Enregistrer les routes
    from app.routes.health import health_ns
    from app.routes.products import products_ns
    from app.routes.categories import categories_ns
    from app.routes.suppliers import suppliers_ns
    from app.routes.warehouses import warehouses_ns

    api.add_namespace(health_ns, path="/health")
    api.add_namespace(products_ns, path="/api/products")
    api.add_namespace(categories_ns, path="/api/categories")
    api.add_namespace(suppliers_ns, path="/api/suppliers")
    api.add_namespace(warehouses_ns, path="/api/warehouses")

    from app.routes.auth import auth_ns
    from app.routes.users import users_ns
    from app.routes.warehouse_stock import warehouse_stocks_ns
    from app.routes.alerts import alerts_ns

    api.add_namespace(health_ns, path="/health")
    api.add_namespace(products_ns, path="/api/products")
    api.add_namespace(auth_ns, path="/api/auth")
    api.add_namespace(users_ns, path="/api/users")
    api.add_namespace(warehouse_stocks_ns, path="/api/warehouse-stocks")
    api.add_namespace(alerts_ns, path="/api/alerts")

    # Commandes CLI (flask create-admin)
    from app.cli import create_admin
    app.cli.add_command(create_admin)

    return app
