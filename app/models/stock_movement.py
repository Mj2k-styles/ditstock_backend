from datetime import datetime, timezone

from app import db
from app.constants import MOVEMENT_TYPES


class StockMovement(db.Model):
    """
    Historique de tous les mouvements de stock.

    Le stock (table warehouse_stocks) n'est jamais modifié directement :
    il est toujours le résultat d'un mouvement.
    """

    __tablename__ = "stock_movements"

    id = db.Column(db.Integer, primary_key=True)

    # ENTREE, SORTIE, TRANSFERT ou AJUSTEMENT
    type = db.Column(db.String(20), nullable=False, index=True)

    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id"), nullable=False, index=True
    )

    # Entrepôt concerné (entrepôt source pour un transfert)
    warehouse_id = db.Column(
        db.Integer, db.ForeignKey("warehouses.id"), nullable=False, index=True
    )

    # Entrepôt de destination (transfert uniquement)
    warehouse_dest_id = db.Column(
        db.Integer, db.ForeignKey("warehouses.id"), nullable=True
    )

    # Quantité : toujours > 0, sauf pour un AJUSTEMENT où c'est l'écart
    # (positif ou négatif, mais jamais 0)
    quantity = db.Column(db.Integer, nullable=False)

    # Motif (obligatoire pour un ajustement)
    reason = db.Column(db.String(255), nullable=True)

    # Référence du bon de réception, de livraison, etc.
    reference = db.Column(db.String(100), nullable=True)

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    product = db.relationship("Product")
    warehouse = db.relationship("Warehouse", foreign_keys=[warehouse_id])
    warehouse_dest = db.relationship(
        "Warehouse", foreign_keys=[warehouse_dest_id]
    )
    user = db.relationship("User")

    __table_args__ = (
        db.CheckConstraint(
            "type IN (%s)" % ", ".join(f"'{t}'" for t in MOVEMENT_TYPES),
            name="ck_movement_type"
        ),
        db.CheckConstraint("quantity <> 0", name="ck_movement_quantity"),
    )

    def __repr__(self):
        return f"<StockMovement {self.type} {self.quantity} produit={self.product_id}>"
