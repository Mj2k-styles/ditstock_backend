import pytest

# Routes protégées : toutes les requêtes sont faites en tant que gestionnaire
pytestmark = pytest.mark.usefixtures("as_gestionnaire")


def test_create_product(client, gestionnaire_headers):
    response = client.post(
        "/api/products/",
        json={
            "sku": "TEST001",
            "name": "Ordinateur Test",
            "unit_price": "250000",
            "minimum_stock": 5
        },
        headers=gestionnaire_headers
    )
    assert response.status_code == 201


def test_get_products(client, gestionnaire_headers):
    client.post(
        "/api/products/",
        json={
            "sku": "TEST002",
            "name": "Clavier Test",
            "unit_price": "15000"
        },
        headers=gestionnaire_headers
    )

    response = client.get(
        "/api/products/",
        headers=gestionnaire_headers
    )
    assert response.status_code == 200


def test_archive_product(client, gestionnaire_headers):
    created = client.post(
        "/api/products/",
        json={
            "sku": "TEST003",
            "name": "Souris Test",
            "unit_price": "10000"
        },
        headers=gestionnaire_headers
    )

    product_id = created.json["id"]

    response = client.delete(
        f"/api/products/{product_id}",
        headers=gestionnaire_headers
    )
    assert response.status_code == 200


def test_create_category(client):
    response = client.post("/api/categories/", json={
        "name": "Catégorie Test",
        "description": "Catégorie pour les tests"
    })
    assert response.status_code == 201
    assert response.json["name"] == "Catégorie Test"


def test_get_categories(client):
    client.post("/api/categories/", json={"name": "Informatique"})
    response = client.get("/api/categories/")
    assert response.status_code == 200
    assert len(response.json) == 1


def test_archive_category(client):
    created = client.post("/api/categories/", json={
        "name": "Catégorie à archiver"
    })
    category_id = created.json["id"]

    response = client.delete(f"/api/categories/{category_id}")
    assert response.status_code == 200

    detail = client.get(f"/api/categories/{category_id}")
    assert detail.status_code == 404