from marshmallow import Schema, fields, validate


class SupplierSchema(Schema):
    name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=150)
    )

    contact = fields.String(
        allow_none=True,
        validate=validate.Length(max=150)
    )

    email = fields.Email(allow_none=True)

    phone = fields.String(
        allow_none=True,
        validate=validate.Length(max=30)
    )

    address = fields.String(allow_none=True)
