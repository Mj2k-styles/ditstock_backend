from marshmallow import Schema, fields, post_load, validate


class LoginSchema(Schema):

    email = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255)
    )

    password = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255)
    )

    @post_load
    def normalize_email(self, data, **kwargs):
        data["email"] = data["email"].strip().lower()
        return data
