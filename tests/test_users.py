from tests.conftest import PASSWORD, login, make_user

NEW_USER = {
    "email": "nouveau@test.sn",
    "password": "NouveauPass123",
    "full_name": "Nouvel Utilisateur",
    "role": "magasinier",
}


# ----- Contrôle d'accès : admin uniquement -----

def test_users_require_authentication(client):
    assert client.get("/api/users/").status_code == 401
    assert client.post("/api/users/", json=NEW_USER).status_code == 401


def test_gestionnaire_cannot_access_users(client, gestionnaire_headers):
    assert client.get(
        "/api/users/", headers=gestionnaire_headers
    ).status_code == 403
    assert client.post(
        "/api/users/", json=NEW_USER, headers=gestionnaire_headers
    ).status_code == 403


def test_magasinier_cannot_access_users(client, magasinier_headers):
    assert client.get(
        "/api/users/", headers=magasinier_headers
    ).status_code == 403
    assert client.delete(
        "/api/users/1", headers=magasinier_headers
    ).status_code == 403


# ----- Création -----

def test_admin_can_create_user(client, admin_headers):
    response = client.post("/api/users/", json=NEW_USER, headers=admin_headers)
    data = response.get_json()

    assert response.status_code == 201
    assert data["user"]["email"] == "nouveau@test.sn"
    assert data["user"]["role"] == "magasinier"
    assert data["user"]["is_active"] is True
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


def test_created_user_can_log_in(client, admin_headers):
    client.post("/api/users/", json=NEW_USER, headers=admin_headers)

    response = login(client, NEW_USER["email"], NEW_USER["password"])

    assert response.status_code == 200


def test_created_user_email_is_lowercased(client, admin_headers):
    payload = {**NEW_USER, "email": "MAJUSCULE@Test.SN"}

    response = client.post("/api/users/", json=payload, headers=admin_headers)

    assert response.get_json()["user"]["email"] == "majuscule@test.sn"


def test_create_user_duplicate_email(client, admin_headers, magasinier):
    payload = {**NEW_USER, "email": magasinier.email}

    response = client.post("/api/users/", json=payload, headers=admin_headers)

    assert response.status_code == 409


def test_create_user_invalid_role(client, admin_headers):
    payload = {**NEW_USER, "role": "superhero"}

    response = client.post("/api/users/", json=payload, headers=admin_headers)

    assert response.status_code == 400
    assert "role" in response.get_json()["errors"]


def test_create_user_invalid_email(client, admin_headers):
    payload = {**NEW_USER, "email": "pas-un-email"}

    response = client.post("/api/users/", json=payload, headers=admin_headers)

    assert response.status_code == 400
    assert "email" in response.get_json()["errors"]


def test_create_user_short_password(client, admin_headers):
    payload = {**NEW_USER, "password": "court"}

    response = client.post("/api/users/", json=payload, headers=admin_headers)

    assert response.status_code == 400
    assert "password" in response.get_json()["errors"]


def test_create_user_too_long_password(client, admin_headers):
    payload = {**NEW_USER, "password": "x" * 73}

    response = client.post("/api/users/", json=payload, headers=admin_headers)

    assert response.status_code == 400


def test_create_user_missing_fields(client, admin_headers):
    response = client.post("/api/users/", json={}, headers=admin_headers)

    assert response.status_code == 400
    assert set(response.get_json()["errors"]) >= {
        "email", "password", "full_name", "role"
    }


# ----- Lecture -----

def test_admin_can_list_users(client, admin_headers, magasinier):
    response = client.get("/api/users/", headers=admin_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert len(data) == 2
    assert all("password_hash" not in user for user in data)


def test_admin_can_get_user(client, admin_headers, magasinier):
    response = client.get(
        f"/api/users/{magasinier.id}", headers=admin_headers
    )

    assert response.status_code == 200
    assert response.get_json()["email"] == magasinier.email


def test_get_unknown_user(client, admin_headers):
    response = client.get("/api/users/9999", headers=admin_headers)

    assert response.status_code == 404


# ----- Modification -----

def test_admin_can_update_user(client, admin_headers, magasinier):
    response = client.put(
        f"/api/users/{magasinier.id}",
        json={"full_name": "Nouveau Nom", "role": "gestionnaire"},
        headers=admin_headers
    )
    data = response.get_json()["user"]

    assert response.status_code == 200
    assert data["full_name"] == "Nouveau Nom"
    assert data["role"] == "gestionnaire"


def test_update_password_is_hashed_and_works(
    client, admin_headers, magasinier
):
    response = client.put(
        f"/api/users/{magasinier.id}",
        json={"password": "AutreMotDePasse456"},
        headers=admin_headers
    )

    assert response.status_code == 200
    assert login(client, magasinier.email, PASSWORD).status_code == 401
    assert login(
        client, magasinier.email, "AutreMotDePasse456"
    ).status_code == 200


def test_update_email_duplicate(
    client, admin_headers, magasinier, gestionnaire
):
    response = client.put(
        f"/api/users/{magasinier.id}",
        json={"email": gestionnaire.email},
        headers=admin_headers
    )

    assert response.status_code == 409


def test_update_keeping_same_email_is_allowed(
    client, admin_headers, magasinier
):
    response = client.put(
        f"/api/users/{magasinier.id}",
        json={"email": magasinier.email},
        headers=admin_headers
    )

    assert response.status_code == 200


def test_update_invalid_role(client, admin_headers, magasinier):
    response = client.put(
        f"/api/users/{magasinier.id}",
        json={"role": "superhero"},
        headers=admin_headers
    )

    assert response.status_code == 400


def test_update_unknown_user(client, admin_headers):
    response = client.put(
        "/api/users/9999", json={"full_name": "X"}, headers=admin_headers
    )

    assert response.status_code == 404


def test_admin_can_deactivate_user_through_update(
    client, admin_headers, magasinier
):
    response = client.put(
        f"/api/users/{magasinier.id}",
        json={"is_active": False},
        headers=admin_headers
    )

    assert response.status_code == 200
    assert login(client, magasinier.email).status_code == 403


def test_admin_cannot_change_own_role(client, admin, admin_headers):
    response = client.put(
        f"/api/users/{admin.id}",
        json={"role": "magasinier"},
        headers=admin_headers
    )

    assert response.status_code == 400


def test_admin_cannot_deactivate_self_through_update(
    client, admin, admin_headers
):
    response = client.put(
        f"/api/users/{admin.id}",
        json={"is_active": False},
        headers=admin_headers
    )

    assert response.status_code == 400


def test_admin_can_update_own_name(client, admin, admin_headers):
    response = client.put(
        f"/api/users/{admin.id}",
        json={"full_name": "Nouveau Nom Admin", "role": "admin"},
        headers=admin_headers
    )

    assert response.status_code == 200


def test_admin_can_demote_another_admin(client, admin_headers):
    other = make_user("admin2@test.sn", "admin")

    response = client.put(
        f"/api/users/{other.id}",
        json={"role": "magasinier"},
        headers=admin_headers
    )

    assert response.status_code == 200


# ----- Désactivation (DELETE) -----

def test_admin_can_deactivate_user(client, admin_headers, magasinier):
    response = client.delete(
        f"/api/users/{magasinier.id}", headers=admin_headers
    )

    assert response.status_code == 200
    # L'utilisateur existe toujours mais est désactivé
    user = client.get(
        f"/api/users/{magasinier.id}", headers=admin_headers
    ).get_json()
    assert user["is_active"] is False


def test_admin_cannot_delete_self(client, admin, admin_headers):
    response = client.delete(f"/api/users/{admin.id}", headers=admin_headers)

    assert response.status_code == 400


def test_delete_unknown_user(client, admin_headers):
    response = client.delete("/api/users/9999", headers=admin_headers)

    assert response.status_code == 404
