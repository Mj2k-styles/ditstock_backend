from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app import db
from app.models.category import Category
from app.schemas.category_schema import CategorySchema
from app.constants import ROLE_GESTIONNAIRE
from app.utils.decorators import login_required, roles_required


categories_ns = Namespace(
    "categories",
    description="Gestion des catégories"
)

category_model = categories_ns.model("Category", {
    "name": fields.String(required=True),
    "description": fields.String
})


@categories_ns.route("/")
@categories_ns.doc(security="Bearer")
class CategoryList(Resource):

    @login_required
    def get(self):
        categories = Category.query.filter_by(
            is_archived=False
        ).all()

        return [
            {
                "id": category.id,
                "name": category.name,
                "description": category.description
            }
            for category in categories
        ], 200

    @roles_required(ROLE_GESTIONNAIRE)
    @categories_ns.expect(category_model)
    def post(self):
        data_json = request.get_json(silent=True)

        if data_json is None:
            return {"message": "Les données JSON sont obligatoires"}, 400

        try:
            data = CategorySchema().load(data_json)
        except ValidationError as err:
            return {"errors": err.messages}, 400

        existing_category = Category.query.filter_by(
            name=data["name"]
        ).first()

        if existing_category:
            return {"message": "Cette catégorie existe déjà"}, 409

        category = Category(**data)

        db.session.add(category)
        db.session.commit()

        return {
            "message": "Catégorie ajoutée avec succès",
            "id": category.id,
            "name": category.name
        }, 201


@categories_ns.route("/<int:category_id>")
@categories_ns.doc(security="Bearer")
class CategoryDetail(Resource):

    @login_required
    def get(self, category_id):
        category = Category.query.filter_by(
            id=category_id,
            is_archived=False
        ).first()

        if category is None:
            return {"message": "Catégorie introuvable"}, 404

        return {
            "id": category.id,
            "name": category.name,
            "description": category.description
        }, 200

    @roles_required(ROLE_GESTIONNAIRE)
    @categories_ns.expect(category_model)
    def put(self, category_id):
        category = Category.query.filter_by(
            id=category_id,
            is_archived=False
        ).first()

        if category is None:
            return {"message": "Catégorie introuvable"}, 404

        data_json = request.get_json(silent=True)

        if data_json is None:
            return {"message": "Les données JSON sont obligatoires"}, 400

        try:
            data = CategorySchema().load(data_json)
        except ValidationError as err:
            return {"errors": err.messages}, 400

        existing_category = Category.query.filter(
            Category.name == data["name"],
            Category.id != category_id
        ).first()

        if existing_category:
            return {"message": "Cette catégorie existe déjà"}, 409

        for key, value in data.items():
            setattr(category, key, value)

        db.session.commit()

        return {
            "message": "Catégorie modifiée avec succès",
            "id": category.id,
            "name": category.name
        }, 200

    @roles_required(ROLE_GESTIONNAIRE)
    def delete(self, category_id):
        category = Category.query.filter_by(
            id=category_id,
            is_archived=False
        ).first()

        if category is None:
            return {"message": "Catégorie introuvable"}, 404

        category.is_archived = True
        db.session.commit()

        return {
            "message": "Catégorie archivée avec succès"
        }, 200