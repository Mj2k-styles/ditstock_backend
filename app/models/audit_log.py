from datetime import datetime, timezone

from app import db


class AuditLog(db.Model):
    """
    Journal des actions sensibles (cahier des charges, F9.1) :
    qui (user_id), quoi (action, entity, entity_id, details), quand (created_at).
    Les lignes ne sont jamais modifiées ni supprimées par l'application.
    """

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)

    # Auteur de l'action (vide pour une action du système)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
    )

    # Verbe : CREATION, MODIFICATION, ARCHIVAGE, AJUSTEMENT...
    action = db.Column(db.String(50), nullable=False, index=True)

    # Type d'élément concerné : produit, utilisateur, entrepôt...
    entity = db.Column(db.String(50), nullable=False, index=True)
    entity_id = db.Column(db.Integer, nullable=True)

    # Détails libres (ancien et nouveau prix, écart, champs modifiés...)
    details = db.Column(db.JSON, nullable=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    user = db.relationship("User")

    def __repr__(self):
        return f"<AuditLog {self.action} {self.entity} {self.entity_id}>"
