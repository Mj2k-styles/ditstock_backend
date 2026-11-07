from datetime import datetime, timezone

import bcrypt
from flask import current_app

from app import db
from app.constants import ROLE_MAGASINIER

# bcrypt ne tient compte que des 72 premiers octets du mot de passe
BCRYPT_MAX_BYTES = 72


class User(db.Model):
    # Nom de la table dans la base de données
    __tablename__ = "users"

    # Identifiant unique
    id = db.Column(db.Integer, primary_key=True)

    # Adresse e-mail (sert d'identifiant de connexion, stockée en minuscules)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)

    # Mot de passe haché avec bcrypt (jamais en clair)
    password_hash = db.Column(db.String(255), nullable=False)

    # Nom complet
    full_name = db.Column(db.String(150), nullable=False)

    # Rôle : admin, gestionnaire ou magasinier
    role = db.Column(db.String(20), nullable=False, default=ROLE_MAGASINIER)

    # Un compte désactivé ne peut plus se connecter
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # Date de création
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    def set_password(self, plain_password):
        """Hache le mot de passe avec bcrypt et le stocke."""
        raw = plain_password.encode("utf-8")
        if len(raw) > BCRYPT_MAX_BYTES:
            raise ValueError("Mot de passe trop long (72 octets maximum)")

        rounds = current_app.config.get("BCRYPT_ROUNDS", 12)
        self.password_hash = bcrypt.hashpw(
            raw, bcrypt.gensalt(rounds=rounds)
        ).decode("utf-8")

    def check_password(self, plain_password):
        """Vérifie un mot de passe en clair par rapport au hash stocké."""
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                self.password_hash.encode("utf-8")
            )
        except ValueError:
            # Mot de passe trop long ou hash invalide
            return False

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
