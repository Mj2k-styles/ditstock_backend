from marshmallow import (
    Schema,
    ValidationError,
    fields,
    post_load,
    validate,
)

from app.constants import ROLES

PASSWORD_MIN_LENGTH = 8


def validate_password(value):
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValidationError(
            f"Le mot de passe doit contenir au moins "
            f"{PASSWORD_MIN_LENGTH} caractères"
        )
    # Limite de bcrypt : 72 octets
    if len(value.encode("utf-8")) > 72:
        raise ValidationError(
            "Le mot de passe est trop long (72 octets maximum)"
        )


class UserCreateSchema(Schema):
    """Données attendues pour créer un utilisateur."""

    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate_password)
    full_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=150)
    )
    role = fields.String(required=True, validate=validate.OneOf(ROLES))
    is_active = fields.Boolean(load_default=True)

    @post_load
    def normalize_email(self, data, **kwargs):
        data["email"] = data["email"].strip().lower()
        return data


class UserUpdateSchema(Schema):
    """Données acceptées pour modifier un utilisateur (tout est optionnel)."""

    email = fields.Email()
    password = fields.String(validate=validate_password)
    full_name = fields.String(validate=validate.Length(min=1, max=150))
    role = fields.String(validate=validate.OneOf(ROLES))
    is_active = fields.Boolean()

    @post_load
    def normalize_email(self, data, **kwargs):
        if "email" in data:
            data["email"] = data["email"].strip().lower()
        return data


class UserSchema(Schema):
    """Représentation d'un utilisateur dans les réponses (sans mot de passe)."""

    id = fields.Integer()
    email = fields.String()
    full_name = fields.String()
    role = fields.String()
    is_active = fields.Boolean()
    created_at = fields.DateTime()


user_schema = UserSchema()
users_schema = UserSchema(many=True)
