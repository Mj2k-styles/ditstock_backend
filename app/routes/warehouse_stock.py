from flask import request
from flask_restx import Namespace, Resource
from app import db
from app.models.warehouse_stock import WarehouseStock
from app.models.warehouse import Warehouse
from app.models.product import Product

warehouse_stocks_ns = Namespace(
    "warehouse_stocks",
    description="Gestion du stock par entrepôt"
)


@warehouse_stocks_ns.route("/")
class WarehouseStockList(Resource):

    def get(self):
        stocks = WarehouseStock.query.all()

        return [{
            "id": s.id,
            "warehouse_id": s.warehouse_id,
            "product_id": s.product_id,
            "quantity": s.quantity
        } for s in stocks], 200

    def post(self):
        data = request.get_json() or {}

        warehouse = db.session.get(Warehouse, data.get("warehouse_id"))
        product = db.session.get(Product, data.get("product_id"))

        if not warehouse or warehouse.is_archived:
            return {"message": "Entrepôt introuvable."}, 404

        if not product or product.is_archived:
            return {"message": "Produit introuvable."}, 404

        quantity = data.get("quantity", 0)

        if not isinstance(quantity, int) or quantity < 0:
            return {"message": "Quantité invalide."}, 400

        stock = WarehouseStock.query.filter_by(
            warehouse_id=warehouse.id,
            product_id=product.id
        ).first()

        if stock:
            stock.quantity = quantity
        else:
            stock = WarehouseStock(
                warehouse_id=warehouse.id,
                product_id=product.id,
                quantity=quantity
            )
            db.session.add(stock)

        db.session.commit()

        return {
            "message": "Stock enregistré.",
            "warehouse_id": stock.warehouse_id,
            "product_id": stock.product_id,
            "quantity": stock.quantity
        }, 201