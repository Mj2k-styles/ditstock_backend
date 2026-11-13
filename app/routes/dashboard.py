from datetime import datetime, time, timedelta, timezone

from flask_restx import Namespace, Resource
from sqlalchemy import func

from app import db
from app.constants import MOVEMENT_SORTIE
from app.models import Product, StockMovement, WarehouseStock
from app.utils.decorators import login_required

# Période des graphiques du tableau de bord (jours, aujourd'hui inclus)
MOVEMENTS_PERIOD_DAYS = 30

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
            Product.is_archived.is_(False)
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
            Product.is_archived.is_(False),
            WarehouseStock.quantity < Product.minimum_stock
        ).count()

        # 4. Mouvements du jour et des 30 derniers jours (graphiques)
        today = datetime.now(timezone.utc).date()
        first_day = today - timedelta(days=MOVEMENTS_PERIOD_DAYS - 1)
        period_start = datetime.combine(first_day, time.min)

        movements_today = StockMovement.query.filter(
            StockMovement.created_at >= datetime.combine(today, time.min)
        ).count()

        # Nombre de mouvements par jour ; les jours sans mouvement valent 0
        # pour que la courbe soit continue
        counts_by_day = {
            str(day)[:10]: count
            for day, count in db.session.query(
                func.date(StockMovement.created_at), func.count()
            ).filter(
                StockMovement.created_at >= period_start
            ).group_by(
                func.date(StockMovement.created_at)
            ).all()
        }
        movements_30d = [
            {
                "date": (first_day + timedelta(days=i)).isoformat(),
                "count": counts_by_day.get(
                    (first_day + timedelta(days=i)).isoformat(), 0
                )
            }
            for i in range(MOVEMENTS_PERIOD_DAYS)
        ]

        # 5. Top 10 des produits sortis sur la même période
        total_out = func.sum(StockMovement.quantity)
        top_products = [
            {"product_id": product_id, "name": name, "quantity": int(quantity)}
            for product_id, name, quantity in db.session.query(
                Product.id, Product.name, total_out
            ).join(
                StockMovement, StockMovement.product_id == Product.id
            ).filter(
                StockMovement.type == MOVEMENT_SORTIE,
                StockMovement.created_at >= period_start
            ).group_by(
                Product.id, Product.name
            ).order_by(
                total_out.desc(), Product.name
            ).limit(10).all()
        ]

        return {
            "total_products": total_products,
            "stock_value": float(stock_value),
            "total_alerts": total_alerts,
            "movements_today": movements_today,
            "movements_30d": movements_30d,
            "top_products": top_products
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
            Product.is_archived.is_(False)
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
