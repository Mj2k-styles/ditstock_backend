
from flask import request
from flask_restx import Namespace, Resource
from app import db
from app.models.warehouse_stock import WarehouseStock
from app.models.warehouse import Warehouse
from app.models.product import Product
from app.constants import ROLE_GESTIONNAIRE, ROLE_MAGASINIER
from app.utils.decorators import login_required, roles_required

warehouse_stocks_ns = Namespace(
    "warehouse_stocks",
    description="Gestion du stock par entrepôt"
)


@warehouse_stocks_ns.route("/")
@warehouse_stocks_ns.doc(security="Bearer")
class WarehouseStockList(Resource):

    @login_required
    def get(self):
        stocks = WarehouseStock.query.all()

        return [{
            "id": s.id,
            "warehouse_id": s.warehouse_id,
            "product_id": s.product_id,
            "quantity": s.quantity
        } for s in stocks], 200

    @roles_required(ROLE_GESTIONNAIRE, ROLE_MAGASINIER)
    def post(self):
        data = request.get_json() or {}

        warehouse_id = data.get("warehouse_id")
        product_id = data.get("product_id")

        warehouse = (
            db.session.get(Warehouse, warehouse_id)
            if warehouse_id is not None else None
        )

        product = (
            db.session.get(Product, product_id)
            if product_id is not None else None
        )

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
