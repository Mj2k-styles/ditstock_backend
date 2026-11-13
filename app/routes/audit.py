from flask import request
from flask_restx import Namespace, Resource
from marshmallow import Schema, ValidationError, fields, validate

from app.constants import ROLE_ADMIN
from app.models.audit_log import AuditLog
from app.utils.decorators import roles_required
from app.utils.pagination import MAX_PER_PAGE, paginate_or_list

audit_ns = Namespace(
    "audit-logs",
    description="Journal d'audit (administrateur uniquement)"
)


class AuditFilterSchema(Schema):
    action = fields.String(validate=validate.Length(max=50))
    entity = fields.String(validate=validate.Length(max=50))
    user_id = fields.Integer()
    page = fields.Integer(validate=validate.Range(min=1))
    per_page = fields.Integer(validate=validate.Range(min=1, max=MAX_PER_PAGE))


def serialize(log):
    return {
        "id": log.id,
        "created_at": log.created_at.isoformat(),
        "user_id": log.user_id,
        "user_name": log.user.full_name if log.user else "Système",
        "action": log.action,
        "entity": log.entity,
        "entity_id": log.entity_id,
        "details": log.details,
    }


@audit_ns.route("/")
@audit_ns.doc(security="Bearer", params={
    "action": "CREATION, MODIFICATION, CHANGEMENT_PRIX, AJUSTEMENT...",
    "entity": "produit, utilisateur, entrepôt, fournisseur, catégorie",
    "user_id": "Auteur de l'action",
    "page": "Active la pagination (avec per_page, 50 par défaut)",
    "per_page": "Taille de page (200 maximum)",
})
class AuditLogList(Resource):

    @roles_required(ROLE_ADMIN)
    def get(self):
        """Actions sensibles : qui, quoi, quand (plus récentes d'abord)."""
        try:
            filters = AuditFilterSchema().load(request.args.to_dict())
        except ValidationError as err:
            return {"errors": err.messages}, 400

        query = AuditLog.query
        for key in ("action", "entity", "user_id"):
            if key in filters:
                query = query.filter(getattr(AuditLog, key) == filters[key])
        query = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())

        page_args = {k: filters[k] for k in ("page", "per_page") if k in filters}
        return paginate_or_list(
            query, page_args, lambda logs: [serialize(log) for log in logs]
        ), 200
