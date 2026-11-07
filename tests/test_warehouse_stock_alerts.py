from app import db
from app.models.product import Product


def test_create_warehouse_stock_and_alert(client, app):
    # Créer un entrepôt
    warehouse_response = client.post(
        "/api/warehouses/",
        json={"name": "Entrepôt Test"}
    )
    assert warehouse_response.status_code == 201

    warehouse_id = warehouse_response.json["id"]

    # Créer un produit directement dans la base de test
    with app.app_context():
        product = Product(
            sku="ALERT-001",
            name="Produit test",
            unit_price=1000,
            minimum_stock=5
        )
        db.session.add(product)
        db.session.commit()
        product_id = product.id

    # Enregistrer une quantité inférieure au seuil
    stock_response = client.post(
        "/api/warehouse-stocks/",
        json={
            "warehouse_id": warehouse_id,
            "product_id": product_id,
            "quantity": 2
        }
    )

    assert stock_response.status_code == 201

    # Vérifier l'alerte
    alert_response = client.get("/api/alerts/")

    assert alert_response.status_code == 200
    assert len(alert_response.json) == 1
    assert alert_response.json[0]["quantity"] == 2


def test_reject_negative_stock(client, app):
    warehouse_response = client.post(
        "/api/warehouses/",
        json={"name": "Entrepôt Stock"}
    )
    warehouse_id = warehouse_response.json["id"]

    with app.app_context():
        product = Product(
            sku="NEG-001",
            name="Produit négatif",
            unit_price=500,
            minimum_stock=5
        )
        db.session.add(product)
        db.session.commit()
        product_id = product.id

    response = client.post(
        "/api/warehouse-stocks/",
        json={
            "warehouse_id": warehouse_id,
            "product_id": product_id,
            "quantity": -3
        }
    )

    assert response.status_code == 400