from marshmallow import Schema, fields, validate


class CategorySchema(Schema):
    name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=100)
    )

    description = fields.String(allow_none=True)
