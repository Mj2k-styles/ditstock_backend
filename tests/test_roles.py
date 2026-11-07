import pytest

from app import db
from app.utils.decorators import roles_required


def test_roles_required_rejects_unknown_role():
    with pytest.raises(ValueError):
        roles_required("superhero")


# ----- Lecture des produits : tous les rôles connectés -----

def test_products_list_requires_authentication(client):
    assert client.get("/api/products/").status_code == 401


@pytest.mark.parametrize(
    "headers_fixture",
    ["admin_headers", "gestionnaire_headers", "magasinier_headers"]
)
def test_all_roles_can_read_products(client, request, headers_fixture):
    headers = request.getfixturevalue(headers_fixture)

    assert client.get("/api/products/", headers=headers).status_code == 200


# ----- Création de produit : admin et gestionnaire -----

def test_magasinier_cannot_create_product(
    client, magasinier_headers, product_payload
):
    response = client.post(
        "/api/products/", json=product_payload, headers=magasinier_headers
    )

    assert response.status_code == 403


def test_gestionnaire_can_create_product(
    client, gestionnaire_headers, product_payload
):
    response = client.post(
        "/api/products/", json=product_payload, headers=gestionnaire_headers
    )

    assert response.status_code == 201


def test_admin_can_create_product(client, admin_headers, product_payload):
    response = client.post(
        "/api/products/", json=product_payload, headers=admin_headers
    )

    assert response.status_code == 201


def test_create_product_without_token(client, product_payload):
    response = client.post("/api/products/", json=product_payload)

    assert response.status_code == 401


# ----- Modification / suppression -----

def _create_product(client, headers, payload):
    return client.post(
        "/api/products/", json=payload, headers=headers
    ).get_json()["id"]


def test_magasinier_cannot_update_price(
    client, admin_headers, magasinier_headers, product_payload
):
    product_id = _create_product(client, admin_headers, product_payload)
    product_payload["unit_price"] = "99.00"

    response = client.put(
        f"/api/products/{product_id}",
        json=product_payload,
        headers=magasinier_headers
    )

    assert response.status_code == 403


def test_gestionnaire_can_update_product(
    client, admin_headers, gestionnaire_headers, product_payload
):
    product_id = _create_product(client, admin_headers, product_payload)
    product_payload["unit_price"] = "20.00"

    response = client.put(
        f"/api/products/{product_id}",
        json=product_payload,
        headers=gestionnaire_headers
    )

    assert response.status_code == 200
    assert response.get_json()["unit_price"] == "20.00"


def test_magasinier_cannot_delete_product(
    client, admin_headers, magasinier_headers, product_payload
):
    product_id = _create_product(client, admin_headers, product_payload)

    response = client.delete(
        f"/api/products/{product_id}", headers=magasinier_headers
    )

    assert response.status_code == 403


def test_gestionnaire_can_archive_product(
    client, admin_headers, gestionnaire_headers, product_payload
):
    product_id = _create_product(client, admin_headers, product_payload)

    response = client.delete(
        f"/api/products/{product_id}", headers=gestionnaire_headers
    )

    assert response.status_code == 200
    assert client.get(
        f"/api/products/{product_id}", headers=gestionnaire_headers
    ).status_code == 404


# ----- Effet immédiat des changements de compte -----

def test_deactivated_user_loses_access_immediately(
    client, magasinier, magasinier_headers
):
    magasinier.is_active = False
    db.session.commit()

    response = client.get("/api/products/", headers=magasinier_headers)

    assert response.status_code == 401


def test_role_change_applies_immediately(
    client, magasinier, gestionnaire_headers, magasinier_headers,
    product_payload
):
    # Le token du magasinier a été émis avec le rôle magasinier...
    magasinier.role = "gestionnaire"
    db.session.commit()

    # ... mais le rôle est relu en base : il peut maintenant créer un produit
    response = client.post(
        "/api/products/", json=product_payload, headers=magasinier_headers
    )

    assert response.status_code == 201
