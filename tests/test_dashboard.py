from app.models.stock_movement import StockMovement
from app.models.user import User
from app import db
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.warehouse_stock import WarehouseStock
import pytest

pytestmark = pytest.mark.usefixtures("as_gestionnaire")


def test_dashboard_stats_empty(client):
    response = client.get("/api/dashboard/stats")

    assert response.status_code == 200
    assert response.json == {
        "total_products": 0,
        "stock_value": 0.0,
        "total_alerts": 0,
        "movements_today": 0
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
    assert response.json["movements_today"] == 0

def test_dashboard_movements_empty(client):
    response = client.get("/api/dashboard/movements")

    assert response.status_code == 200
    assert response.json == {
    "movements": []
}

def test_dashboard_movements_with_data(app, client, gestionnaire):
    with app.app_context():
        product = Product(
            sku="MOV001",
            name="Ordinateur",
            unit_price=100,
            minimum_stock=5
        )

        warehouse = Warehouse(
            name="Entrepot Mouvement",
            location="Dakar"
        )

        db.session.add_all([product, warehouse])
        db.session.commit()

        movement1 = StockMovement(
            type="ENTREE",
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=10,
            user_id=gestionnaire.id
        )

        movement2 = StockMovement(
            type="SORTIE",
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=2,
            user_id=gestionnaire.id
        )

        db.session.add_all([movement1, movement2])
        db.session.commit()

    response = client.get("/api/dashboard/movements")

    assert response.status_code == 200

    movements = response.json["movements"]

    assert len(movements) == 2
    assert movements[0]["type"] == "ENTREE"
    assert movements[0]["total"] == 1
    assert movements[1]["type"] == "SORTIE"
    assert movements[1]["total"] == 1

def test_dashboard_top_exits(app, client, gestionnaire):
    with app.app_context():
        product1 = Product(
            sku="TOP001",
            name="Ordinateur",
            unit_price=100,
            minimum_stock=5
        )

        product2 = Product(
            sku="TOP002",
            name="Clavier",
            unit_price=20,
            minimum_stock=5
        )

        warehouse = Warehouse(
            name="Entrepot Top",
            location="Dakar"
        )

        db.session.add_all([product1, product2, warehouse])
        db.session.commit()

        movements = [
            StockMovement(
                type="SORTIE",
                product_id=product1.id,
                warehouse_id=warehouse.id,
                quantity=5,
                user_id=gestionnaire.id
            ),
            StockMovement(
                type="SORTIE",
                product_id=product2.id,
                warehouse_id=warehouse.id,
                quantity=10,
                user_id=gestionnaire.id
            ),
            StockMovement(
                type="ENTREE",
                product_id=product1.id,
                warehouse_id=warehouse.id,
                quantity=100,
                user_id=gestionnaire.id
            )
        ]

        db.session.add_all(movements)
        db.session.commit()

    response = client.get("/api/dashboard/top-exits")

    assert response.status_code == 200

    top_exits = response.json["top_exits"]

    assert len(top_exits) == 2
    assert top_exits[0]["product_name"] == "Clavier"
    assert top_exits[0]["total_exits"] == 10
    assert top_exits[1]["product_name"] == "Ordinateur"
    assert top_exits[1]["total_exits"] == 5