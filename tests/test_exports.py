from app import db
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.warehouse_stock import WarehouseStock
from app.models.stock_movement import StockMovement
import pytest

pytestmark = pytest.mark.usefixtures("as_gestionnaire")


def create_stock_data(app):
    with app.app_context():
        product = Product(
            sku="EXPORT001",
            name="Ordinateur HP",
            unit_price=350000,
            minimum_stock=5
        )

        warehouse = Warehouse(
            name="Entrepot Export",
            location="Dakar"
        )

        db.session.add_all([product, warehouse])
        db.session.commit()

        stock = WarehouseStock(
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=10
        )

        db.session.add(stock)
        db.session.commit()


def create_movement_data(app, gestionnaire):
    with app.app_context():
        product = Product(
            sku="MOVE001",
            name="Clavier HP",
            unit_price=15000,
            minimum_stock=3
        )

        warehouse = Warehouse(
            name="Entrepot Mouvement",
            location="Dakar"
        )

        db.session.add_all([product, warehouse])
        db.session.commit()

        movement = StockMovement(
            type="ENTREE",
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=20,
            reason="Approvisionnement",
            reference="CMD-001",
            user_id=gestionnaire.id
        )

        db.session.add(movement)
        db.session.commit()


def test_export_stock_csv(app, client):
    create_stock_data(app)

    response = client.get("/api/exports/stock/csv")

    assert response.status_code == 200
    assert "text/csv" in response.content_type
    assert "etat_du_stock.csv" in response.headers["Content-Disposition"]

    contenu = response.data.decode("utf-8-sig")

    assert "SKU" in contenu
    assert "Ordinateur HP" in contenu
    assert "EXPORT001" in contenu
    assert "10" in contenu


def test_export_stock_pdf(app, client):
    create_stock_data(app)

    response = client.get("/api/exports/stock/pdf")

    assert response.status_code == 200
    assert response.content_type == "application/pdf"
    assert "etat_du_stock.pdf" in response.headers["Content-Disposition"]
    assert response.data.startswith(b"%PDF")


def test_export_movements_csv(app, client, gestionnaire):
    create_movement_data(app, gestionnaire)

    response = client.get("/api/exports/movements/csv")

    assert response.status_code == 200
    assert "text/csv" in response.content_type
    assert "historique_mouvements.csv" in response.headers["Content-Disposition"]

    contenu = response.data.decode("utf-8-sig")

    assert "ENTREE" in contenu
    assert "MOVE001" in contenu
    assert "Clavier HP" in contenu
    assert "Entrepot Mouvement" in contenu
    assert "20" in contenu
    assert "Approvisionnement" in contenu
    assert "CMD-001" in contenu


def test_export_movements_pdf(app, client, gestionnaire):
    create_movement_data(app, gestionnaire)

    response = client.get("/api/exports/movements/pdf")

    assert response.status_code == 200
    assert response.content_type == "application/pdf"
    assert "historique_mouvements.pdf" in response.headers["Content-Disposition"]
    assert response.data.startswith(b"%PDF")
