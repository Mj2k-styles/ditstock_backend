
from flask_restx import Namespace, Resource
from sqlalchemy import func

from app import db
from app.models import Product, WarehouseStock
from app.utils.decorators import login_required

dashboard_ns = Namespace(
    "dashboard",
    description="Statistiques du tableau de bord"
)


@dashboard_ns.route("/stats")
@dashboard_ns.doc(security="Bearer")
class DashboardStats(Resource):

    @login_required
    def get(self):
        # 1. Nombre de produits actifs
        total_products = Product.query.filter_by(
            is_archived=False
        ).count()

        # 2. Valeur totale du stock
        stock_value = db.session.query(
            func.coalesce(
                func.sum(WarehouseStock.quantity * Product.unit_price),
                0
            )
        ).join(
            Product,
            Product.id == WarehouseStock.product_id
        ).filter(
            Product.is_archived == False
        ).scalar()

        # 3. Nombre d'alertes de stock
        total_alerts = db.session.query(
            WarehouseStock.id
        ).join(
            Product,
            Product.id == WarehouseStock.product_id
        ).filter(
            Product.is_archived == False,
            WarehouseStock.quantity < Product.minimum_stock
        ).count()

        return {
            "total_products": total_products,
            "stock_value": float(stock_value),
            "total_alerts": total_alerts
        }, 200
