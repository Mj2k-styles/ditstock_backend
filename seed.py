"""Données de démonstration pour les produits.

Usage : python seed.py
Idempotent : un produit dont le SKU existe déjà n'est pas recréé.
"""
from decimal import Decimal

from app import create_app, db
from app.models.product import Product

PRODUCTS = [
    ("INFO-001", "Clavier sans fil", "Clavier AZERTY sans fil, USB", 29.90, 10),
    ("INFO-002", "Souris optique", "Souris optique 1600 DPI", 14.50, 15),
    ("INFO-003", "Écran 24 pouces", "Écran Full HD IPS 24\"", 139.00, 5),
    ("INFO-004", "Câble HDMI 2 m", "Câble HDMI haute vitesse", 8.90, 20),
    ("INFO-005", "Clé USB 64 Go", "Clé USB 3.0, 64 Go", 11.99, 25),
    ("BUR-001", "Ramette papier A4", "500 feuilles, 80 g/m²", 4.80, 40),
    ("BUR-002", "Stylos bille (boîte de 50)", "Encre bleue", 9.50, 12),
    ("BUR-003", "Classeur à levier", "Dos 80 mm, format A4", 3.20, 30),
    ("BUR-004", "Agrafeuse de bureau", "Capacité 25 feuilles", 6.75, 8),
    ("ENT-001", "Gants de manutention", "Taille L, paire", 2.90, 50),
    ("ENT-002", "Chariot de transport", "Charge max 150 kg", 89.00, 3),
    ("ENT-003", "Ruban adhésif d'emballage", "Rouleau 50 mm x 66 m", 1.90, 60),
]


def seed():
    app = create_app()
    with app.app_context():
        # Pas de migrations dans le dépôt pour l'instant : on crée les tables si besoin.
        db.create_all()

        existing = {sku for (sku,) in db.session.query(Product.sku).all()}
        created = 0
        for sku, name, description, price, minimum_stock in PRODUCTS:
            if sku in existing:
                continue
            db.session.add(
                Product(
                    sku=sku,
                    name=name,
                    description=description,
                    unit_price=Decimal(str(price)),
                    minimum_stock=minimum_stock,
                )
            )
            created += 1
        db.session.commit()
        print(f"{created} produit(s) créé(s), {len(PRODUCTS) - created} déjà présent(s).")


if __name__ == "__main__":
    seed()
