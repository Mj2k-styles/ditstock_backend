from app.routes.health import health_ns
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_restx import Api
from dotenv import load_dotenv
import os

# Charger les variables du fichier .env
load_dotenv()

# Initialiser les extensions
db = SQLAlchemy()
migrate = Migrate()


def create_app():
    # Créer l'application Flask
    app = Flask(__name__)

    # Configuration de l'application
    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY", "cle-temporaire-de-developpement"
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///gestion_stock.db"

    # Initialiser les extensions avec l'application
    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
     
     from app.models import product

    # Préparer la documentation de l'API
    api = Api(
        app,
        title="API Gestion de Stock",
        version="1.0",
        description="API de gestion des produits, catégories et fournisseurs"
    )
    api.add_namespace(health_ns, path="/health")

    return app
# Importer les modèles après la création des extensions
from app.models.product import Product
