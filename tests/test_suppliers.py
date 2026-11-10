import pytest

# Routes protégées : toutes les requêtes sont faites en tant que gestionnaire
pytestmark = pytest.mark.usefixtures("as_gestionnaire")


def test_create_supplier(client):
    response = client.post("/api/suppliers/", json={
        "name": "Fournisseur Test",
        "email": "test@example.com",
        "phone": "770000000",
        "address": "Dakar"
    })

    assert response.status_code == 201
    assert response.json["name"] == "Fournisseur Test"


def test_get_suppliers(client):
    client.post("/api/suppliers/", json={
        "name": "Fournisseur Test"
    })

    response = client.get("/api/suppliers/")

    assert response.status_code == 200
    assert len(response.json) == 1


def test_update_supplier(client):
    created = client.post("/api/suppliers/", json={
        "name": "Ancien nom"
    })

    supplier_id = created.json["id"]

    response = client.put(
        f"/api/suppliers/{supplier_id}",
        json={"name": "Nouveau nom"}
    )

    assert response.status_code == 200
    assert response.json["name"] == "Nouveau nom"


def test_archive_supplier(client):
    created = client.post("/api/suppliers/", json={
        "name": "Fournisseur à archiver"
    })

    supplier_id = created.json["id"]

    response = client.delete(f"/api/suppliers/{supplier_id}")

    assert response.status_code == 200

    detail = client.get(f"/api/suppliers/{supplier_id}")
    assert detail.status_code == 404


def test_supplier_without_name(client):
    response = client.post("/api/suppliers/", json={
        "email": "test@example.com"
    })

    assert response.status_code == 400