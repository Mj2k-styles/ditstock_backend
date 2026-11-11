from datetime import datetime, time, timedelta

from flask import g, request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app import db
from app.constants import MOVEMENT_TYPES
from app.models.stock_movement import StockMovement
from app.schemas.movement_schema import (
    MovementCreateSchema,
    MovementFilterSchema,
    movement_schema,
    movements_schema,
)
from app.services.movement_service import MovementError, create_movement
from app.utils.decorators import login_required

movements_ns = Namespace(
    "movements",
    description="Mouvements de stock (entrée, sortie, transfert, ajustement)"
)

# Modèle utilisé pour documenter les données dans Swagger
movement_model = movements_ns.model("MovementCreate", {
    "type": fields.String(required=True, enum=list(MOVEMENT_TYPES)),
    "product_id": fields.Integer(required=True),
    "warehouse_id": fields.Integer(
        required=True, description="Entrepôt (source pour un transfert)"
    ),
    "warehouse_dest_id": fields.Integer(
        description="Entrepôt de destination (transfert uniquement)"
    ),
    "quantity": fields.Integer(
        required=True,
        description="> 0, sauf ajustement : écart positif ou négatif"
    ),
    "reason": fields.String(
        description="Motif (obligatoire pour un ajustement)"
    ),
    "reference": fields.String(description="Référence du bon"),
})


@movements_ns.route("/")
@movements_ns.doc(security="Bearer")
class MovementList(Resource):

    @login_required
    @movements_ns.doc(params={
        "type": "ENTREE, SORTIE, TRANSFERT ou AJUSTEMENT",
        "product_id": "Identifiant du produit",
        "warehouse_id": "Entrepôt source ou destination",
        "user_id": "Utilisateur ayant fait le mouvement",
        "date_from": "Date de début incluse (AAAA-MM-JJ)",
        "date_to": "Date de fin incluse (AAAA-MM-JJ)",
        "page": "Active la pagination (avec per_page, 50 par défaut)",
        "per_page": "Taille de page (200 maximum)",
    })
    def get(self):
        """Historique des mouvements, du plus récent au plus ancien."""
        try:
            filters = MovementFilterSchema().load(request.args.to_dict())
        except ValidationError as err:
            return {"errors": err.messages}, 400

        query = StockMovement.query

        if "type" in filters:
            query = query.filter(StockMovement.type == filters["type"])
        if "product_id" in filters:
            query = query.filter(
                StockMovement.product_id == filters["product_id"]
            )
        if "user_id" in filters:
            query = query.filter(StockMovement.user_id == filters["user_id"])
        if "warehouse_id" in filters:
            # Un transfert concerne aussi l'entrepôt de destination
            wid = filters["warehouse_id"]
            query = query.filter(
                (StockMovement.warehouse_id == wid)
                | (StockMovement.warehouse_dest_id == wid)
            )
        if "date_from" in filters:
            query = query.filter(
                StockMovement.created_at >= datetime.combine(
                    filters["date_from"], time.min
                )
            )
        if "date_to" in filters:
            # date_to est incluse : on prend tout ce qui précède le lendemain
            query = query.filter(
                StockMovement.created_at < datetime.combine(
                    filters["date_to"] + timedelta(days=1), time.min
                )
            )

        query = query.order_by(
            StockMovement.created_at.desc(), StockMovement.id.desc()
        )

        # Sans "page" : simple tableau (comme les autres routes).
        # Avec "page" ou "per_page" : réponse paginée.
        if "page" not in filters and "per_page" not in filters:
            return movements_schema.dump(query.all()), 200

        page = filters.get("page", 1)
        per_page = filters.get("per_page", 50)
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            "items": movements_schema.dump(pagination.items),
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
            "per_page": per_page,
        }, 200

    @login_required
    @movements_ns.expect(movement_model)
    def post(self):
        """Enregistre un mouvement et met à jour le stock (transaction)."""
        try:
            data = MovementCreateSchema().load(
                request.get_json(silent=True) or {}
            )
        except ValidationError as err:
            return {"errors": err.messages}, 400

        try:
            movement, stocks = create_movement(data, g.current_user)
        except MovementError as err:
            return {"message": err.message}, err.status

        return {
            "message": "Mouvement enregistré avec succès.",
            "movement": movement_schema.dump(movement),
            "stock": [
                {
                    "warehouse_id": s.warehouse_id,
                    "product_id": s.product_id,
                    "quantity": s.quantity,
                }
                for s in stocks
            ],
        }, 201


@movements_ns.route("/<int:movement_id>")
@movements_ns.doc(security="Bearer")
class MovementDetail(Resource):

    @login_required
    def get(self, movement_id):
        """Détail d'un mouvement."""
        movement = db.session.get(StockMovement, movement_id)

        if movement is None:
            return {"message": "Mouvement introuvable."}, 404

        return movement_schema.dump(movement), 200
