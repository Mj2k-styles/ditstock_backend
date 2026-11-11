"""
Tests des règles de gestion des mouvements de stock.

Règles du cahier des charges :
- le stock n'est jamais modifié directement, seulement par un mouvement ;
- une sortie supérieure au stock disponible est refusée ;
- un ajustement exige un motif ;
- le mouvement et la mise à jour du stock forment une seule transaction.
"""
from datetime import datetime

import pytest

from app import db
from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.models.warehouse import Warehouse
from app.models.warehouse_stock import WarehouseStock
from app.services import movement_service

URL = "/api/movements/"


# ----------------------------------------------------------------- helpers

@pytest.fixture
def product(app):
    product = Product(sku="MV-001", name="Clou 50mm", unit_price=10,
                      minimum_stock=5)
    db.session.add(product)
    db.session.commit()
    return product


@pytest.fixture
def wh1(app):
    warehouse = Warehouse(name="Entrepôt A")
    db.session.add(warehouse)
    db.session.commit()
    return warehouse


@pytest.fixture
def wh2(app):
    warehouse = Warehouse(name="Entrepôt B")
    db.session.add(warehouse)
    db.session.commit()
    return warehouse


def quantity(warehouse, product):
    """Quantité en stock lue directement en base (0 si pas de ligne)."""
    db.session.expire_all()
    row = WarehouseStock.query.filter_by(
        warehouse_id=warehouse.id, product_id=product.id
    ).first()
    return row.quantity if row else None


def movement_count():
    return StockMovement.query.count()


def move(client, headers, **payload):
    return client.post(URL, json=payload, headers=headers)


def entree(client, headers, product, warehouse, qty, **extra):
    return move(client, headers, type="ENTREE", product_id=product.id,
                warehouse_id=warehouse.id, quantity=qty, **extra)


def sortie(client, headers, product, warehouse, qty, **extra):
    return move(client, headers, type="SORTIE", product_id=product.id,
                warehouse_id=warehouse.id, quantity=qty, **extra)


def transfert(client, headers, product, src, dest, qty, **extra):
    return move(client, headers, type="TRANSFERT", product_id=product.id,
                warehouse_id=src.id, warehouse_dest_id=dest.id,
                quantity=qty, **extra)


def ajustement(client, headers, product, warehouse, delta, **extra):
    return move(client, headers, type="AJUSTEMENT", product_id=product.id,
                warehouse_id=warehouse.id, quantity=delta, **extra)


# ------------------------------------------------------------------ ENTREE

def test_entree_creates_stock_and_movement(
    client, gestionnaire, gestionnaire_headers, product, wh1
):
    response = entree(client, gestionnaire_headers, product, wh1, 20,
                      reference="BL-2026-001")
    data = response.get_json()

    assert response.status_code == 201
    assert quantity(wh1, product) == 20
    assert data["stock"] == [
        {"warehouse_id": wh1.id, "product_id": product.id, "quantity": 20}
    ]
    assert data["movement"]["type"] == "ENTREE"
    assert data["movement"]["reference"] == "BL-2026-001"
    assert data["movement"]["user_id"] == gestionnaire.id
    assert data["movement"]["product_name"] == "Clou 50mm"
    assert movement_count() == 1


def test_entree_adds_to_existing_stock(
    client, gestionnaire_headers, product, wh1
):
    entree(client, gestionnaire_headers, product, wh1, 20)
    entree(client, gestionnaire_headers, product, wh1, 5)

    assert quantity(wh1, product) == 25
    assert WarehouseStock.query.count() == 1
    assert movement_count() == 2


# ------------------------------------------------------------------ SORTIE

def test_sortie_decreases_stock(client, gestionnaire_headers, product, wh1):
    entree(client, gestionnaire_headers, product, wh1, 20)

    response = sortie(client, gestionnaire_headers, product, wh1, 8,
                      reason="Vente")

    assert response.status_code == 201
    assert quantity(wh1, product) == 12
    assert response.get_json()["movement"]["reason"] == "Vente"


def test_sortie_of_exact_stock_is_allowed(
    client, gestionnaire_headers, product, wh1
):
    entree(client, gestionnaire_headers, product, wh1, 10)

    response = sortie(client, gestionnaire_headers, product, wh1, 10)

    assert response.status_code == 201
    assert quantity(wh1, product) == 0


def test_sortie_refused_when_stock_insufficient(
    client, gestionnaire_headers, product, wh1
):
    entree(client, gestionnaire_headers, product, wh1, 5)

    response = sortie(client, gestionnaire_headers, product, wh1, 6)

    assert response.status_code == 409
    assert "insuffisant" in response.get_json()["message"].lower()
    assert "disponible : 5" in response.get_json()["message"]


def test_refused_sortie_changes_nothing(
    client, gestionnaire_headers, product, wh1
):
    entree(client, gestionnaire_headers, product, wh1, 5)

    sortie(client, gestionnaire_headers, product, wh1, 6)

    # Ni le stock ni l'historique ne changent
    assert quantity(wh1, product) == 5
    assert movement_count() == 1


def test_sortie_refused_when_product_never_stocked(
    client, gestionnaire_headers, product, wh1
):
    response = sortie(client, gestionnaire_headers, product, wh1, 1)

    assert response.status_code == 409
    assert movement_count() == 0


def test_sortie_checks_the_right_warehouse(
    client, gestionnaire_headers, product, wh1, wh2
):
    # Du stock dans A ne permet pas une sortie dans B
    entree(client, gestionnaire_headers, product, wh1, 50)

    response = sortie(client, gestionnaire_headers, product, wh2, 1)

    assert response.status_code == 409
    assert quantity(wh1, product) == 50


def test_conditional_update_never_goes_negative(app, product, wh1):
    """Deux sorties « simultanées » ne peuvent pas passer sous 0."""
    db.session.add(WarehouseStock(
        warehouse_id=wh1.id, product_id=product.id, quantity=10
    ))
    db.session.commit()

    first = movement_service._change_stock(wh1.id, product.id, -8)
    second = movement_service._change_stock(wh1.id, product.id, -8)
    db.session.commit()

    assert first is True
    assert second is False
    assert quantity(wh1, product) == 2


# --------------------------------------------------------------- TRANSFERT

def test_transfert_moves_stock_between_warehouses(
    client, gestionnaire_headers, product, wh1, wh2
):
    entree(client, gestionnaire_headers, product, wh1, 30)

    response = transfert(client, gestionnaire_headers, product, wh1, wh2, 12)
    data = response.get_json()

    assert response.status_code == 201
    assert quantity(wh1, product) == 18
    assert quantity(wh2, product) == 12
    assert data["movement"]["warehouse_dest_id"] == wh2.id
    assert data["movement"]["warehouse_dest_name"] == "Entrepôt B"
    assert {s["warehouse_id"]: s["quantity"] for s in data["stock"]} == {
        wh1.id: 18, wh2.id: 12
    }
    # Un seul mouvement pour un transfert (en plus de l'entrée initiale)
    assert movement_count() == 2


def test_transfert_does_not_change_total_stock(
    client, gestionnaire_headers, product, wh1, wh2
):
    entree(client, gestionnaire_headers, product, wh1, 30)
    transfert(client, gestionnaire_headers, product, wh1, wh2, 12)

    total = sum(s.quantity for s in WarehouseStock.query.all())

    assert total == 30


def test_transfert_refused_when_source_insufficient(
    client, gestionnaire_headers, product, wh1, wh2
):
    entree(client, gestionnaire_headers, product, wh1, 5)

    response = transfert(client, gestionnaire_headers, product, wh1, wh2, 6)

    assert response.status_code == 409
    assert quantity(wh1, product) == 5
    assert quantity(wh2, product) is None  # destination non touchée
    assert movement_count() == 1


def test_transfert_to_same_warehouse_is_refused(
    client, gestionnaire_headers, product, wh1
):
    entree(client, gestionnaire_headers, product, wh1, 5)

    response = transfert(client, gestionnaire_headers, product, wh1, wh1, 1)

    assert response.status_code == 400
    assert quantity(wh1, product) == 5


def test_transfert_requires_destination(
    client, gestionnaire_headers, product, wh1
):
    response = move(client, gestionnaire_headers, type="TRANSFERT",
                    product_id=product.id, warehouse_id=wh1.id, quantity=1)

    assert response.status_code == 400
    assert "warehouse_dest_id" in response.get_json()["errors"]


def test_transfert_to_archived_warehouse_is_refused(
    client, gestionnaire_headers, product, wh1, wh2
):
    entree(client, gestionnaire_headers, product, wh1, 5)
    wh2.is_archived = True
    db.session.commit()

    response = transfert(client, gestionnaire_headers, product, wh1, wh2, 1)

    assert response.status_code == 404
    assert quantity(wh1, product) == 5


def test_destination_only_allowed_for_transfert(
    client, gestionnaire_headers, product, wh1, wh2
):
    response = move(client, gestionnaire_headers, type="ENTREE",
                    product_id=product.id, warehouse_id=wh1.id,
                    warehouse_dest_id=wh2.id, quantity=1)

    assert response.status_code == 400


# -------------------------------------------------------------- AJUSTEMENT

def test_ajustement_positive(client, gestionnaire_headers, product, wh1):
    entree(client, gestionnaire_headers, product, wh1, 10)

    response = ajustement(client, gestionnaire_headers, product, wh1, 3,
                          reason="Inventaire : 3 pièces retrouvées")

    assert response.status_code == 201
    assert quantity(wh1, product) == 13
    assert response.get_json()["movement"]["quantity"] == 3


def test_ajustement_negative(client, gestionnaire_headers, product, wh1):
    entree(client, gestionnaire_headers, product, wh1, 10)

    response = ajustement(client, gestionnaire_headers, product, wh1, -4,
                          reason="Casse constatée")

    assert response.status_code == 201
    assert quantity(wh1, product) == 6
    assert response.get_json()["movement"]["quantity"] == -4


def test_ajustement_requires_reason(
    client, gestionnaire_headers, product, wh1
):
    entree(client, gestionnaire_headers, product, wh1, 10)

    response = ajustement(client, gestionnaire_headers, product, wh1, 3)

    assert response.status_code == 400
    assert "reason" in response.get_json()["errors"]
    assert quantity(wh1, product) == 10
    assert movement_count() == 1


@pytest.mark.parametrize("reason", ["", "   ", None])
def test_ajustement_rejects_blank_reason(
    client, gestionnaire_headers, product, wh1, reason
):
    response = ajustement(client, gestionnaire_headers, product, wh1, 3,
                          reason=reason)

    assert response.status_code == 400
    assert "reason" in response.get_json()["errors"]


def test_ajustement_of_zero_is_refused(
    client, gestionnaire_headers, product, wh1
):
    response = ajustement(client, gestionnaire_headers, product, wh1, 0,
                          reason="Rien")

    assert response.status_code == 400
    assert "quantity" in response.get_json()["errors"]


def test_ajustement_cannot_make_stock_negative(
    client, gestionnaire_headers, product, wh1
):
    entree(client, gestionnaire_headers, product, wh1, 5)

    response = ajustement(client, gestionnaire_headers, product, wh1, -6,
                          reason="Erreur de comptage")

    assert response.status_code == 409
    assert quantity(wh1, product) == 5
    assert movement_count() == 1


# -------------------------------------------------------------- VALIDATION

@pytest.mark.parametrize("qty", [0, -1, -100])
@pytest.mark.parametrize("movement_type", ["ENTREE", "SORTIE"])
def test_quantity_must_be_positive(
    client, gestionnaire_headers, product, wh1, movement_type, qty
):
    response = move(client, gestionnaire_headers, type=movement_type,
                    product_id=product.id, warehouse_id=wh1.id, quantity=qty)

    assert response.status_code == 400
    assert "quantity" in response.get_json()["errors"]


@pytest.mark.parametrize("qty", [1.5, "10", None])
def test_quantity_must_be_an_integer(
    client, gestionnaire_headers, product, wh1, qty
):
    response = entree(client, gestionnaire_headers, product, wh1, qty)

    assert response.status_code == 400
    assert movement_count() == 0


def test_quantity_has_an_upper_bound(
    client, gestionnaire_headers, product, wh1
):
    response = entree(client, gestionnaire_headers, product, wh1, 10**9)

    assert response.status_code == 400


def test_unknown_type_is_refused(client, gestionnaire_headers, product, wh1):
    response = move(client, gestionnaire_headers, type="DESTRUCTION",
                    product_id=product.id, warehouse_id=wh1.id, quantity=1)

    assert response.status_code == 400
    assert "type" in response.get_json()["errors"]


def test_missing_fields(client, gestionnaire_headers):
    response = client.post(URL, json={}, headers=gestionnaire_headers)

    assert response.status_code == 400
    assert set(response.get_json()["errors"]) >= {
        "type", "product_id", "warehouse_id", "quantity"
    }


def test_post_without_body(client, gestionnaire_headers):
    response = client.post(URL, headers=gestionnaire_headers)

    assert response.status_code == 400


def test_unknown_product_is_refused(client, gestionnaire_headers, wh1):
    response = move(client, gestionnaire_headers, type="ENTREE",
                    product_id=9999, warehouse_id=wh1.id, quantity=1)

    assert response.status_code == 404
    assert movement_count() == 0


def test_archived_product_is_refused(
    client, gestionnaire_headers, product, wh1
):
    product.is_archived = True
    db.session.commit()

    response = entree(client, gestionnaire_headers, product, wh1, 1)

    assert response.status_code == 404


def test_unknown_warehouse_is_refused(client, gestionnaire_headers, product):
    response = move(client, gestionnaire_headers, type="ENTREE",
                    product_id=product.id, warehouse_id=9999, quantity=1)

    assert response.status_code == 404


def test_archived_warehouse_is_refused(
    client, gestionnaire_headers, product, wh1
):
    wh1.is_archived = True
    db.session.commit()

    response = entree(client, gestionnaire_headers, product, wh1, 1)

    assert response.status_code == 404


# ------------------------------------------------------------- TRANSACTION

def test_transaction_is_rolled_back_on_failure(
    app, admin, product, wh1, wh2, monkeypatch
):
    """
    Si une étape échoue après la mise à jour du stock source, le stock source
    est restauré et aucun mouvement n'est enregistré (tout ou rien).
    """
    db.session.add(WarehouseStock(
        warehouse_id=wh1.id, product_id=product.id, quantity=30
    ))
    db.session.commit()

    real_change_stock = movement_service._change_stock
    calls = []

    def failing_second_call(*args):
        calls.append(args)
        if len(calls) == 2:  # l'ajout dans l'entrepôt de destination
            raise RuntimeError("panne simulée")
        return real_change_stock(*args)

    monkeypatch.setattr(movement_service, "_change_stock", failing_second_call)

    data = {"type": "TRANSFERT", "product_id": product.id,
            "warehouse_id": wh1.id, "warehouse_dest_id": wh2.id,
            "quantity": 10}

    with pytest.raises(RuntimeError):
        movement_service.create_movement(data, admin)

    assert len(calls) == 2  # la 1re étape (retrait de la source) a bien eu lieu
    assert quantity(wh1, product) == 30  # ... mais elle est annulée
    assert quantity(wh2, product) is None
    assert movement_count() == 0


def test_database_rejects_zero_quantity_movement(app, admin, product, wh1):
    db.session.add(StockMovement(
        type="ENTREE", product_id=product.id, warehouse_id=wh1.id,
        quantity=0, user_id=admin.id
    ))

    with pytest.raises(Exception):
        db.session.commit()
    db.session.rollback()


# -------------------------------------------------------------------- ROLES

def test_movements_require_authentication(client, product, wh1):
    assert client.get(URL).status_code == 401
    assert client.post(URL, json={}).status_code == 401


def test_magasinier_can_do_entree_and_sortie(
    client, magasinier, magasinier_headers, product, wh1
):
    r1 = entree(client, magasinier_headers, product, wh1, 10)
    r2 = sortie(client, magasinier_headers, product, wh1, 4)

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert quantity(wh1, product) == 6
    assert r2.get_json()["movement"]["user_id"] == magasinier.id


def test_magasinier_cannot_transfer(
    client, gestionnaire_headers, magasinier_headers, product, wh1, wh2
):
    entree(client, gestionnaire_headers, product, wh1, 10)

    response = transfert(client, magasinier_headers, product, wh1, wh2, 5)

    assert response.status_code == 403
    assert quantity(wh1, product) == 10
    assert movement_count() == 1


def test_magasinier_cannot_adjust(
    client, gestionnaire_headers, magasinier_headers, product, wh1
):
    entree(client, gestionnaire_headers, product, wh1, 10)

    response = ajustement(client, magasinier_headers, product, wh1, 5,
                          reason="Test")

    assert response.status_code == 403
    assert quantity(wh1, product) == 10


def test_admin_can_do_every_type(
    client, admin_headers, product, wh1, wh2
):
    assert entree(client, admin_headers, product, wh1, 10).status_code == 201
    assert sortie(client, admin_headers, product, wh1, 1).status_code == 201
    assert transfert(client, admin_headers, product, wh1, wh2,
                     2).status_code == 201
    assert ajustement(client, admin_headers, product, wh1, 1,
                      reason="Inventaire").status_code == 201


def test_deactivated_user_cannot_move_stock(
    client, magasinier, magasinier_headers, product, wh1
):
    magasinier.is_active = False
    db.session.commit()

    response = entree(client, magasinier_headers, product, wh1, 1)

    assert response.status_code == 401
    assert movement_count() == 0


# --------------------------------------------------------------- HISTORIQUE

@pytest.fixture
def history(client, gestionnaire_headers, magasinier_headers, product,
            wh1, wh2):
    """4 mouvements variés, datés de jours différents."""
    entree(client, gestionnaire_headers, product, wh1, 50)
    sortie(client, magasinier_headers, product, wh1, 5, reason="Vente")
    transfert(client, gestionnaire_headers, product, wh1, wh2, 10)
    ajustement(client, gestionnaire_headers, product, wh2, -1,
               reason="Casse")

    dates = ["2026-11-01 09:00", "2026-11-02 10:00",
             "2026-11-03 11:00", "2026-11-04 23:30"]
    for movement, value in zip(
        StockMovement.query.order_by(StockMovement.id).all(), dates
    ):
        movement.created_at = datetime.strptime(value, "%Y-%m-%d %H:%M")
    db.session.commit()


def test_history_lists_all_newest_first(client, gestionnaire_headers, history):
    response = client.get(URL, headers=gestionnaire_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert [m["type"] for m in data] == [
        "AJUSTEMENT", "TRANSFERT", "SORTIE", "ENTREE"
    ]


def test_history_contains_readable_names(
    client, gestionnaire_headers, history
):
    first = client.get(URL, headers=gestionnaire_headers).get_json()[-1]

    assert first["product_name"] == "Clou 50mm"
    assert first["product_sku"] == "MV-001"
    assert first["warehouse_name"] == "Entrepôt A"
    assert first["user_name"] == "Test gestionnaire"


@pytest.mark.parametrize("movement_type, expected", [
    ("ENTREE", 1), ("SORTIE", 1), ("TRANSFERT", 1), ("AJUSTEMENT", 1)
])
def test_history_filter_by_type(
    client, gestionnaire_headers, history, movement_type, expected
):
    response = client.get(f"{URL}?type={movement_type}",
                          headers=gestionnaire_headers)

    data = response.get_json()
    assert len(data) == expected
    assert all(m["type"] == movement_type for m in data)


def test_history_filter_by_warehouse_includes_transfer_destination(
    client, gestionnaire_headers, history, wh2
):
    # L'entrepôt B apparaît comme destination du transfert + ajustement
    data = client.get(f"{URL}?warehouse_id={wh2.id}",
                      headers=gestionnaire_headers).get_json()

    assert {m["type"] for m in data} == {"TRANSFERT", "AJUSTEMENT"}


def test_history_filter_by_product(
    client, gestionnaire_headers, history, product
):
    other = Product(sku="MV-002", name="Vis", unit_price=1, minimum_stock=0)
    db.session.add(other)
    db.session.commit()

    assert len(client.get(f"{URL}?product_id={product.id}",
                          headers=gestionnaire_headers).get_json()) == 4
    assert client.get(f"{URL}?product_id={other.id}",
                      headers=gestionnaire_headers).get_json() == []


def test_history_filter_by_user(
    client, gestionnaire_headers, magasinier, history
):
    data = client.get(f"{URL}?user_id={magasinier.id}",
                      headers=gestionnaire_headers).get_json()

    assert [m["type"] for m in data] == ["SORTIE"]


def test_history_filter_by_dates_is_inclusive(
    client, gestionnaire_headers, history
):
    data = client.get(f"{URL}?date_from=2026-11-02&date_to=2026-11-03",
                      headers=gestionnaire_headers).get_json()

    assert [m["type"] for m in data] == ["TRANSFERT", "SORTIE"]


def test_history_date_to_includes_the_whole_day(
    client, gestionnaire_headers, history
):
    # Le mouvement du 4 novembre est à 23h30 : il doit être inclus
    data = client.get(f"{URL}?date_to=2026-11-04",
                      headers=gestionnaire_headers).get_json()

    assert len(data) == 4


def test_history_filters_can_be_combined(
    client, gestionnaire_headers, history, wh1
):
    data = client.get(
        f"{URL}?type=SORTIE&warehouse_id={wh1.id}&date_from=2026-11-02",
        headers=gestionnaire_headers
    ).get_json()

    assert [m["type"] for m in data] == ["SORTIE"]


@pytest.mark.parametrize("query", [
    "type=INCONNU", "date_from=pas-une-date", "product_id=abc",
    "page=0", "per_page=1000",
])
def test_history_invalid_filters(client, gestionnaire_headers, query):
    response = client.get(f"{URL}?{query}", headers=gestionnaire_headers)

    assert response.status_code == 400
    assert "errors" in response.get_json()


def test_history_pagination(client, gestionnaire_headers, history):
    response = client.get(f"{URL}?page=2&per_page=3",
                          headers=gestionnaire_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["total"] == 4
    assert data["pages"] == 2
    assert data["page"] == 2
    assert len(data["items"]) == 1
    assert data["items"][0]["type"] == "ENTREE"  # le plus ancien


def test_history_readable_by_every_role(
    client, admin_headers, gestionnaire_headers, magasinier_headers
):
    for headers in (admin_headers, gestionnaire_headers, magasinier_headers):
        assert client.get(URL, headers=headers).status_code == 200


def test_movement_detail(client, gestionnaire_headers, product, wh1):
    movement_id = entree(client, gestionnaire_headers, product,
                         wh1, 7).get_json()["movement"]["id"]

    ok = client.get(f"{URL}{movement_id}", headers=gestionnaire_headers)
    missing = client.get(f"{URL}9999", headers=gestionnaire_headers)

    assert ok.status_code == 200
    assert ok.get_json()["quantity"] == 7
    assert missing.status_code == 404


def test_movements_are_never_modifiable_through_the_api(
    client, gestionnaire_headers, product, wh1
):
    """L'historique est en lecture seule : ni modification ni suppression."""
    movement_id = entree(client, gestionnaire_headers, product,
                         wh1, 7).get_json()["movement"]["id"]

    put = client.put(f"{URL}{movement_id}", json={"quantity": 1},
                     headers=gestionnaire_headers)
    delete = client.delete(f"{URL}{movement_id}",
                           headers=gestionnaire_headers)

    assert put.status_code == 405
    assert delete.status_code == 405
    assert quantity(wh1, product) == 7
