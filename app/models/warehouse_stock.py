from app import db


class WarehouseStock(db.Model):
    __tablename__ = "warehouse_stocks"

    id = db.Column(db.Integer, primary_key=True)

    warehouse_id = db.Column(
        db.Integer,
        db.ForeignKey("warehouses.id"),
        nullable=False
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False
    )

    quantity = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint(
            "warehouse_id",
            "product_id",
            name="uq_warehouse_product"
        ),
        db.CheckConstraint("quantity >= 0", name="ck_quantity_positive"),
    )