from marshmallow import Schema, fields, validate


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

    unit_price = fields.Decimal(
        required=True,
        as_string=True,
        validate=validate.Range(min=0)
    )

    minimum_stock = fields.Integer(
        load_default=0,
        validate=validate.Range(min=0)
    )