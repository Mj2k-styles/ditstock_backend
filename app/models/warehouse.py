from app import db


class Warehouse(db.Model):
    __tablename__ = "warehouses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    location = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<Warehouse {self.name}>"