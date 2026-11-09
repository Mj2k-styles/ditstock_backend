import pytest


# Toutes les routes de l'API (hors /health et /api/auth/login) exigent un token
PROTECTED_ROUTES = [
    ("get", "/api/categories/"),
    ("post", "/api/categories/"),
    ("get", "/api/categories/1"),
    ("put", "/api/categories/1"),
    ("delete", "/api/categories/1"),
    ("get", "/api/suppliers/"),
    ("post", "/api/suppliers/"),
    ("get", "/api/suppliers/1"),
    ("put", "/api/suppliers/1"),
    ("delete", "/api/suppliers/1"),
    ("get", "/api/warehouses/"),
    ("post", "/api/warehouses/"),
    ("get", "/api/warehouses/1"),
    ("put", "/api/warehouses/1"),
    ("delete", "/api/warehouses/1"),
    ("get", "/api/warehouse-stocks/"),
    ("post", "/api/warehouse-stocks/"),
    ("get", "/api/alerts/"),
    ("get", "/api/dashboard/stats"),
    ("get", "/api/exports/stock/csv"),
    ("get", "/api/exports/stock/pdf"),
    ("get", "/api/products/"),
    ("get", "/api/users/"),
]

# Écritures et exports réservés au gestionnaire (et à l'admin)
MANAGER_ONLY_ROUTES = [
    ("post", "/api/categories/"),
    ("put", "/api/categories/1"),
    ("delete", "/api/categories/1"),
    ("post", "/api/suppliers/"),
    ("put", "/api/suppliers/1"),
    ("delete", "/api/suppliers/1"),
    ("post", "/api/warehouses/"),
    ("put", "/api/warehouses/1"),
    ("delete", "/api/warehouses/1"),
    ("get", "/api/exports/stock/csv"),
    ("get", "/api/exports/stock/pdf"),
]

# Lectures ouvertes à tout utilisateur connecté
READ_ROUTES = [
    "/api/categories/",
    "/api/suppliers/",
    "/api/warehouses/",
    "/api/warehouse-stocks/",
    "/api/alerts/",
    "/api/dashboard/stats",
]


@pytest.mark.parametrize("method, url", PROTECTED_ROUTES)
def test_route_sans_token_refusee(client, method, url):
    response = getattr(client, method)(url, json={})

    assert response.status_code == 401


def test_health_reste_public(client):
    assert client.get("/health/").status_code == 200


@pytest.mark.parametrize("method, url", MANAGER_ONLY_ROUTES)
def test_magasinier_ne_peut_pas_modifier_le_referentiel(
    client, magasinier_headers, method, url
):
    response = getattr(client, method)(url, json={}, headers=magasinier_headers)

    assert response.status_code == 403


@pytest.mark.parametrize("url", READ_ROUTES)
def test_magasinier_peut_consulter(client, magasinier_headers, url):
    response = client.get(url, headers=magasinier_headers)

    assert response.status_code == 200


def test_magasinier_peut_saisir_le_stock(client, magasinier_headers):
    # Champs absents : la requête passe le contrôle d'accès puis échoue en validation
    response = client.post(
        "/api/warehouse-stocks/", json={}, headers=magasinier_headers
    )

    assert response.status_code == 404


@pytest.mark.parametrize("fmt", ["csv", "pdf"])
def test_gestionnaire_peut_exporter(client, gestionnaire_headers, fmt):
    response = client.get(
        f"/api/exports/stock/{fmt}", headers=gestionnaire_headers
    )

    assert response.status_code == 200


def test_admin_peut_modifier_le_referentiel(client, admin_headers):
    response = client.post(
        "/api/categories/", json={"name": "Quincaillerie"}, headers=admin_headers
    )

    assert response.status_code == 201
