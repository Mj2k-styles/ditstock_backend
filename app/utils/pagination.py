"""
Pagination commune aux listes de l'API.

Sans "page" ni "per_page" : la route renvoie un simple tableau.
Avec l'un des deux : { items, total, page, pages, per_page }.
"""
from flask import request
from marshmallow import Schema, ValidationError, fields, validate

DEFAULT_PER_PAGE = 50
MAX_PER_PAGE = 200


class PageSchema(Schema):
    page = fields.Integer(validate=validate.Range(min=1))
    per_page = fields.Integer(validate=validate.Range(min=1, max=MAX_PER_PAGE))


def read_page_args():
    """(arguments de pagination, None) ou (None, réponse 400)."""
    args = {k: v for k, v in request.args.items() if k in ("page", "per_page")}
    try:
        return PageSchema().load(args), None
    except ValidationError as err:
        return None, ({"errors": err.messages}, 400)


def paginate_or_list(query, page_args, dump):
    """Applique la pagination si elle est demandée, puis sérialise avec `dump`."""
    if not page_args:
        return dump(query.all())

    per_page = page_args.get("per_page", DEFAULT_PER_PAGE)
    pagination = query.paginate(
        page=page_args.get("page", 1), per_page=per_page, error_out=False
    )
    return {
        "items": dump(pagination.items),
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
        "per_page": per_page,
    }
