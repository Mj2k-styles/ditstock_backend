"""Produits : champs complets (F2.1), recherche, filtres et pagination (F2.2)."""
import pytest

from app import db
from app.constants import MOVEMENT_ENTREE
from app.models.category import Category
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.warehouse import Warehouse
from app.services.movement_service import create_movement

pytestmark = pytest.mark.usefixtures("as_gestionnaire")


@pytest.fixture
def catalogue(app, gestionnaire):
    cat = Category(name="Quincaillerie")
    sup = Supplier(name="Sénégal Outils")
    wh1 = Warehouse(name="Central")
    wh2 = Warehouse(name="Annexe")
    db.session.add_all([cat, sup, wh1, wh2])
    db.session.flush()

    def product(sku, name, minimum, **extra):
        p = Product(sku=sku, name=name, unit_price=100, minimum_stock=minimum, **extra)
        db.session.add(p)
        db.session.flush()
        return p

    ok = product("VIS-01", "Vis à bois", 5, category_id=cat.id, supplier_id=sup.id)
    low = product("CLOU-01", "Clou 50mm", 10, category_id=cat.id)
    out = product("COLLE-01", "Colle forte", 3, supplier_id=sup.id)
    db.session.commit()

    def entry(p, wh, qty):
        create_movement({"type": MOVEMENT_ENTREE, "product_id": p.id,
                         "warehouse_id": wh.id, "quantity": qty}, gestionnaire)

    entry(ok, wh1, 20)
    entry(low, wh2, 4)
    return {"cat": cat, "sup": sup, "wh1": wh1, "wh2": wh2,
            "ok": ok, "low": low, "out": out}


def skus(response):
    data = response.get_json()
    items = data["items"] if isinstance(data, dict) else data
    return [p["sku"] for p in items]


def test_creation_avec_tous_les_champs(client, product_payload):
    product_payload.update({
        "unit": "boîte",
        "sale_price": "18.00",
        "image_url": "https://exemple.sn/clou.png",
    })
    created = client.post("/api/products/", json=product_payload)
    assert created.status_code == 201

    product = client.get(f"/api/products/{created.get_json()['id']}").get_json()
    assert product["unit"] == "boîte"
    assert product["unit_price"] == "12.50"
    assert product["sale_price"] == "18.00"
    assert product["image_url"] == "https://exemple.sn/clou.png"
    assert product["stock_total"] == 0


def test_unite_par_defaut(client, product_payload):
    created = client.post("/api/products/", json=product_payload)
    product = client.get(f"/api/products/{created.get_json()['id']}").get_json()
    assert product["unit"] == "pièce"
    assert product["sale_price"] is None


@pytest.mark.parametrize("field, value", [
    ("image_url", "javascript:alert(1)"),
    ("image_url", "pas une url"),
    ("sale_price", "-1"),
    ("unit", ""),
])
def test_champs_invalides_refuses(client, product_payload, field, value):
    product_payload[field] = value
    response = client.post("/api/products/", json=product_payload)
    assert response.status_code == 400
    assert field in response.get_json()["errors"]


def test_liste_simple_avec_stock_total(client, catalogue):
    response = client.get("/api/products/")
    assert response.status_code == 200
    stocks = {p["sku"]: p["stock_total"] for p in response.get_json()}
    assert stocks == {"VIS-01": 20, "CLOU-01": 4, "COLLE-01": 0}


def test_recherche_nom_ou_sku(client, catalogue):
    assert skus(client.get("/api/products/?q=clou")) == ["CLOU-01"]
    assert skus(client.get("/api/products/?q=vis-0")) == ["VIS-01"]


def test_filtres_categorie_et_fournisseur(client, catalogue):
    cat, sup = catalogue["cat"].id, catalogue["sup"].id
    assert skus(client.get(f"/api/products/?category_id={cat}")) == ["VIS-01", "CLOU-01"]
    assert skus(client.get(f"/api/products/?supplier_id={sup}")) == ["VIS-01", "COLLE-01"]


def test_filtre_entrepot_donne_le_stock_de_cet_entrepot(client, catalogue):
    response = client.get(f"/api/products/?warehouse_id={catalogue['wh2'].id}")
    assert [(p["sku"], p["stock_total"]) for p in response.get_json()] == [("CLOU-01", 4)]


@pytest.mark.parametrize("state, expected", [
    ("ok", ["VIS-01"]),
    ("alerte", ["CLOU-01"]),
    ("rupture", ["COLLE-01"]),
])
def test_filtre_etat_du_stock(client, catalogue, state, expected):
    assert skus(client.get(f"/api/products/?stock_state={state}")) == expected


def test_pagination_serveur(client, catalogue):
    data = client.get("/api/products/?page=2&per_page=2").get_json()
    assert data["total"] == 3
    assert data["pages"] == 2
    assert data["page"] == 2
    assert [p["sku"] for p in data["items"]] == ["COLLE-01"]


@pytest.mark.parametrize("query", [
    "stock_state=inconnu", "page=0", "per_page=500", "category_id=abc",
])
def test_filtres_invalides(client, catalogue, query):
    assert client.get(f"/api/products/?{query}").status_code == 400


def test_produit_archive_absent_des_listes(client, catalogue):
    client.delete(f"/api/products/{catalogue['out'].id}")
    assert "COLLE-01" not in skus(client.get("/api/products/"))
