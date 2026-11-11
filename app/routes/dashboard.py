
from flask_restx import Namespace, Resource
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from app.models.stock_movement import StockMovement

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
        # 3. Nombre de mouvements effectués aujourd'hui
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        movements_today = StockMovement.query.filter(
            StockMovement.created_at >= start_of_day,
            StockMovement.created_at <= now
        ).count()

        # 4. Nombre d'alertes de stock        
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
            "total_alerts": total_alerts,
            "movements_today": movements_today
        }, 200

@dashboard_ns.route("/movements")
@dashboard_ns.doc(security="Bearer")
class DashboardMovements(Resource):

    @login_required
    def get(self):
        # Date actuelle en UTC
        now = datetime.now(timezone.utc)

        # Début de la période : 30 jours
        start_date = now.date() - timedelta(days=29)

        start_datetime = datetime(
            start_date.year,
            start_date.month,
            start_date.day,
            tzinfo=timezone.utc
        )

        # Regrouper les mouvements par jour et par type
        results = db.session.query(
            func.date(StockMovement.created_at).label("date"),
            StockMovement.type,
            func.count(StockMovement.id).label("total")
        ).filter(
            StockMovement.created_at >= start_datetime,
            StockMovement.created_at <= now
        ).group_by(
            func.date(StockMovement.created_at),
            StockMovement.type
        ).order_by(
            func.date(StockMovement.created_at)
        ).all()

        return {
            "movements": [
                {
                    "date": str(row.date),
                    "type": row.type,
                    "total": row.total
                }
                for row in results
            ]
        }, 200

@dashboard_ns.route("/top-exits")
@dashboard_ns.doc(security="Bearer")
class DashboardTopExits(Resource):

    @login_required
    def get(self):
        # Période des 30 derniers jours
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=30)

        # Calculer les quantités réellement sorties par produit
        results = db.session.query(
            Product.id,
            Product.name,
            Product.sku,
            func.sum(StockMovement.quantity).label("total_exits")
        ).join(
            StockMovement,
            StockMovement.product_id == Product.id
        ).filter(
            StockMovement.type == "SORTIE",
            StockMovement.created_at >= start_date,
            StockMovement.created_at <= now,
            Product.is_archived == False
        ).group_by(
            Product.id,
            Product.name,
            Product.sku
        ).order_by(
            func.sum(StockMovement.quantity).desc()
        ).limit(10).all()

        return {
            "top_exits": [
                {
                    "product_id": row.id,
                    "product_name": row.name,
                    "sku": row.sku,
                    "total_exits": int(row.total_exits)
                }
                for row in results
            ]
        }, 200    