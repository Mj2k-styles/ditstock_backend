"""Tableau de bord : mouvements du jour, évolution sur 30 jours, top 10."""
from datetime import datetime, timedelta, timezone

import pytest

from app import db
from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.models.warehouse import Warehouse

pytestmark = pytest.mark.usefixtures("as_gestionnaire")

URL = "/api/dashboard/stats"


def utc_now():
    # created_at est stocké en UTC, sans fuseau
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture
def base(app, gestionnaire):
    warehouse = Warehouse(name="Entrepôt A")
    db.session.add(warehouse)
    db.session.commit()
    return warehouse, gestionnaire


def add_product(sku, name):
    product = Product(sku=sku, name=name, unit_price=1, minimum_stock=0)
    db.session.add(product)
    db.session.commit()
    return product


def add_movement(base, product, movement_type="ENTREE", quantity=1,
                 days_ago=0):
    warehouse, user = base
    db.session.add(StockMovement(
        type=movement_type, product_id=product.id,
        warehouse_id=warehouse.id, quantity=quantity, user_id=user.id,
        created_at=utc_now() - timedelta(days=days_ago)
    ))
    db.session.commit()


def test_dashboard_without_movements(client):
    data = client.get(URL).get_json()

    assert data["movements_today"] == 0
    assert data["top_products"] == []
    assert len(data["movements_30d"]) == 30
    assert all(day["count"] == 0 for day in data["movements_30d"])


def test_existing_indicators_are_unchanged(client, base):
    data = client.get(URL).get_json()

    assert {"total_products", "stock_value", "total_alerts"} <= set(data)


def test_movements_today_counts_only_today(client, base):
    product = add_product("D-1", "Clou")
    add_movement(base, product, days_ago=0)
    add_movement(base, product, days_ago=0)
    add_movement(base, product, days_ago=1)

    assert client.get(URL).get_json()["movements_today"] == 2


def test_movements_30d_has_one_entry_per_day_ending_today(client, base):
    product = add_product("D-1", "Clou")
    add_movement(base, product, days_ago=0)
    add_movement(base, product, days_ago=0)
    add_movement(base, product, days_ago=3)

    days = client.get(URL).get_json()["movements_30d"]
    today = utc_now().date()

    assert len(days) == 30
    assert days[-1] == {"date": today.isoformat(), "count": 2}
    assert days[0]["date"] == (today - timedelta(days=29)).isoformat()
    by_date = {d["date"]: d["count"] for d in days}
    assert by_date[(today - timedelta(days=3)).isoformat()] == 1
    assert sum(by_date.values()) == 3
    # dates consécutives, sans trou
    assert [d["date"] for d in days] == sorted(by_date)


def test_movements_older_than_30_days_are_ignored(client, base):
    product = add_product("D-1", "Clou")
    add_movement(base, product, days_ago=29)  # dernier jour inclus
    add_movement(base, product, days_ago=30)  # trop ancien

    days = client.get(URL).get_json()["movements_30d"]

    assert sum(d["count"] for d in days) == 1


def test_top_products_ranks_sorties_by_quantity(client, base):
    clou = add_product("D-1", "Clou")
    vis = add_product("D-2", "Vis")
    ecrou = add_product("D-3", "Écrou")
    add_movement(base, clou, "SORTIE", 5)
    add_movement(base, clou, "SORTIE", 10)
    add_movement(base, vis, "SORTIE", 20)
    add_movement(base, ecrou, "SORTIE", 1)

    top = client.get(URL).get_json()["top_products"]

    assert [(p["name"], p["quantity"]) for p in top] == [
        ("Vis", 20), ("Clou", 15), ("Écrou", 1)
    ]


def test_top_products_counts_only_sorties(client, base):
    product = add_product("D-1", "Clou")
    add_movement(base, product, "ENTREE", 100)
    add_movement(base, product, "TRANSFERT", 50)
    add_movement(base, product, "AJUSTEMENT", -5)
    add_movement(base, product, "SORTIE", 7)

    top = client.get(URL).get_json()["top_products"]

    assert [(p["name"], p["quantity"]) for p in top] == [("Clou", 7)]


def test_top_products_ignores_old_sorties(client, base):
    product = add_product("D-1", "Clou")
    add_movement(base, product, "SORTIE", 7, days_ago=45)

    assert client.get(URL).get_json()["top_products"] == []


def test_top_products_is_limited_to_10(client, base):
    for i in range(12):
        product = add_product(f"D-{i}", f"Produit {i}")
        add_movement(base, product, "SORTIE", i + 1)

    top = client.get(URL).get_json()["top_products"]

    assert len(top) == 10
    assert top[0]["quantity"] == 12
    assert top[-1]["quantity"] == 3
