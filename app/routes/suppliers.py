from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app import db
from app.models.supplier import Supplier
from app.schemas.supplier_schema import SupplierSchema
from app.constants import ROLE_GESTIONNAIRE
from app.utils.decorators import login_required, roles_required

suppliers_ns = Namespace(
    "suppliers",
    description="Gestion des fournisseurs"
)

supplier_model = suppliers_ns.model("Supplier", {
    "name": fields.String(required=True),
    "email": fields.String,
    "phone": fields.String,
    "address": fields.String
})


# Liste et création des fournisseurs
@suppliers_ns.route("/")
@suppliers_ns.doc(security="Bearer")
class SupplierList(Resource):

    @login_required
    def get(self):
        suppliers = Supplier.query.filter_by(is_archived=False).all()

        return [
            {
                "id": s.id,
                "name": s.name,
                "email": s.email,
                "phone": s.phone,
                "address": s.address
            }
            for s in suppliers
        ], 200

    @roles_required(ROLE_GESTIONNAIRE)
    @suppliers_ns.expect(supplier_model)
    def post(self):
        data_json = request.get_json(silent=True)

        if data_json is None:
            return {"message": "Les données JSON sont obligatoires"}, 400

        try:
            data = SupplierSchema().load(data_json)
        except ValidationError as err:
            return {"errors": err.messages}, 400

        supplier = Supplier(**data)
        db.session.add(supplier)
        db.session.commit()

        return {
            "message": "Fournisseur ajouté avec succès",
            "id": supplier.id,
            "name": supplier.name
        }, 201


# Consultation, modification et archivage
@suppliers_ns.route("/<int:supplier_id>")
@suppliers_ns.doc(security="Bearer")
class SupplierDetail(Resource):

    @login_required
    def get(self, supplier_id):
        supplier = Supplier.query.filter_by(
            id=supplier_id,
            is_archived=False
        ).first()

        if supplier is None:
            return {"message": "Fournisseur introuvable"}, 404

        return {
            "id": supplier.id,
            "name": supplier.name,
            "email": supplier.email,
            "phone": supplier.phone,
            "address": supplier.address
        }, 200

    @roles_required(ROLE_GESTIONNAIRE)
    @suppliers_ns.expect(supplier_model)
    def put(self, supplier_id):
        supplier = Supplier.query.filter_by(
            id=supplier_id,
            is_archived=False
        ).first()

        if supplier is None:
            return {"message": "Fournisseur introuvable"}, 404

        data_json = request.get_json(silent=True)

        if data_json is None:
            return {"message": "Les données JSON sont obligatoires"}, 400

        try:
            data = SupplierSchema().load(data_json)
        except ValidationError as err:
            return {"errors": err.messages}, 400

        for key, value in data.items():
            setattr(supplier, key, value)

        db.session.commit()

        return {
            "message": "Fournisseur modifié avec succès",
            "id": supplier.id,
            "name": supplier.name
        }, 200

    @roles_required(ROLE_GESTIONNAIRE)
    def delete(self, supplier_id):
        supplier = Supplier.query.filter_by(
            id=supplier_id,
            is_archived=False
        ).first()

        if supplier is None:
            return {"message": "Fournisseur introuvable"}, 404

        supplier.is_archived = True
        db.session.commit()

        return {
            "message": "Fournisseur archivé avec succès"
        }, 200