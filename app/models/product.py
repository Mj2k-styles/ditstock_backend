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

    # Catégorie et fournisseur principal (facultatifs)
    category_id = db.Column(db.Integer, nullable=True)
    supplier_id = db.Column(
        db.Integer, db.ForeignKey("suppliers.id"), nullable=True, index=True
    )

    # Unité de gestion (pièce, kg, litre, carton...)
    unit = db.Column(db.String(20), nullable=False, default="pièce")

    # Prix d'achat unitaire : sert à calculer la valeur du stock
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    # Prix de vente unitaire (facultatif)
    sale_price = db.Column(db.Numeric(10, 2), nullable=True)

    # Quantité minimale souhaitée en stock
    minimum_stock = db.Column(db.Integer, nullable=False, default=0)

    # Adresse de l'image du produit (facultative)
    image_url = db.Column(db.String(500), nullable=True)

    # Indique si le produit est archivé
    is_archived = db.Column(db.Boolean, nullable=False, default=False)
