from flask import g, request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app import db
from app.constants import ROLE_ADMIN, ROLES
from app.models.user import User
from app.schemas.user_schema import (
    UserCreateSchema,
    UserUpdateSchema,
    user_schema,
    users_schema,
)
from app.services import audit
from app.utils.decorators import roles_required

users_ns = Namespace(
    "users",
    description="Gestion des utilisateurs (administrateur uniquement)"
)

# Modèles utilisés pour documenter les données dans Swagger
user_create_model = users_ns.model("UserCreate", {
    "email": fields.String(required=True),
    "password": fields.String(required=True),
    "full_name": fields.String(required=True),
    "role": fields.String(required=True, enum=list(ROLES)),
    "is_active": fields.Boolean(default=True)
})

user_update_model = users_ns.model("UserUpdate", {
    "email": fields.String,
    "password": fields.String,
    "full_name": fields.String,
    "role": fields.String(enum=list(ROLES)),
    "is_active": fields.Boolean
})


@users_ns.route("/")
@users_ns.doc(security="Bearer")
class UserList(Resource):

    @roles_required(ROLE_ADMIN)
    def get(self):
        users = User.query.order_by(User.id).all()
        return users_schema.dump(users), 200

    @roles_required(ROLE_ADMIN)
    @users_ns.expect(user_create_model)
    def post(self):
        try:
            data = UserCreateSchema().load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return {"errors": err.messages}, 400

        # Vérifier l'unicité de l'e-mail
        if User.query.filter_by(email=data["email"]).first():
            return {"message": "Cet e-mail existe déjà"}, 409

        password = data.pop("password")
        user = User(**data)
        user.set_password(password)

        db.session.add(user)
        db.session.flush()
        audit.record(audit.CREATION, "utilisateur", user.id, {
            "email": user.email, "role": user.role
        })
        db.session.commit()

        return {
            "message": "Utilisateur créé avec succès",
            "user": user_schema.dump(user)
        }, 201


@users_ns.route("/<int:user_id>")
@users_ns.doc(security="Bearer")
class UserDetail(Resource):

    @roles_required(ROLE_ADMIN)
    def get(self, user_id):
        user = db.session.get(User, user_id)

        if user is None:
            return {"message": "Utilisateur introuvable"}, 404

        return user_schema.dump(user), 200

    @roles_required(ROLE_ADMIN)
    @users_ns.expect(user_update_model)
    def put(self, user_id):
        user = db.session.get(User, user_id)

        if user is None:
            return {"message": "Utilisateur introuvable"}, 404

        try:
            data = UserUpdateSchema().load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return {"errors": err.messages}, 400

        # Un administrateur ne peut pas se retirer ses propres droits.
        # Cela garantit aussi qu'il reste toujours au moins un admin actif.
        if user.id == g.current_user.id:
            if data.get("role", user.role) != ROLE_ADMIN:
                return {
                    "message": "Vous ne pouvez pas modifier votre propre rôle"
                }, 400
            if data.get("is_active", user.is_active) is False:
                return {
                    "message": "Vous ne pouvez pas désactiver votre propre compte"
                }, 400

        # Vérifier l'unicité de l'e-mail
        if "email" in data:
            existing = User.query.filter(
                User.email == data["email"],
                User.id != user_id
            ).first()
            if existing:
                return {"message": "Cet e-mail existe déjà"}, 409

        # Le mot de passe passe par set_password pour être haché
        password = data.pop("password", None)
        details = audit.changes(user, data)
        if password is not None:
            user.set_password(password)
            details["mot_de_passe"] = "modifié"
        if details:
            audit.record(audit.MODIFICATION, "utilisateur", user.id, details)

        for key, value in data.items():
            setattr(user, key, value)

        db.session.commit()

        return {
            "message": "Utilisateur modifié avec succès",
            "user": user_schema.dump(user)
        }, 200

    @roles_required(ROLE_ADMIN)
    def delete(self, user_id):
        user = db.session.get(User, user_id)

        if user is None:
            return {"message": "Utilisateur introuvable"}, 404

        if user.id == g.current_user.id:
            return {
                "message": "Vous ne pouvez pas désactiver votre propre compte"
            }, 400

        # Désactivation plutôt que suppression : l'historique
        # (mouvements, audit) garde la trace de l'utilisateur.
        user.is_active = False
        audit.record(audit.ARCHIVAGE, "utilisateur", user.id, {
            "email": user.email
        })
        db.session.commit()

        return {"message": "Utilisateur désactivé avec succès"}, 200
