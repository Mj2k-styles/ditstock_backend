from functools import wraps

from flask import g
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import (
    JWTExtendedException,
    NoAuthorizationError,
)
from jwt.exceptions import ExpiredSignatureError, PyJWTError

from app import db
from app.constants import ROLE_ADMIN, ROLES
from app.models.user import User


def _jwt_error_response(error):
    """Transforme une erreur JWT en réponse JSON (toujours 401)."""
    if isinstance(error, ExpiredSignatureError):
        return {"message": "Le token a expiré"}, 401
    if isinstance(error, NoAuthorizationError):
        return {"message": "Token d'authentification manquant"}, 401
    return {"message": "Token invalide"}, 401


def _authenticate(refresh=False):
    """
    Vérifie le token JWT de la requête et charge l'utilisateur.

    Retourne (utilisateur, None) si tout va bien,
    sinon (None, réponse d'erreur).
    """
    try:
        verify_jwt_in_request(refresh=refresh)
    except (JWTExtendedException, PyJWTError) as error:
        return None, _jwt_error_response(error)

    try:
        user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return None, ({"message": "Token invalide"}, 401)

    # Le rôle est relu en base : un changement de rôle ou une
    # désactivation est donc pris en compte immédiatement.
    user = db.session.get(User, user_id)
    if user is None or not user.is_active:
        return None, ({"message": "Compte introuvable ou désactivé"}, 401)

    return user, None


def roles_required(*roles):
    """
    Réserve une route aux utilisateurs connectés ayant l'un des rôles donnés.
    L'administrateur a tous les droits : il passe toujours.

    Exemple :
        @roles_required("gestionnaire")
        def post(self): ...
    """
    for role in roles:
        if role not in ROLES:
            raise ValueError(f"Rôle inconnu : {role}")

    allowed_roles = set(roles) | {ROLE_ADMIN}

    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            user, error = _authenticate()
            if error:
                return error

            if user.role not in allowed_roles:
                return {"message": "Accès refusé : droits insuffisants"}, 403

            # Utilisateur disponible dans la route via g.current_user
            g.current_user = user
            return function(*args, **kwargs)

        return wrapper

    return decorator


# Tout utilisateur connecté (quel que soit son rôle)
login_required = roles_required(*ROLES)


def refresh_token_required(function):
    """Réserve une route à un refresh token valide (utilisé par /refresh)."""

    @wraps(function)
    def wrapper(*args, **kwargs):
        user, error = _authenticate(refresh=True)
        if error:
            return error

        g.current_user = user
        return function(*args, **kwargs)

    return wrapper
