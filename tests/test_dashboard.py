from app import db
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.warehouse_stock import WarehouseStock


def test_dashboard_stats_empty(client):
    response = client.get("/api/dashboard/stats")

    assert response.status_code == 200
    assert response.json == {
        "total_products": 0,
        "stock_value": 0.0,
        "total_alerts": 0
    }


def test_dashboard_stats_with_stock(app, client):
    with app.app_context():
        product1 = Product(
            sku="TEST001",
            name="Ordinateur",
            unit_price=10,
            minimum_stock=5
        )

        product2 = Product(
            sku="TEST002",
            name="Clavier",
            unit_price=5,
            minimum_stock=2
        )

        product_archived = Product(
            sku="TEST003",
            name="Ancien produit",
            unit_price=100,
            minimum_stock=10,
            is_archived=True
        )

        warehouse = Warehouse(
            name="Entrepot Test",
            location="Dakar"
        )

        db.session.add_all([
            product1,
            product2,
            product_archived,
            warehouse
        ])
        db.session.commit()

        stock1 = WarehouseStock(
            warehouse_id=warehouse.id,
            product_id=product1.id,
            quantity=2
        )

        stock2 = WarehouseStock(
            warehouse_id=warehouse.id,
            product_id=product2.id,
            quantity=3
        )

        stock3 = WarehouseStock(
            warehouse_id=warehouse.id,
            product_id=product_archived.id,
            quantity=1
        )

        db.session.add_all([stock1, stock2, stock3])
        db.session.commit()

    response = client.get("/api/dashboard/stats")

    assert response.status_code == 200
    assert response.json["total_products"] == 2
    assert response.json["stock_value"] == 35.0
    assert response.json["total_alerts"] == 1