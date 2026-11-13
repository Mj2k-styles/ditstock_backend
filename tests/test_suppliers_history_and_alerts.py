"""Historique des approvisionnements (F4.2) et alertes e-mail de seuil (F7.2)."""
import pytest

from app import db
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.warehouse import Warehouse
from tests.conftest import make_user


@pytest.fixture
def setup(app):
    product = Product(sku="HIS-1", name="Ciment", unit_price=5000, minimum_stock=5)
    supplier = Supplier(name="Ciments du Sahel", contact="Fatou Diallo")
    archived = Supplier(name="Ancien", is_archived=True)
    warehouse = Warehouse(name="Dépôt")
    db.session.add_all([product, supplier, archived, warehouse])
    db.session.commit()
    return product, supplier, archived, warehouse


def move(client, headers, **payload):
    return client.post("/api/movements/", json=payload, headers=headers)


def test_contact_du_fournisseur(client, gestionnaire_headers):
    created = client.post("/api/suppliers/", headers=gestionnaire_headers,
                          json={"name": "SDE", "contact": "Awa Ndiaye"}).get_json()
    supplier = client.get(f"/api/suppliers/{created['id']}", headers=gestionnaire_headers).get_json()
    assert supplier["contact"] == "Awa Ndiaye"


def test_historique_des_approvisionnements(client, gestionnaire_headers, setup):
    product, supplier, _, warehouse = setup
    base = {"product_id": product.id, "warehouse_id": warehouse.id}
    move(client, gestionnaire_headers, type="ENTREE", quantity=10, supplier_id=supplier.id,
         reference="BL-1", **base)
    move(client, gestionnaire_headers, type="ENTREE", quantity=4, **base)
    move(client, gestionnaire_headers, type="ENTREE", quantity=6, supplier_id=supplier.id,
         reference="BL-2", **base)

    history = client.get(f"/api/suppliers/{supplier.id}/movements",
                         headers=gestionnaire_headers).get_json()
    assert [m["reference"] for m in history] == ["BL-2", "BL-1"]
    assert history[0]["supplier_name"] == "Ciments du Sahel"

    page = client.get(f"/api/suppliers/{supplier.id}/movements?page=1&per_page=1",
                      headers=gestionnaire_headers).get_json()
    assert page["total"] == 2 and page["pages"] == 2

    filtered = client.get(f"/api/movements/?supplier_id={supplier.id}",
                          headers=gestionnaire_headers).get_json()
    assert len(filtered) == 2


def test_historique_fournisseur_inconnu(client, gestionnaire_headers):
    assert client.get("/api/suppliers/999/movements", headers=gestionnaire_headers).status_code == 404


def test_fournisseur_reserve_aux_entrees(client, gestionnaire_headers, setup):
    product, supplier, _, warehouse = setup
    move(client, gestionnaire_headers, type="ENTREE", quantity=10,
         product_id=product.id, warehouse_id=warehouse.id)
    response = move(client, gestionnaire_headers, type="SORTIE", quantity=1, supplier_id=supplier.id,
                    product_id=product.id, warehouse_id=warehouse.id, reason="Vente")
    assert response.status_code == 400
    assert "supplier_id" in response.get_json()["errors"]


def test_fournisseur_archive_refuse(client, gestionnaire_headers, setup):
    product, _, archived, warehouse = setup
    response = move(client, gestionnaire_headers, type="ENTREE", quantity=1, supplier_id=archived.id,
                    product_id=product.id, warehouse_id=warehouse.id)
    assert response.status_code == 404


def test_email_quand_le_stock_passe_sous_le_seuil(app, client, gestionnaire, magasinier_headers, setup):
    make_user("inactif@test.sn", "gestionnaire", is_active=False)
    product, _, _, warehouse = setup
    base = {"product_id": product.id, "warehouse_id": warehouse.id}
    move(client, magasinier_headers, type="ENTREE", quantity=8, **base)
    outbox = app.extensions.setdefault("outbox", [])
    assert outbox == []

    move(client, magasinier_headers, type="SORTIE", quantity=2, reason="Vente", **base)  # 6 : au-dessus
    assert outbox == []

    move(client, magasinier_headers, type="SORTIE", quantity=3, reason="Vente", **base)  # 3 < 5
    assert len(outbox) == 1
    assert outbox[0]["To"] == gestionnaire.email
    assert "Ciment" in outbox[0]["Subject"]
    assert "est passé à 3" in outbox[0].get_content()

    move(client, magasinier_headers, type="SORTIE", quantity=1, reason="Vente", **base)  # reste bas
    assert len(outbox) == 1


def test_echec_d_envoi_sans_effet_sur_le_mouvement(app, client, gestionnaire, magasinier_headers,
                                                   setup, monkeypatch):
    from app.services import movement_service

    def broken(*args, **kwargs):
        raise RuntimeError("SMTP indisponible")

    monkeypatch.setattr(movement_service, "send_mail", broken)
    product, _, _, warehouse = setup
    base = {"product_id": product.id, "warehouse_id": warehouse.id}
    move(client, magasinier_headers, type="ENTREE", quantity=6, **base)
    response = move(client, magasinier_headers, type="SORTIE", quantity=5, reason="Vente", **base)
    assert response.status_code == 201
