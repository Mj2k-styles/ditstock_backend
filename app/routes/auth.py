from flask import g, request
from flask_jwt_extended import create_access_token, create_refresh_token
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.models.user import User
from app.schemas.auth_schema import LoginSchema
from app.schemas.user_schema import user_schema
from app.utils.decorators import login_required, refresh_token_required

auth_ns = Namespace(
    "auth",
    description="Authentification (JWT)"
)

# Modèles utilisés pour documenter les données dans Swagger
login_model = auth_ns.model("Login", {
    "email": fields.String(required=True, example="admin@ditstock.sn"),
    "password": fields.String(required=True)
})

# Utilisateur factice : quand l'e-mail n'existe pas, on fait quand même une
# vérification bcrypt pour ne pas révéler par le temps de réponse si un
# compte existe. Le hash est calculé une seule fois.
_dummy_user = None


def _fake_password_check(password):
    global _dummy_user
    if _dummy_user is None:
        _dummy_user = User()
        _dummy_user.set_password("mot-de-passe-factice")
    _dummy_user.check_password(password)


def _claims(user):
    return {"role": user.role}


@auth_ns.route("/login")
class Login(Resource):

    @auth_ns.expect(login_model)
    def post(self):
        try:
            data = LoginSchema().load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return {"errors": err.messages}, 400

        user = User.query.filter_by(email=data["email"]).first()

        if user is None:
            _fake_password_check(data["password"])
            return {"message": "Identifiants invalides"}, 401

        if not user.check_password(data["password"]):
            return {"message": "Identifiants invalides"}, 401

        if not user.is_active:
            return {"message": "Ce compte est désactivé"}, 403

        return {
            "access_token": create_access_token(
                identity=str(user.id), additional_claims=_claims(user)
            ),
            "refresh_token": create_refresh_token(identity=str(user.id)),
            "user": user_schema.dump(user)
        }, 200


@auth_ns.route("/refresh")
class Refresh(Resource):

    @auth_ns.doc(security="Bearer")
    @refresh_token_required
    def post(self):
        user = g.current_user

        return {
            "access_token": create_access_token(
                identity=str(user.id), additional_claims=_claims(user)
            )
        }, 200


@auth_ns.route("/me")
class Me(Resource):

    @auth_ns.doc(security="Bearer")
    @login_required
    def get(self):
        return user_schema.dump(g.current_user), 200
