from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app import db
from app.models.warehouse import Warehouse
from app.schemas.warehouse_schema import WarehouseSchema
from app.constants import ROLE_GESTIONNAIRE
from app.utils.decorators import login_required, roles_required

warehouses_ns = Namespace("warehouses", description="Gestion des entrepôts")

warehouse_schema = WarehouseSchema()
warehouses_schema = WarehouseSchema(many=True)

warehouse_model = warehouses_ns.model("Warehouse", {
    "name": fields.String(required=True),
    "location": fields.String,
    "description": fields.String,
})


@warehouses_ns.route("/")
@warehouses_ns.doc(security="Bearer")
class WarehouseList(Resource):

    @login_required
    def get(self):
        warehouses = Warehouse.query.filter_by(is_archived=False).all()
        return warehouses_schema.dump(warehouses), 200

    @roles_required(ROLE_GESTIONNAIRE)
    def post(self):
        try:
            data = warehouse_schema.load(request.get_json() or {})
        except ValidationError as err:
            return {"errors": err.messages}, 400

        if Warehouse.query.filter_by(name=data["name"]).first():
            return {"message": "Cet entrepôt existe déjà."}, 409

        warehouse = Warehouse(**data)
        db.session.add(warehouse)
        db.session.commit()

        return warehouse_schema.dump(warehouse), 201


@warehouses_ns.route("/<int:warehouse_id>")
@warehouses_ns.doc(security="Bearer")
class WarehouseDetail(Resource):

    @login_required
    def get(self, warehouse_id):
        warehouse = Warehouse.query.filter_by(
            id=warehouse_id,
            is_archived=False
        ).first()

        if not warehouse:
            return {"message": "Entrepôt introuvable."}, 404

        return warehouse_schema.dump(warehouse), 200

    @roles_required(ROLE_GESTIONNAIRE)
    def put(self, warehouse_id):
        warehouse = Warehouse.query.filter_by(
            id=warehouse_id,
            is_archived=False
        ).first()

        if not warehouse:
            return {"message": "Entrepôt introuvable."}, 404

        try:
            data = warehouse_schema.load(
                request.get_json() or {},
                partial=True
            )
        except ValidationError as err:
            return {"errors": err.messages}, 400

        if "name" in data:
            existing = Warehouse.query.filter(
                Warehouse.name == data["name"],
                Warehouse.id != warehouse_id
            ).first()

            if existing:
                return {"message": "Ce nom d'entrepôt existe déjà."}, 409

        for key, value in data.items():
            setattr(warehouse, key, value)

        db.session.commit()
        return warehouse_schema.dump(warehouse), 200

    @roles_required(ROLE_GESTIONNAIRE)
    def delete(self, warehouse_id):
        warehouse = Warehouse.query.filter_by(
            id=warehouse_id,
            is_archived=False
        ).first()

        if not warehouse:
            return {"message": "Entrepôt introuvable."}, 404

        warehouse.is_archived = True
        db.session.commit()

        return {"message": "Entrepôt archivé avec succès."}, 200