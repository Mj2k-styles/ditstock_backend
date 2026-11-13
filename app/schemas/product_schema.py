from marshmallow import Schema, fields, validate

STOCK_STATES = ("ok", "alerte", "rupture")


class ProductSchema(Schema):

    sku = fields.String(
        required=True,
        validate=validate.Length(min=1, max=50)
    )

    name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=150)
    )

    description = fields.String(
        allow_none=True
    )

    category_id = fields.Integer(
        allow_none=True
    )

    supplier_id = fields.Integer(
        allow_none=True
    )

    unit = fields.String(
        load_default="pièce",
        validate=validate.Length(min=1, max=20)
    )

    # Prix d'achat unitaire (sert à la valeur du stock)
    unit_price = fields.Decimal(
        required=True,
        as_string=True,
        validate=validate.Range(min=0)
    )

    # Prix de vente unitaire (facultatif)
    sale_price = fields.Decimal(
        allow_none=True,
        as_string=True,
        validate=validate.Range(min=0)
    )

    minimum_stock = fields.Integer(
        load_default=0,
        validate=validate.Range(min=0)
    )

    image_url = fields.Url(
        allow_none=True,
        schemes={"http", "https"},
        validate=validate.Length(max=500)
    )


class ProductFilterSchema(Schema):
    """Filtres acceptés par GET /api/products (tous facultatifs)."""

    q = fields.String(validate=validate.Length(max=100))
    category_id = fields.Integer()
    supplier_id = fields.Integer()
    warehouse_id = fields.Integer()
    stock_state = fields.String(validate=validate.OneOf(STOCK_STATES))
    page = fields.Integer(validate=validate.Range(min=1))
    per_page = fields.Integer(validate=validate.Range(min=1, max=200))
