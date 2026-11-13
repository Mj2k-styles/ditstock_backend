import hashlib

from flask import current_app, g, request
from flask_jwt_extended import create_access_token, create_refresh_token
from flask_restx import Namespace, Resource, fields
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from marshmallow import ValidationError

from app import db
from app.models.user import User
from app.schemas.auth_schema import (
    ChangePasswordSchema,
    ForgotPasswordSchema,
    LoginSchema,
    ResetPasswordSchema,
)
from app.schemas.user_schema import user_schema
from app.services import audit
from app.services.mailer import send_mail
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
forgot_model = auth_ns.model("ForgotPassword", {
    "email": fields.String(required=True)
})
reset_model = auth_ns.model("ResetPassword", {
    "token": fields.String(required=True),
    "password": fields.String(required=True)
})
change_model = auth_ns.model("ChangePassword", {
    "current_password": fields.String(required=True),
    "new_password": fields.String(required=True)
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


# --- Réinitialisation du mot de passe (cahier des charges, F1.2) ---
# Le lien contient un jeton signé avec SECRET_KEY, valable 30 minutes.
# Il embarque une empreinte du hash actuel : dès que le mot de passe change,
# le lien n'est plus utilisable (usage unique).

def _reset_serializer():
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"], salt="password-reset"
    )


def _password_fingerprint(user):
    return hashlib.sha256(user.password_hash.encode("utf-8")).hexdigest()[:16]


def make_reset_token(user):
    return _reset_serializer().dumps(
        {"uid": user.id, "fp": _password_fingerprint(user)}
    )


def user_from_reset_token(token):
    """L'utilisateur du jeton, ou None si le jeton est invalide ou expiré."""
    try:
        payload = _reset_serializer().loads(
            token, max_age=current_app.config["PASSWORD_RESET_MAX_AGE"]
        )
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("uid"), int):
        return None
    user = db.session.get(User, payload["uid"])
    if user is None or not user.is_active:
        return None
    if payload.get("fp") != _password_fingerprint(user):
        return None
    return user


GENERIC_FORGOT_MESSAGE = (
    "Si un compte actif correspond à cet e-mail, un lien de "
    "réinitialisation vient d'être envoyé."
)


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


@auth_ns.route("/forgot-password")
class ForgotPassword(Resource):

    @auth_ns.expect(forgot_model)
    def post(self):
        """Envoie un lien de réinitialisation (même réponse si l'e-mail est inconnu)."""
        try:
            data = ForgotPasswordSchema().load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return {"errors": err.messages}, 400

        user = User.query.filter_by(email=data["email"]).first()
        if user is not None and user.is_active:
            link = (
                f"{current_app.config['FRONTEND_URL']}"
                f"/reinitialiser-mot-de-passe?token={make_reset_token(user)}"
            )
            send_mail(
                user.email,
                "[DitStock] Réinitialisation de votre mot de passe",
                f"Bonjour {user.full_name},\n\n"
                "Pour choisir un nouveau mot de passe, ouvrez ce lien "
                f"(valable 30 minutes) :\n{link}\n\n"
                "Si vous n'êtes pas à l'origine de cette demande, "
                "ignorez ce message.\n",
            )

        return {"message": GENERIC_FORGOT_MESSAGE}, 200


@auth_ns.route("/reset-password")
class ResetPassword(Resource):

    @auth_ns.expect(reset_model)
    def post(self):
        """Définit un nouveau mot de passe à partir du lien reçu par e-mail."""
        try:
            data = ResetPasswordSchema().load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return {"errors": err.messages}, 400

        user = user_from_reset_token(data["token"])
        if user is None:
            return {
                "message": "Lien invalide ou expiré : refaites une demande."
            }, 400

        user.set_password(data["password"])
        audit.record(
            audit.REINITIALISATION_MOT_DE_PASSE, "utilisateur", user.id,
            {"email": user.email}, user=user
        )
        db.session.commit()

        return {
            "message": "Mot de passe modifié : vous pouvez vous connecter."
        }, 200


@auth_ns.route("/change-password")
class ChangePassword(Resource):

    @auth_ns.doc(security="Bearer")
    @auth_ns.expect(change_model)
    @login_required
    def post(self):
        """Change le mot de passe de l'utilisateur connecté."""
        try:
            data = ChangePasswordSchema().load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return {"errors": err.messages}, 400

        user = g.current_user
        if not user.check_password(data["current_password"]):
            return {"message": "Mot de passe actuel incorrect"}, 400

        user.set_password(data["new_password"])
        audit.record(audit.CHANGEMENT_MOT_DE_PASSE, "utilisateur", user.id)
        db.session.commit()

        return {"message": "Mot de passe modifié avec succès"}, 200


@auth_ns.route("/me")
class Me(Resource):

    @auth_ns.doc(security="Bearer")
    @login_required
    def get(self):
        return user_schema.dump(g.current_user), 200
