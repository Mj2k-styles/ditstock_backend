
from flask_restx import Namespace, Resource
from app import db
from app.models.warehouse_stock import WarehouseStock
from app.models.product import Product
from app.models.warehouse import Warehouse

alerts_ns = Namespace("alerts", description="Alertes de stock")


@alerts_ns.route("/")
class StockAlerts(Resource):

    def get(self):
        stocks = WarehouseStock.query.join(
            Product, WarehouseStock.product_id == Product.id
        ).join(
            Warehouse, WarehouseStock.warehouse_id == Warehouse.id
        ).filter(
            Product.is_archived == False,
            Warehouse.is_archived == False,
            WarehouseStock.quantity < Product.minimum_stock
        ).all()

        return [{
            "product_id": stock.product_id,
            "product_name": db.session.get(Product, stock.product_id).name,
            "warehouse_id": stock.warehouse_id,
            "warehouse_name": db.session.get(Warehouse, stock.warehouse_id).name,
            "quantity": stock.quantity,
            "minimum_stock": db.session.get(Product, stock.product_id).minimum_stock
        } for stock in stocks], 200
