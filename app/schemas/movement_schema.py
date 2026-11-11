from marshmallow import (
    Schema,
    ValidationError,
    fields,
    validate,
    validates_schema,
)

from app.constants import (
    MOVEMENT_AJUSTEMENT,
    MOVEMENT_ENTREE,
    MOVEMENT_SORTIE,
    MOVEMENT_TRANSFERT,
    MOVEMENT_TYPES,
)

MAX_QUANTITY = 1_000_000


class MovementCreateSchema(Schema):
    """Données attendues pour POST /api/movements."""

    type = fields.String(required=True, validate=validate.OneOf(MOVEMENT_TYPES))
    product_id = fields.Integer(required=True, strict=True)
    warehouse_id = fields.Integer(required=True, strict=True)
    warehouse_dest_id = fields.Integer(allow_none=True, strict=True)

    # Quantité entière. Le signe est contrôlé dans validates_schema
    # (> 0 pour entrée / sortie / transfert, écart non nul pour un ajustement).
    quantity = fields.Integer(
        required=True,
        strict=True,
        validate=validate.Range(min=-MAX_QUANTITY, max=MAX_QUANTITY)
    )

    reason = fields.String(
        allow_none=True, validate=validate.Length(max=255)
    )
    reference = fields.String(
        allow_none=True, validate=validate.Length(max=100)
    )

    @validates_schema
    def validate_business_rules(self, data, **kwargs):
        movement_type = data.get("type")
        quantity = data.get("quantity")

        if movement_type == MOVEMENT_AJUSTEMENT:
            if quantity == 0:
                raise ValidationError(
                    "L'écart d'un ajustement ne peut pas être 0.", "quantity"
                )
            # Motif obligatoire pour un ajustement
            if not (data.get("reason") or "").strip():
                raise ValidationError(
                    "Le motif est obligatoire pour un ajustement.", "reason"
                )

        elif movement_type in (
            MOVEMENT_ENTREE, MOVEMENT_SORTIE, MOVEMENT_TRANSFERT
        ):
            if quantity is not None and quantity <= 0:
                raise ValidationError(
                    "La quantité doit être strictement positive.", "quantity"
                )

        if movement_type == MOVEMENT_TRANSFERT:
            if data.get("warehouse_dest_id") is None:
                raise ValidationError(
                    "L'entrepôt de destination est obligatoire "
                    "pour un transfert.", "warehouse_dest_id"
                )
        elif data.get("warehouse_dest_id") is not None:
            raise ValidationError(
                "L'entrepôt de destination n'est utilisé que pour "
                "un transfert.", "warehouse_dest_id"
            )


class MovementFilterSchema(Schema):
    """Filtres acceptés par GET /api/movements (tous facultatifs)."""

    type = fields.String(validate=validate.OneOf(MOVEMENT_TYPES))
    product_id = fields.Integer()
    warehouse_id = fields.Integer()
    user_id = fields.Integer()
    date_from = fields.Date()
    date_to = fields.Date()
    page = fields.Integer(validate=validate.Range(min=1))
    per_page = fields.Integer(validate=validate.Range(min=1, max=200))


class MovementSchema(Schema):
    """Représentation d'un mouvement dans les réponses."""

    id = fields.Integer()
    type = fields.String()
    product_id = fields.Integer()
    product_name = fields.Function(lambda m: m.product.name)
    product_sku = fields.Function(lambda m: m.product.sku)
    warehouse_id = fields.Integer()
    warehouse_name = fields.Function(lambda m: m.warehouse.name)
    warehouse_dest_id = fields.Integer(allow_none=True)
    warehouse_dest_name = fields.Function(
        lambda m: m.warehouse_dest.name if m.warehouse_dest else None
    )
    quantity = fields.Integer()
    reason = fields.String(allow_none=True)
    reference = fields.String(allow_none=True)
    user_id = fields.Integer()
    user_name = fields.Function(lambda m: m.user.full_name)
    created_at = fields.DateTime()


movement_schema = MovementSchema()
movements_schema = MovementSchema(many=True)
