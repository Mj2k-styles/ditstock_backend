import os

import click
from flask.cli import with_appcontext
from marshmallow import ValidationError

from app import db
from app.constants import (
    MOVEMENT_ENTREE,
    MOVEMENT_SORTIE,
    ROLE_ADMIN,
    ROLE_GESTIONNAIRE,
    ROLE_MAGASINIER,
)
from app.models.category import Category
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.user import User
from app.models.warehouse import Warehouse
from app.schemas.user_schema import validate_password


@click.command("create-admin")
@click.option("--email", prompt=True, help="E-mail de l'administrateur")
@click.option("--full-name", prompt="Nom complet", help="Nom complet")
@click.password_option(help="Mot de passe (8 caractères minimum)")
@with_appcontext
def create_admin(email, full_name, password):
    """Crée le premier compte administrateur."""
    email = email.strip().lower()

    try:
        validate_password(password)
    except ValidationError as err:
        raise click.ClickException(err.messages[0])

    if User.query.filter_by(email=email).first():
        raise click.ClickException("Cet e-mail existe déjà")

    admin = User(email=email, full_name=full_name, role=ROLE_ADMIN)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()

    click.echo(f"Administrateur créé : {email}")


# --- Données de démonstration (développement et tests de bout en bout) ---

DEMO_USERS = [
    ("admin@ditstock.local", "Admin Démo", ROLE_ADMIN),
    ("gestionnaire@ditstock.local", "Gestionnaire Démo", ROLE_GESTIONNAIRE),
    ("magasinier@ditstock.local", "Magasinier Démo", ROLE_MAGASINIER),
]
DEMO_CATEGORIES = ["Informatique", "Bureautique", "Entretien"]
DEMO_SUPPLIERS = [
    ("Dakar Informatique", "Moussa Ndiaye", "+221 33 800 00 01"),
    ("Papeterie du Plateau", "Aïssatou Ba", "+221 33 800 00 02"),
]
DEMO_WAREHOUSES = [("Entrepôt central", "Dakar"), ("Dépôt Thiès", "Thiès")]
# sku, nom, catégorie, fournisseur, unité, prix d'achat, prix de vente, seuil
DEMO_PRODUCTS = [
    ("INFO-001", "Clavier sans fil", 0, 0, "pièce", 15000, 22000, 10),
    ("INFO-002", "Souris optique", 0, 0, "pièce", 6000, 9500, 15),
    ("INFO-003", "Écran 24 pouces", 0, 0, "pièce", 85000, 120000, 5),
    ("BUR-001", "Ramette papier A4", 1, 1, "paquet", 3000, 4500, 40),
    ("BUR-002", "Stylos bille (boîte de 50)", 1, 1, "boîte", 5000, 7500, 12),
    ("ENT-001", "Gants de manutention", 2, None, "paire", 1500, 2500, 50),
]
# sku, entrepôt, quantité reçue, quantité sortie
DEMO_STOCK = [
    ("INFO-001", 0, 30, 4), ("INFO-002", 0, 40, 30), ("INFO-003", 0, 8, 6),
    ("BUR-001", 1, 120, 20), ("BUR-002", 1, 10, 0), ("ENT-001", 0, 60, 12),
]


def _get_or_create(model, defaults=None, **keys):
    obj = model.query.filter_by(**keys).first()
    if obj is None:
        obj = model(**keys, **(defaults or {}))
        db.session.add(obj)
        db.session.flush()
    return obj


@click.command("seed-demo")
@click.option("--password", envvar="DEMO_PASSWORD", default="Demo12345!",
              show_default=True, help="Mot de passe des comptes de démonstration")
@with_appcontext
def seed_demo(password):
    """Remplit une base VIDE avec un jeu de démonstration (idempotent)."""
    from app.services.movement_service import create_movement

    if os.getenv("ALLOW_DEMO_SEED") != "1":
        raise click.ClickException(
            "Refusé : définissez ALLOW_DEMO_SEED=1 (jamais en production)."
        )

    users = []
    for email, name, role in DEMO_USERS:
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(email=email, full_name=name, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
        users.append(user)

    categories = [_get_or_create(Category, name=n) for n in DEMO_CATEGORIES]
    suppliers = [
        _get_or_create(Supplier, {"contact": c, "phone": p}, name=n)
        for n, c, p in DEMO_SUPPLIERS
    ]
    warehouses = [
        _get_or_create(Warehouse, {"location": loc}, name=n)
        for n, loc in DEMO_WAREHOUSES
    ]

    new_products = set()
    for sku, name, cat, sup, unit, buy, sell, minimum in DEMO_PRODUCTS:
        if Product.query.filter_by(sku=sku).first() is None:
            db.session.add(Product(
                sku=sku, name=name, unit=unit, unit_price=buy, sale_price=sell,
                minimum_stock=minimum, category_id=categories[cat].id,
                supplier_id=suppliers[sup].id if sup is not None else None,
            ))
            new_products.add(sku)
    db.session.commit()

    # Stock initial : uniquement par des mouvements, comme dans l'application
    admin = users[0]
    for sku, wh, received, issued in DEMO_STOCK:
        if sku not in new_products:
            continue
        product = Product.query.filter_by(sku=sku).one()
        create_movement({
            "type": MOVEMENT_ENTREE, "product_id": product.id,
            "warehouse_id": warehouses[wh].id, "quantity": received,
            "reference": "BL-DEMO", "supplier_id": product.supplier_id,
        }, admin)
        if issued:
            create_movement({
                "type": MOVEMENT_SORTIE, "product_id": product.id,
                "warehouse_id": warehouses[wh].id, "quantity": issued,
                "reason": "Vente",
            }, admin)

    click.echo(
        f"Démonstration prête : {len(new_products)} produit(s) ajouté(s). "
        f"Comptes : {', '.join(u.email for u in users)}"
    )
