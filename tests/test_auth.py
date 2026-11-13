from datetime import timedelta

from flask_jwt_extended import create_access_token

from tests.conftest import PASSWORD, login


def test_login_success(client, admin):
    response = login(client, admin.email)
    data = response.get_json()

    assert response.status_code == 200
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["email"] == admin.email
    assert "password_hash" not in data["user"]
    assert "password" not in data["user"]


def test_login_email_is_case_insensitive(client, admin):
    response = login(client, "ADMIN@Test.SN")

    assert response.status_code == 200


def test_login_wrong_password(client, admin):
    response = login(client, admin.email, "mauvais-mot-de-passe")

    assert response.status_code == 401
    assert response.get_json()["message"] == "Identifiants invalides"


def test_login_unknown_email_gives_same_message(client, admin):
    response = login(client, "inconnu@test.sn")

    assert response.status_code == 401
    assert response.get_json()["message"] == "Identifiants invalides"


def test_login_inactive_user(client, app):
    from tests.conftest import make_user
    user = make_user("inactif@test.sn", "magasinier", is_active=False)

    response = login(client, user.email, PASSWORD)

    assert response.status_code == 403


def test_login_missing_fields(client):
    response = client.post("/api/auth/login", json={"email": "a@test.sn"})

    assert response.status_code == 400
    assert "password" in response.get_json()["errors"]


def test_login_without_body(client):
    response = client.post("/api/auth/login")

    assert response.status_code == 400


def test_refresh_success(client, admin):
    refresh_token = login(client, admin.email).get_json()["refresh_token"]

    response = client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {refresh_token}"}
    )

    assert response.status_code == 200
    assert response.get_json()["access_token"]


def test_new_access_token_is_usable(client, admin):
    refresh_token = login(client, admin.email).get_json()["refresh_token"]
    new_access = client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {refresh_token}"}
    ).get_json()["access_token"]

    response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {new_access}"}
    )

    assert response.status_code == 200
    assert response.get_json()["email"] == admin.email


def test_refresh_rejects_access_token(client, admin):
    access_token = login(client, admin.email).get_json()["access_token"]

    response = client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 401


def test_refresh_without_token(client):
    response = client.post("/api/auth/refresh")

    assert response.status_code == 401


def test_refresh_fails_for_deactivated_user(client, admin, magasinier):
    from app import db
    refresh_token = login(client, magasinier.email).get_json()["refresh_token"]
    magasinier.is_active = False
    db.session.commit()

    response = client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {refresh_token}"}
    )

    assert response.status_code == 401


def test_me_rejects_refresh_token(client, admin):
    refresh_token = login(client, admin.email).get_json()["refresh_token"]

    response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {refresh_token}"}
    )

    assert response.status_code == 401


def test_me_without_token(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert "manquant" in response.get_json()["message"]


def test_me_with_invalid_token(client):
    response = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer pas.un.token"}
    )

    assert response.status_code == 401
    assert response.get_json()["message"] == "Token invalide"


def test_me_with_expired_token(client, app, admin):
    token = create_access_token(
        identity=str(admin.id), expires_delta=timedelta(seconds=-1)
    )

    response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401
    assert "expiré" in response.get_json()["message"]


def test_token_with_non_numeric_identity_is_rejected(client, app):
    token = create_access_token(identity="abc")

    response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401


def test_token_of_deleted_user_is_rejected(client, app):
    token = create_access_token(identity="9999")

    response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401
