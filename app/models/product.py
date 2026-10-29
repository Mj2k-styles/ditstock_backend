
from app import db


class Product(db.Model):
    # Nom de la table dans la base de données
    __tablename__ = "products"

    # Identifiant unique
    id = db.Column(db.Integer, primary_key=True)

    # Référence unique du produit
    sku = db.Column(db.String(50), unique=True, nullable=False)

    # Nom du produit
    name = db.Column(db.String(150), nullable=False)

    # Description facultative
    description = db.Column(db.Text, nullable=True)

    # Identifiant de la catégorie
    category_id = db.Column(db.Integer, nullable=True)

    # Prix unitaire
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    # Quantité minimale souhaitée en stock
    minimum_stock = db.Column(db.Integer, nullable=False, default=0)

    # Indique si le produit est archivé
    is_archived = db.Column(db.Boolean, nullable=False, default=False)
