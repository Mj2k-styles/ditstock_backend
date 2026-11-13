from marshmallow import Schema, fields, post_load, validate

from app.schemas.user_schema import validate_password


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


class ForgotPasswordSchema(Schema):

    email = fields.String(
        required=True,
        validate=validate.Length(min=3, max=255)
    )

    @post_load
    def normalize_email(self, data, **kwargs):
        data["email"] = data["email"].strip().lower()
        return data


class ResetPasswordSchema(Schema):

    token = fields.String(
        required=True,
        validate=validate.Length(min=10, max=500)
    )
    password = fields.String(required=True, validate=validate_password)


class ChangePasswordSchema(Schema):

    current_password = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255)
    )
    new_password = fields.String(required=True, validate=validate_password)
