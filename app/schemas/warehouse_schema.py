from marshmallow import Schema, fields, validate


class WarehouseSchema(Schema):
    id = fields.Int(dump_only=True)

    name = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=150)
    )

    location = fields.Str(
        allow_none=True,
        validate=validate.Length(max=255)
    )

    description = fields.Str(allow_none=True)

    is_archived = fields.Bool(dump_only=True)