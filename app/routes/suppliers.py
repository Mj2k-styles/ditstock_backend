from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app import db
from app.constants import MOVEMENT_ENTREE, ROLE_GESTIONNAIRE
from app.models.stock_movement import StockMovement
from app.models.supplier import Supplier
from app.schemas.movement_schema import movements_schema
from app.schemas.supplier_schema import SupplierSchema
from app.services import audit
from app.utils.decorators import login_required, roles_required
from app.utils.pagination import paginate_or_list, read_page_args

suppliers_ns = Namespace(
    "suppliers",
    description="Gestion des fournisseurs"
)

supplier_model = suppliers_ns.model("Supplier", {
    "name": fields.String(required=True),
    "contact": fields.String,
    "email": fields.String,
    "phone": fields.String,
    "address": fields.String
})


def serialize(supplier):
    return {
        "id": supplier.id,
        "name": supplier.name,
        "contact": supplier.contact,
        "email": supplier.email,
        "phone": supplier.phone,
        "address": supplier.address
    }


def _active_supplier(supplier_id):
    return Supplier.query.filter_by(id=supplier_id, is_archived=False).first()


def _load_payload():
    """(données validées, None) ou (None, réponse d'erreur)."""
    data_json = request.get_json(silent=True)
    if data_json is None:
        return None, ({"message": "Les données JSON sont obligatoires"}, 400)
    try:
        return SupplierSchema().load(data_json), None
    except ValidationError as err:
        return None, ({"errors": err.messages}, 400)


# Liste et création des fournisseurs
@suppliers_ns.route("/")
@suppliers_ns.doc(security="Bearer")
class SupplierList(Resource):

    @login_required
    def get(self):
        suppliers = Supplier.query.filter_by(is_archived=False).all()
        return [serialize(s) for s in suppliers], 200

    @roles_required(ROLE_GESTIONNAIRE)
    @suppliers_ns.expect(supplier_model)
    def post(self):
        data, error = _load_payload()
        if error:
            return error

        supplier = Supplier(**data)
        db.session.add(supplier)
        db.session.flush()
        audit.record(audit.CREATION, "fournisseur", supplier.id, {"nom": supplier.name})
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
        supplier = _active_supplier(supplier_id)
        if supplier is None:
            return {"message": "Fournisseur introuvable"}, 404

        return serialize(supplier), 200

    @roles_required(ROLE_GESTIONNAIRE)
    @suppliers_ns.expect(supplier_model)
    def put(self, supplier_id):
        supplier = _active_supplier(supplier_id)
        if supplier is None:
            return {"message": "Fournisseur introuvable"}, 404

        data, error = _load_payload()
        if error:
            return error

        details = audit.changes(supplier, data)
        for key, value in data.items():
            setattr(supplier, key, value)
        if details:
            audit.record(audit.MODIFICATION, "fournisseur", supplier.id, details)

        db.session.commit()

        return {
            "message": "Fournisseur modifié avec succès",
            "id": supplier.id,
            "name": supplier.name
        }, 200

    @roles_required(ROLE_GESTIONNAIRE)
    def delete(self, supplier_id):
        supplier = _active_supplier(supplier_id)
        if supplier is None:
            return {"message": "Fournisseur introuvable"}, 404

        supplier.is_archived = True
        audit.record(audit.ARCHIVAGE, "fournisseur", supplier.id, {"nom": supplier.name})
        db.session.commit()

        return {
            "message": "Fournisseur archivé avec succès"
        }, 200


# Historique des approvisionnements (cahier des charges, F4.2)
@suppliers_ns.route("/<int:supplier_id>/movements")
@suppliers_ns.doc(
    security="Bearer",
    params={
        "page": "Active la pagination (avec per_page, 50 par défaut)",
        "per_page": "Taille de page (200 maximum)",
    },
)
class SupplierHistory(Resource):

    @login_required
    def get(self, supplier_id):
        supplier = db.session.get(Supplier, supplier_id)
        if supplier is None:
            return {"message": "Fournisseur introuvable"}, 404

        page_args, error = read_page_args()
        if error:
            return error

        query = StockMovement.query.filter_by(
            supplier_id=supplier.id, type=MOVEMENT_ENTREE
        ).order_by(StockMovement.created_at.desc(), StockMovement.id.desc())

        return paginate_or_list(query, page_args, movements_schema.dump), 200
