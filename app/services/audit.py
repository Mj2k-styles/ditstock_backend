"""
Journal d'audit (cahier des charges, F9.1).

record() ajoute une ligne à la session SANS valider : elle est enregistrée
dans la même transaction que l'action tracée (commit ou rollback ensemble).
"""
from decimal import Decimal

from flask import g, has_app_context

from app import db
from app.models.audit_log import AuditLog

# Actions tracées
CREATION = "CREATION"
MODIFICATION = "MODIFICATION"
ARCHIVAGE = "ARCHIVAGE"
CHANGEMENT_PRIX = "CHANGEMENT_PRIX"
AJUSTEMENT = "AJUSTEMENT"
TRANSFERT = "TRANSFERT"
IMPORT = "IMPORT"
REINITIALISATION_MOT_DE_PASSE = "REINITIALISATION_MOT_DE_PASSE"
CHANGEMENT_MOT_DE_PASSE = "CHANGEMENT_MOT_DE_PASSE"

# Champs jamais recopiés dans le journal
_SECRET_FIELDS = {"password", "password_hash"}


def _plain(value):
    """Valeur sérialisable en JSON (les prix sont des Decimal)."""
    if isinstance(value, Decimal):
        return str(value)
    return value


def _same(old, new):
    """Égalité tolérante pour les montants ("20" et Decimal("20.00"))."""
    if isinstance(old, Decimal) and new is not None:
        try:
            return old == Decimal(str(new))
        except ArithmeticError:
            return False
    return False


def changes(obj, data):
    """{champ: {"avant": ..., "apres": ...}} pour les champs réellement modifiés."""
    diff = {}
    for key, new in data.items():
        if key in _SECRET_FIELDS:
            continue
        old = getattr(obj, key, None)
        if _same(old, new):
            continue
        if _plain(old) != _plain(new):
            diff[key] = {"avant": _plain(old), "apres": _plain(new)}
    return diff


def record(action, entity, entity_id=None, details=None, user=None):
    """Ajoute une entrée au journal (l'appelant fait le commit)."""
    if user is None and has_app_context():
        user = g.get("current_user")
    db.session.add(AuditLog(
        user_id=user.id if user is not None else None,
        action=action,
        entity=entity,
        entity_id=entity_id,
        details={k: _plain(v) for k, v in (details or {}).items()},
    ))
