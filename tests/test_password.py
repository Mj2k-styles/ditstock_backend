"""Mot de passe oublié, réinitialisation et changement (F1.2)."""
import re

import pytest

from app.models.audit_log import AuditLog
from app.routes.auth import make_reset_token
from tests.conftest import PASSWORD, login

NEW_PASSWORD = "NouveauSecret42"


def outbox(app):
    return app.extensions.setdefault("outbox", [])


def token_from_mail(message):
    return re.search(r"token=([\w\-.]+)", message.get_content()).group(1)


def test_lien_envoye_puis_mot_de_passe_reinitialise(app, client, gestionnaire):
    response = client.post("/api/auth/forgot-password", json={"email": "Gestionnaire@test.sn "})
    assert response.status_code == 200

    [message] = outbox(app)
    assert message["To"] == gestionnaire.email
    assert "/reinitialiser-mot-de-passe?token=" in message.get_content()

    token = token_from_mail(message)
    response = client.post("/api/auth/reset-password", json={"token": token, "password": NEW_PASSWORD})
    assert response.status_code == 200

    assert login(client, gestionnaire.email, PASSWORD).status_code == 401
    assert login(client, gestionnaire.email, NEW_PASSWORD).status_code == 200
    assert AuditLog.query.filter_by(action="REINITIALISATION_MOT_DE_PASSE").count() == 1


def test_lien_a_usage_unique(app, client, gestionnaire):
    token = make_reset_token(gestionnaire)
    assert client.post("/api/auth/reset-password",
                       json={"token": token, "password": NEW_PASSWORD}).status_code == 200
    second = client.post("/api/auth/reset-password",
                         json={"token": token, "password": "EncoreAutre99"})
    assert second.status_code == 400


def test_meme_reponse_pour_un_email_inconnu(app, client, gestionnaire):
    known = client.post("/api/auth/forgot-password", json={"email": gestionnaire.email})
    unknown = client.post("/api/auth/forgot-password", json={"email": "personne@test.sn"})
    assert known.get_json() == unknown.get_json()
    assert len(outbox(app)) == 1


def test_compte_desactive_ne_recoit_rien(app, client, gestionnaire):
    gestionnaire.is_active = False
    client.post("/api/auth/forgot-password", json={"email": gestionnaire.email})
    assert outbox(app) == []


@pytest.mark.parametrize("token", ["faux", "x" * 40])
def test_jeton_invalide(client, token):
    response = client.post("/api/auth/reset-password", json={"token": token, "password": NEW_PASSWORD})
    assert response.status_code == 400


def test_jeton_expire(app, client, gestionnaire):
    token = make_reset_token(gestionnaire)
    app.config["PASSWORD_RESET_MAX_AGE"] = -1
    response = client.post("/api/auth/reset-password", json={"token": token, "password": NEW_PASSWORD})
    assert response.status_code == 400


def test_mot_de_passe_trop_court_refuse(client, gestionnaire):
    response = client.post("/api/auth/reset-password",
                           json={"token": make_reset_token(gestionnaire), "password": "court"})
    assert response.status_code == 400
    assert "password" in response.get_json()["errors"]


def test_changement_par_l_utilisateur_connecte(client, magasinier, magasinier_headers):
    response = client.post("/api/auth/change-password", headers=magasinier_headers,
                           json={"current_password": PASSWORD, "new_password": NEW_PASSWORD})
    assert response.status_code == 200
    assert login(client, magasinier.email, NEW_PASSWORD).status_code == 200
    log = AuditLog.query.filter_by(action="CHANGEMENT_MOT_DE_PASSE").one()
    assert log.user_id == magasinier.id


def test_changement_refuse_si_mot_de_passe_actuel_faux(client, magasinier_headers):
    response = client.post("/api/auth/change-password", headers=magasinier_headers,
                           json={"current_password": "mauvais", "new_password": NEW_PASSWORD})
    assert response.status_code == 400


def test_changement_sans_token(client):
    response = client.post("/api/auth/change-password",
                           json={"current_password": PASSWORD, "new_password": NEW_PASSWORD})
    assert response.status_code == 401


def test_email_invalide(client):
    assert client.post("/api/auth/forgot-password", json={}).status_code == 400
