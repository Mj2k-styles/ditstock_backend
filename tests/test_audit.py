"""Journal d'audit (F9.1) et traçabilité des prix et ajustements (règles de gestion)."""
import pytest

from app import db
from app.models.audit_log import AuditLog
from app.models.product import Product
from app.models.warehouse import Warehouse


def actions(**filters):
    return [
        (log.action, log.entity)
        for log in AuditLog.query.filter_by(**filters).order_by(AuditLog.id)
    ]


@pytest.fixture
def stock_setup(app):
    product = Product(sku="AUD-1", name="Marteau", unit_price=1000, minimum_stock=0)
    a, b = Warehouse(name="A"), Warehouse(name="B")
    db.session.add_all([product, a, b])
    db.session.commit()
    return product, a, b


def test_creation_et_changement_de_prix_traces(client, gestionnaire, gestionnaire_headers, product_payload):
    product_id = client.post(
        "/api/products/", json=product_payload, headers=gestionnaire_headers
    ).get_json()["id"]

    product_payload.update({"unit_price": "15.00", "name": "Clou 60mm"})
    client.put(f"/api/products/{product_id}", json=product_payload, headers=gestionnaire_headers)

    assert actions(entity_id=product_id) == [
        ("CREATION", "produit"), ("CHANGEMENT_PRIX", "produit"), ("MODIFICATION", "produit"),
    ]
    price = AuditLog.query.filter_by(action="CHANGEMENT_PRIX").one()
    assert price.user_id == gestionnaire.id
    assert price.details["unit_price"] == {"avant": "12.50", "apres": "15.00"}


def test_modification_sans_changement_non_tracee(client, gestionnaire_headers, product_payload):
    product_id = client.post(
        "/api/products/", json=product_payload, headers=gestionnaire_headers
    ).get_json()["id"]
    product_payload["unit_price"] = "12.5"  # même montant, autre écriture
    client.put(f"/api/products/{product_id}", json=product_payload, headers=gestionnaire_headers)

    assert actions(entity_id=product_id) == [("CREATION", "produit")]


def test_archivage_trace(client, gestionnaire_headers, product_payload):
    product_id = client.post(
        "/api/products/", json=product_payload, headers=gestionnaire_headers
    ).get_json()["id"]
    client.delete(f"/api/products/{product_id}", headers=gestionnaire_headers)
    assert ("ARCHIVAGE", "produit") in actions(entity_id=product_id)


def test_ajustement_et_transfert_traces(client, gestionnaire_headers, stock_setup):
    product, a, b = stock_setup
    base = {"product_id": product.id, "warehouse_id": a.id}
    client.post("/api/movements/", json={**base, "type": "ENTREE", "quantity": 10},
                headers=gestionnaire_headers)
    client.post("/api/movements/", json={**base, "type": "AJUSTEMENT", "quantity": -2,
                                         "reason": "Casse"}, headers=gestionnaire_headers)
    client.post("/api/movements/", json={**base, "type": "TRANSFERT", "quantity": 3,
                                         "warehouse_dest_id": b.id}, headers=gestionnaire_headers)

    assert actions(entity="produit") == [("AJUSTEMENT", "produit"), ("TRANSFERT", "produit")]
    adjustment = AuditLog.query.filter_by(action="AJUSTEMENT").one()
    assert adjustment.details["ecart"] == -2
    assert adjustment.details["motif"] == "Casse"


def test_ajustement_refuse_non_trace(client, gestionnaire_headers, stock_setup):
    product, a, _ = stock_setup
    response = client.post("/api/movements/", json={
        "type": "AJUSTEMENT", "product_id": product.id, "warehouse_id": a.id,
        "quantity": -5, "reason": "Inventaire",
    }, headers=gestionnaire_headers)
    assert response.status_code == 409
    assert AuditLog.query.count() == 0


def test_referentiels_et_utilisateurs_traces(client, admin_headers):
    cat = client.post("/api/categories/", json={"name": "Outils"}, headers=admin_headers).get_json()
    client.put(f"/api/categories/{cat['id']}", json={"name": "Outillage"}, headers=admin_headers)
    sup = client.post("/api/suppliers/", json={"name": "Fourni"}, headers=admin_headers).get_json()
    client.delete(f"/api/suppliers/{sup['id']}", headers=admin_headers)
    wh = client.post("/api/warehouses/", json={"name": "Nord"}, headers=admin_headers).get_json()
    client.put(f"/api/warehouses/{wh['id']}", json={"location": "Saint-Louis"}, headers=admin_headers)
    client.delete(f"/api/warehouses/{wh['id']}", headers=admin_headers)
    user = client.post("/api/users/", json={
        "email": "nouveau@test.sn", "password": "MotDePasse123",
        "full_name": "Nouveau", "role": "magasinier",
    }, headers=admin_headers).get_json()["user"]
    client.put(f"/api/users/{user['id']}", json={"role": "gestionnaire", "password": "AutreMotDePasse1"},
               headers=admin_headers)
    client.delete(f"/api/users/{user['id']}", headers=admin_headers)

    assert actions() == [
        ("CREATION", "catégorie"), ("MODIFICATION", "catégorie"),
        ("CREATION", "fournisseur"), ("ARCHIVAGE", "fournisseur"),
        ("CREATION", "entrepôt"), ("MODIFICATION", "entrepôt"), ("ARCHIVAGE", "entrepôt"),
        ("CREATION", "utilisateur"), ("MODIFICATION", "utilisateur"), ("ARCHIVAGE", "utilisateur"),
    ]
    change = AuditLog.query.filter_by(action="MODIFICATION", entity="utilisateur").one()
    assert change.details["role"] == {"avant": "magasinier", "apres": "gestionnaire"}
    assert change.details["mot_de_passe"] == "modifié"
    # Jamais de mot de passe ni de hash dans le journal
    for log in AuditLog.query:
        assert "MotDePasse" not in str(log.details)
        assert "$2b$" not in str(log.details)


def test_liste_paginee_et_filtree(client, admin, admin_headers):
    for name in ("C1", "C2", "C3"):
        client.post("/api/categories/", json={"name": name}, headers=admin_headers)

    data = client.get("/api/audit-logs/?page=1&per_page=2", headers=admin_headers).get_json()
    assert data["total"] == 3 and data["pages"] == 2
    first = data["items"][0]
    assert first["details"] == {"nom": "C3"}  # plus récent d'abord
    assert first["user_name"] == admin.full_name
    assert {"created_at", "action", "entity", "entity_id", "user_id"} <= set(first)

    filtered = client.get("/api/audit-logs/?entity=produit", headers=admin_headers).get_json()
    assert filtered == []


def test_filtre_invalide(client, admin_headers):
    assert client.get("/api/audit-logs/?page=0", headers=admin_headers).status_code == 400


@pytest.mark.parametrize("headers_fixture", ["gestionnaire_headers", "magasinier_headers"])
def test_journal_reserve_a_l_admin(client, request, headers_fixture):
    headers = request.getfixturevalue(headers_fixture)
    assert client.get("/api/audit-logs/", headers=headers).status_code == 403


def test_journal_sans_token(client):
    assert client.get("/api/audit-logs/").status_code == 401
