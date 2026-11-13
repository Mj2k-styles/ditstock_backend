"""Import de produits depuis un fichier CSV (cahier des charges, F2.3)."""
import csv
import io

from marshmallow import ValidationError

from app import db
from app.models.category import Category
from app.models.product import Product
from app.models.supplier import Supplier
from app.schemas.product_schema import ProductSchema

MAX_ROWS = 1000

# Noms de colonnes acceptés (anglais ou français) -> champ du produit
ALIASES = {
    "sku": "sku", "reference": "sku", "référence": "sku",
    "name": "name", "nom": "name",
    "description": "description",
    "unit": "unit", "unite": "unit", "unité": "unit",
    "unit_price": "unit_price", "prix_achat": "unit_price", "prix d'achat": "unit_price",
    "sale_price": "sale_price", "prix_vente": "sale_price", "prix de vente": "sale_price",
    "minimum_stock": "minimum_stock", "seuil_min": "minimum_stock", "seuil": "minimum_stock",
    "category": "category", "categorie": "category", "catégorie": "category",
    "supplier": "supplier", "fournisseur": "supplier",
    "image_url": "image_url", "image": "image_url",
}
REQUIRED = ("sku", "name", "unit_price")
NUMERIC = ("unit_price", "sale_price", "minimum_stock")


class ProductImportError(Exception):
    """Fichier inutilisable (format, en-têtes, taille)."""


def _decode(raw):
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ProductImportError("Encodage du fichier non reconnu (UTF-8 attendu).")


def _reader(text):
    first_line = text.split("\n", 1)[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ProductImportError("Le fichier est vide.")

    columns = {}
    for header in reader.fieldnames:
        key = ALIASES.get((header or "").strip().lower())
        if key:
            columns[header] = key
    missing = [c for c in REQUIRED if c not in columns.values()]
    if missing:
        raise ProductImportError(
            "Colonnes obligatoires manquantes : " + ", ".join(missing)
        )
    return reader, columns


def _lookup(model):
    """{nom en minuscules: id} des éléments actifs d'un référentiel."""
    query = db.session.query(model.id, model.name)
    if hasattr(model, "is_archived"):
        query = query.filter(model.is_archived.is_(False))
    return {name.strip().lower(): id_ for id_, name in query}


def import_products(raw):
    """
    Crée les produits valides du fichier. Retourne un rapport :
    { created, skipped: [{line, sku, reason}], errors: [{line, sku, errors}] }.
    L'appelant fait le commit.
    """
    reader, columns = _reader(_decode(raw))
    categories = _lookup(Category)
    suppliers = _lookup(Supplier)
    existing = {sku for (sku,) in db.session.query(Product.sku)}

    created, skipped, errors = 0, [], []
    for index, row in enumerate(reader):
        line = index + 2  # ligne 1 = en-têtes
        if index >= MAX_ROWS:
            raise ProductImportError(f"Trop de lignes : {MAX_ROWS} au maximum.")

        values = {}
        for header, key in columns.items():
            value = (row.get(header) or "").strip()
            if value == "":
                continue
            if key in NUMERIC:
                value = value.replace(" ", "").replace(",", ".")
            values[key] = value

        if not values:
            continue  # ligne vide
        sku = values.get("sku", "")
        row_errors = {}

        category = values.pop("category", None)
        if category is not None:
            if category.lower() in categories:
                values["category_id"] = categories[category.lower()]
            else:
                row_errors["category"] = [f"Catégorie inconnue : {category}"]
        supplier = values.pop("supplier", None)
        if supplier is not None:
            if supplier.lower() in suppliers:
                values["supplier_id"] = suppliers[supplier.lower()]
            else:
                row_errors["supplier"] = [f"Fournisseur inconnu : {supplier}"]

        try:
            data = ProductSchema().load(values)
        except ValidationError as err:
            row_errors.update(err.messages)
        if row_errors:
            errors.append({"line": line, "sku": sku, "errors": row_errors})
            continue

        if data["sku"] in existing:
            skipped.append({"line": line, "sku": data["sku"], "reason": "SKU déjà existant"})
            continue

        db.session.add(Product(**data))
        existing.add(data["sku"])
        created += 1

    return {"created": created, "skipped": skipped, "errors": errors}
