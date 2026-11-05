
from flask_restx import Namespace, Resource, fields
from app.models.product import Product

products_ns = Namespace(
    "products",
    description="Gestion des produits"
)

# Modèle utilisé pour documenter les données dans Swagger
product_model = products_ns.model("Product", {
    "sku": fields.String(required=True),
    "name": fields.String(required=True),
    "description": fields.String,
    "category_id": fields.Integer,
    "unit_price": fields.String(required=True),
    "minimum_stock": fields.Integer
})


@products_ns.route("/")
class ProductList(Resource):
    

    def get(self):
        products = Product.query.filter_by(is_archived=False).all()

        return [
            {
                "id": product.id,
                "sku": product.sku,
                "name": product.name,
                "description": product.description,
                "category_id": product.category_id,
                "unit_price": str(product.unit_price),
                "minimum_stock": product.minimum_stock
            }
            for product in products
        ], 200
    
@products_ns.route("/<int:product_id>")
class ProductDetail(Resource):
    
    def delete(self, product_id):
        from app import db

        product = Product.query.filter_by(
            id=product_id,
            is_archived=False
        ).first()

        if product is None:
            return {"message": "Produit introuvable"}, 404

        product.is_archived = True
        db.session.commit()

        return {
            "message": "Produit archivé avec succès"
        }, 200

    
    def get(self, product_id):
        # Rechercher le produit par son identifiant
        product = Product.query.filter_by(
            id=product_id,
            is_archived=False
        ).first()

        # Vérifier si le produit existe
        if product is None:
            return {"message": "Produit introuvable"}, 404

        # Retourner les informations du produit
        return {
            "id": product.id,
            "sku": product.sku,
            "name": product.name,
            "description": product.description,
            "category_id": product.category_id,
            "unit_price": str(product.unit_price),
            "minimum_stock": product.minimum_stock
        }, 200
    
    @products_ns.expect(product_model)
    def put(self, product_id):
        from flask import request
        from marshmallow import ValidationError
        from app.schemas.product_schema import ProductSchema
        from app import db

        # Rechercher le produit
        product = Product.query.filter_by(
            id=product_id,
            is_archived=False
        ).first()

        if product is None:
            return {"message": "Produit introuvable"}, 404

        # Vérifier les nouvelles données
        try:
            data = ProductSchema().load(request.get_json())
        except ValidationError as err:
            return {"errors": err.messages}, 400

        # Vérifier l'unicité du SKU
        existing_product = Product.query.filter(
            Product.sku == data["sku"],
            Product.id != product_id
        ).first()

        if existing_product:
            return {"message": "Ce SKU existe déjà"}, 409

        # Mettre à jour le produit
        for key, value in data.items():
            setattr(product, key, value)

        db.session.commit()

        return {
            "message": "Produit modifié avec succès",
            "id": product.id,
            "sku": product.sku,
            "name": product.name,
            "unit_price": str(product.unit_price)
        }, 200


    @products_ns.expect(product_model)
    def post(self):
        from flask import request
        from marshmallow import ValidationError
        from app.schemas.product_schema import ProductSchema
        from app import db

        schema = ProductSchema()

        try:
            data = schema.load(request.get_json())
        except ValidationError as err:
            return {"errors": err.messages}, 400

        # Vérifier si le SKU existe déjà
        existing_product = Product.query.filter_by(
            sku=data["sku"]
        ).first()

        if existing_product:
            return {"message": "Ce SKU existe déjà"}, 409

        # Créer le produit
        product = Product(**data)

        db.session.add(product)
        db.session.commit()

        return {
            "message": "Produit ajouté avec succès",
            "id": product.id,
            "sku": product.sku,
            "name": product.name
        }, 201


