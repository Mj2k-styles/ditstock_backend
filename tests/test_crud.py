def test_create_product(client):
    response = client.post("/api/products/", json={
        "sku": "TEST001",
        "name": "Ordinateur Test",
        "unit_price": "250000",
        "minimum_stock": 5
    })
    assert response.status_code == 201
    assert response.json["name"] == "Ordinateur Test"


def test_get_products(client):
    client.post("/api/products/", json={
        "sku": "TEST002",
        "name": "Clavier Test",
        "unit_price": "15000"
    })
    response = client.get("/api/products/")
    assert response.status_code == 200
    assert len(response.json) == 1


def test_archive_product(client):
    created = client.post("/api/products/", json={
        "sku": "TEST003",
        "name": "Souris Test",
        "unit_price": "10000"
    })
    product_id = created.json["id"]

    response = client.delete(f"/api/products/{product_id}")
    assert response.status_code == 200

    detail = client.get(f"/api/products/{product_id}")
    assert detail.status_code == 404


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