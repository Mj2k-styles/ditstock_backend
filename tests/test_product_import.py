"""Import de produits par fichier CSV (F2.3)."""
import io

import pytest

from app import db
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.product import Product
from app.models.supplier import Supplier


def upload(client, content, headers, filename="produits.csv", encoding="utf-8"):
    data = {"file": (io.BytesIO(content.encode(encoding)), filename)}
    return client.post(
        "/api/products/import", data=data, headers=headers,
        content_type="multipart/form-data",
    )


@pytest.fixture
def referentiels(app):
    db.session.add_all([Category(name="Bureautique"), Supplier(name="Papeterie")])
    db.session.add(Product(sku="EXIST-1", name="Déjà là", unit_price=1))
    db.session.commit()


def test_import_complet_avec_separateur_point_virgule(client, gestionnaire_headers, referentiels):
    csv = (
        "sku;nom;prix_achat;prix_vente;seuil_min;unite;categorie;fournisseur\n"
        "BUR-1;Ramette A4;3 000,50;4500;40;paquet;Bureautique;Papeterie\n"
        "BUR-2;Stylos;5000;;12;boîte;;\n"
    )
    response = upload(client, csv, gestionnaire_headers)

    assert response.status_code == 200
    body = response.get_json()
    assert body["created"] == 2
    assert body["errors"] == [] and body["skipped"] == []

    ramette = Product.query.filter_by(sku="BUR-1").one()
    assert str(ramette.unit_price) == "3000.50"
    assert ramette.unit == "paquet"
    assert ramette.category_id == Category.query.one().id
    assert ramette.supplier_id == Supplier.query.one().id
    assert AuditLog.query.filter_by(action="IMPORT").count() == 1


def test_import_signale_doublons_et_lignes_invalides(client, gestionnaire_headers, referentiels):
    csv = (
        "sku,name,unit_price,category\n"
        "EXIST-1,Doublon base,10,\n"
        "NEW-1,Nouveau,10,\n"
        "NEW-1,Doublon fichier,10,\n"
        "NEW-2,,10,\n"
        "NEW-3,Prix faux,abc,\n"
        "NEW-4,Catégorie,10,Inconnue\n"
        ",,,\n"
    )
    body = upload(client, csv, gestionnaire_headers).get_json()

    assert body["created"] == 1
    assert [(s["line"], s["sku"]) for s in body["skipped"]] == [(2, "EXIST-1"), (4, "NEW-1")]
    errors = {e["line"]: e["errors"] for e in body["errors"]}
    assert set(errors) == {5, 6, 7}
    assert "name" in errors[5]
    assert "unit_price" in errors[6]
    assert "category" in errors[7]


def test_import_accepte_un_fichier_windows(client, gestionnaire_headers):
    csv = "sku;nom;prix_achat\r\nWIN-1;Équerre;1500\r\n"
    body = upload(client, csv, gestionnaire_headers, encoding="cp1252").get_json()
    assert body["created"] == 1
    assert Product.query.filter_by(sku="WIN-1").one().name == "Équerre"


@pytest.mark.parametrize("content, message", [
    ("", "vide"),
    ("sku,name\nA,B\n", "unit_price"),
])
def test_fichier_inutilisable(client, gestionnaire_headers, content, message):
    response = upload(client, content, gestionnaire_headers)
    assert response.status_code == 400
    assert message in response.get_json()["message"]


def test_fichier_absent(client, gestionnaire_headers):
    response = client.post(
        "/api/products/import", data={}, headers=gestionnaire_headers,
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


def test_trop_de_lignes(client, gestionnaire_headers):
    rows = "".join(f"S{i},P{i},1\n" for i in range(1001))
    response = upload(client, "sku,name,unit_price\n" + rows, gestionnaire_headers)
    assert response.status_code == 400
    assert Product.query.count() == 0


def test_magasinier_ne_peut_pas_importer(client, magasinier_headers):
    response = upload(client, "sku,name,unit_price\nA,B,1\n", magasinier_headers)
    assert response.status_code == 403


def test_import_sans_token(client):
    assert upload(client, "sku,name,unit_price\nA,B,1\n", {}).status_code == 401
