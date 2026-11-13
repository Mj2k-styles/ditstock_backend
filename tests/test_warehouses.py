import pytest

# Les entrepôts sont gérés par l'administrateur (cahier des charges, section 2)
pytestmark = pytest.mark.usefixtures("as_admin")


def test_create_warehouse(client):
    response = client.post("/api/warehouses/", json={
        "name": "Entrepôt principal",
        "location": "Dakar",
        "description": "Stock principal"
    })

    assert response.status_code == 201
    assert response.json["name"] == "Entrepôt principal"


def test_duplicate_warehouse(client):
    data = {"name": "Entrepôt principal"}

    client.post("/api/warehouses/", json=data)
    response = client.post("/api/warehouses/", json=data)

    assert response.status_code == 409


def test_get_warehouses(client):
    client.post("/api/warehouses/", json={"name": "Entrepôt A"})

    response = client.get("/api/warehouses/")

    assert response.status_code == 200
    assert len(response.json) == 1


def test_update_warehouse(client):
    created = client.post(
        "/api/warehouses/",
        json={"name": "Entrepôt A"}
    )

    warehouse_id = created.json["id"]

    response = client.put(
        f"/api/warehouses/{warehouse_id}",
        json={"name": "Entrepôt B"}
    )

    assert response.status_code == 200
    assert response.json["name"] == "Entrepôt B"


def test_archive_warehouse(client):
    created = client.post(
        "/api/warehouses/",
        json={"name": "Entrepôt A"}
    )

    warehouse_id = created.json["id"]

    response = client.delete(f"/api/warehouses/{warehouse_id}")

    assert response.status_code == 200

    detail = client.get(f"/api/warehouses/{warehouse_id}")
    assert detail.status_code == 404
