from flask import request
from flask_restx import Namespace, Resource, fields, reqparse
from marshmallow import ValidationError
from sqlalchemy import func, or_
from werkzeug.datastructures import FileStorage

from app import db
from app.constants import ROLE_GESTIONNAIRE
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.warehouse_stock import WarehouseStock
from app.schemas.product_schema import ProductFilterSchema, ProductSchema
from app.services import audit
from app.services.product_import import ProductImportError, import_products
from app.utils.decorators import login_required, roles_required
from app.utils.pagination import paginate_or_list

products_ns = Namespace(
    "products",
    description="Gestion des produits"
)

product_model = products_ns.model("Product", {
    "sku": fields.String(required=True),
    "name": fields.String(required=True),
    "description": fields.String,
    "category_id": fields.Integer,
    "supplier_id": fields.Integer,
    "unit": fields.String(example="pièce"),
    "unit_price": fields.String(required=True, description="Prix d'achat unitaire"),
    "sale_price": fields.String(description="Prix de vente unitaire"),
    "minimum_stock": fields.Integer,
    "image_url": fields.String(description="Adresse http(s) de l'image")
})

import_parser = reqparse.RequestParser()
import_parser.add_argument(
    "file", location="files", type=FileStorage, required=True,
    help="Fichier CSV (séparateur , ou ;)"
)

PRICE_FIELDS = ("unit_price", "sale_price")


def _money(value):
    return None if value is None else str(value)


def serialize(product, stock_total=None):
    data = {
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "description": product.description,
        "category_id": product.category_id,
        "supplier_id": product.supplier_id,
        "unit": product.unit,
        "unit_price": _money(product.unit_price),
        "sale_price": _money(product.sale_price),
        "minimum_stock": product.minimum_stock,
        "image_url": product.image_url,
    }
    if stock_total is not None:
        data["stock_total"] = int(stock_total)
    return data


def _stock_totals(warehouse_id=None):
    """Sous-requête : stock total par produit (entrepôts actifs ou un seul entrepôt)."""
    query = db.session.query(
        WarehouseStock.product_id.label("product_id"),
        func.sum(WarehouseStock.quantity).label("quantity"),
    ).join(Warehouse, Warehouse.id == WarehouseStock.warehouse_id).filter(
        Warehouse.is_archived.is_(False)
    )
    if warehouse_id is not None:
        query = query.filter(WarehouseStock.warehouse_id == warehouse_id)
    return query.group_by(WarehouseStock.product_id).subquery()


def _active_product(product_id):
    return Product.query.filter_by(id=product_id, is_archived=False).first()


@products_ns.route("/")
@products_ns.doc(security="Bearer")
class ProductList(Resource):

    @login_required
    @products_ns.doc(params={
        "q": "Recherche dans le nom et le SKU",
        "category_id": "Catégorie",
        "supplier_id": "Fournisseur",
        "warehouse_id": "Produits présents dans cet entrepôt (stock de cet entrepôt)",
        "stock_state": "ok, alerte (sous le seuil) ou rupture",
        "page": "Active la pagination (avec per_page, 50 par défaut)",
        "per_page": "Taille de page (200 maximum)",
    })
    def get(self):
        """Liste des produits actifs avec leur stock, filtrable et paginée."""
        try:
            filters = ProductFilterSchema().load(request.args.to_dict())
        except ValidationError as err:
            return {"errors": err.messages}, 400

        totals = _stock_totals(filters.get("warehouse_id"))
        quantity = func.coalesce(totals.c.quantity, 0)

        query = Product.query.filter(Product.is_archived.is_(False))
        if "warehouse_id" in filters:
            # Seulement les produits ayant une ligne de stock dans l'entrepôt
            query = query.join(totals, totals.c.product_id == Product.id)
        else:
            query = query.outerjoin(totals, totals.c.product_id == Product.id)
        query = query.add_columns(quantity.label("stock_total"))

        needle = (filters.get("q") or "").strip()
        if needle:
            pattern = f"%{needle}%"
            query = query.filter(or_(
                Product.name.ilike(pattern), Product.sku.ilike(pattern)
            ))
        if "category_id" in filters:
            query = query.filter(Product.category_id == filters["category_id"])
        if "supplier_id" in filters:
            query = query.filter(Product.supplier_id == filters["supplier_id"])

        state = filters.get("stock_state")
        if state == "rupture":
            query = query.filter(quantity <= 0)
        elif state == "alerte":
            query = query.filter(quantity > 0, quantity < Product.minimum_stock)
        elif state == "ok":
            query = query.filter(quantity > 0, quantity >= Product.minimum_stock)

        query = query.order_by(Product.id)
        page_args = {k: filters[k] for k in ("page", "per_page") if k in filters}

        def dump(rows):
            return [serialize(product, stock) for product, stock in rows]

        return paginate_or_list(query, page_args, dump), 200

    @roles_required(ROLE_GESTIONNAIRE)
    @products_ns.expect(product_model)
    def post(self):
        try:
            data = ProductSchema().load(
                request.get_json(silent=True) or {}
            )
        except ValidationError as err:
            return {"errors": err.messages}, 400

        existing_product = Product.query.filter_by(
            sku=data["sku"]
        ).first()

        if existing_product:
            return {"message": "Ce SKU existe déjà"}, 409

        product = Product(**data)
        db.session.add(product)
        db.session.flush()
        audit.record(audit.CREATION, "produit", product.id, {
            "sku": product.sku,
            "nom": product.name,
            "prix_achat": data["unit_price"],
            "prix_vente": data.get("sale_price"),
        })
        db.session.commit()

        return {
            "message": "Produit ajouté avec succès",
            "id": product.id,
            "sku": product.sku,
            "name": product.name
        }, 201


@products_ns.route("/import")
@products_ns.doc(security="Bearer")
class ProductImport(Resource):

    @roles_required(ROLE_GESTIONNAIRE)
    @products_ns.expect(import_parser)
    def post(self):
        """
        Import en masse depuis un CSV (cahier des charges, F2.3).

        Colonnes : sku, name, unit_price (obligatoires) ; description, unit,
        sale_price, minimum_stock, category, supplier, image_url (facultatives).
        Les noms français sont acceptés (nom, prix_achat, seuil_min...).
        Un SKU déjà existant est ignoré ; une ligne invalide est signalée.
        """
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            return {"message": "Aucun fichier reçu (champ « file »)."}, 400

        try:
            report = import_products(upload.read())
        except ProductImportError as err:
            # Rien n'est importé si le fichier est inutilisable
            db.session.rollback()
            return {"message": str(err)}, 400

        if report["created"]:
            audit.record(audit.IMPORT, "produit", None, {
                "fichier": upload.filename,
                "crees": report["created"],
                "ignores": len(report["skipped"]),
                "erreurs": len(report["errors"]),
            })
        db.session.commit()

        return {
            "message": f"{report['created']} produit(s) importé(s).",
            **report,
        }, 200


@products_ns.route("/<int:product_id>")
@products_ns.doc(security="Bearer")
class ProductDetail(Resource):

    @login_required
    def get(self, product_id):
        product = _active_product(product_id)

        if product is None:
            return {"message": "Produit introuvable"}, 404

        totals = _stock_totals()
        stock = db.session.query(totals.c.quantity).filter(
            totals.c.product_id == product.id
        ).scalar()
        return serialize(product, stock or 0), 200

    @roles_required(ROLE_GESTIONNAIRE)
    @products_ns.expect(product_model)
    def put(self, product_id):
        product = _active_product(product_id)

        if product is None:
            return {"message": "Produit introuvable"}, 404

        try:
            data = ProductSchema().load(
                request.get_json(silent=True) or {}
            )
        except ValidationError as err:
            return {"errors": err.messages}, 400

        existing_product = Product.query.filter(
            Product.sku == data["sku"],
            Product.id != product_id
        ).first()

        if existing_product:
            return {"message": "Ce SKU existe déjà"}, 409

        # Journal d'audit : les changements de prix sont tracés à part
        diff = audit.changes(product, data)
        prices = {k: v for k, v in diff.items() if k in PRICE_FIELDS}
        others = {k: v for k, v in diff.items() if k not in PRICE_FIELDS}

        for key, value in data.items():
            setattr(product, key, value)

        if prices:
            audit.record(audit.CHANGEMENT_PRIX, "produit", product.id, {
                "sku": product.sku, **prices
            })
        if others:
            audit.record(audit.MODIFICATION, "produit", product.id, {
                "sku": product.sku, **others
            })

        db.session.commit()

        return {
            "message": "Produit modifié avec succès",
            "id": product.id,
            "sku": product.sku,
            "name": product.name,
            "unit_price": _money(product.unit_price),
            "sale_price": _money(product.sale_price)
        }, 200

    @roles_required(ROLE_GESTIONNAIRE)
    def delete(self, product_id):
        product = _active_product(product_id)

        if product is None:
            return {"message": "Produit introuvable"}, 404

        # Jamais de suppression : un produit peut avoir des mouvements
        product.is_archived = True
        audit.record(audit.ARCHIVAGE, "produit", product.id, {
            "sku": product.sku, "nom": product.name
        })
        db.session.commit()

        return {"message": "Produit archivé avec succès"}, 200
