"""
Règles de gestion des mouvements de stock.

Tout se passe dans UNE transaction : le mouvement et les mises à jour
de warehouse_stocks sont validés ensemble (commit) ou annulés ensemble
(rollback). Le stock n'est jamais modifié ailleurs que par ce module.
"""
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from app import db
from app.constants import (
    MANAGER_ONLY_MOVEMENT_TYPES,
    MOVEMENT_AJUSTEMENT,
    MOVEMENT_ENTREE,
    MOVEMENT_SORTIE,
    MOVEMENT_TRANSFERT,
    ROLE_ADMIN,
    ROLE_GESTIONNAIRE,
)
from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.models.warehouse import Warehouse
from app.models.warehouse_stock import WarehouseStock


class MovementError(Exception):
    """Erreur de règle de gestion, avec le code HTTP à renvoyer."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def _active_product(product_id):
    product = db.session.get(Product, product_id)
    if product is None or product.is_archived:
        raise MovementError("Produit introuvable.", 404)
    return product


def _active_warehouse(warehouse_id, label="Entrepôt"):
    warehouse = db.session.get(Warehouse, warehouse_id)
    if warehouse is None or warehouse.is_archived:
        raise MovementError(f"{label} introuvable.", 404)
    return warehouse


def _ensure_stock_row(warehouse_id, product_id):
    """Crée la ligne de stock (quantité 0) si elle n'existe pas encore."""
    exists = WarehouseStock.query.filter_by(
        warehouse_id=warehouse_id, product_id=product_id
    ).first()
    if exists:
        return

    try:
        # SAVEPOINT : si une requête concurrente crée la même ligne en même
        # temps, seule cette insertion est annulée, pas toute la transaction.
        with db.session.begin_nested():
            db.session.add(WarehouseStock(
                warehouse_id=warehouse_id, product_id=product_id, quantity=0
            ))
    except IntegrityError:
        pass


def _change_stock(warehouse_id, product_id, delta):
    """
    Ajoute `delta` (positif ou négatif) au stock, de façon atomique.

    Le UPDATE ne s'applique que si le stock reste >= 0 : deux sorties
    simultanées ne peuvent donc pas rendre le stock négatif.
    Retourne False si le stock est insuffisant.
    """
    if delta > 0:
        _ensure_stock_row(warehouse_id, product_id)

    condition = [
        WarehouseStock.warehouse_id == warehouse_id,
        WarehouseStock.product_id == product_id,
    ]
    if delta < 0:
        condition.append(WarehouseStock.quantity >= -delta)

    result = db.session.execute(
        update(WarehouseStock)
        .where(*condition)
        .values(quantity=WarehouseStock.quantity + delta)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1


def _insufficient(warehouse, product):
    current = _current_quantity(warehouse.id, product.id)
    return MovementError(
        f"Stock insuffisant pour « {product.name} » dans "
        f"« {warehouse.name} » (disponible : {current}).",
        409
    )


def _current_quantity(warehouse_id, product_id):
    stock = WarehouseStock.query.filter_by(
        warehouse_id=warehouse_id, product_id=product_id
    ).first()
    return stock.quantity if stock else 0


def check_permission(movement_type, role):
    """Transferts et ajustements : gestionnaire ou admin uniquement."""
    if movement_type in MANAGER_ONLY_MOVEMENT_TYPES and role not in (
        ROLE_ADMIN, ROLE_GESTIONNAIRE
    ):
        raise MovementError(
            "Accès refusé : seuls le gestionnaire et l'administrateur "
            "peuvent enregistrer cette opération.",
            403
        )


def create_movement(data, user):
    """
    Valide et enregistre un mouvement. `data` vient de MovementCreateSchema.

    Retourne (mouvement, [lignes de stock modifiées]).
    Lève MovementError (et annule tout) si une règle n'est pas respectée.
    """
    movement_type = data["type"]
    quantity = data["quantity"]

    check_permission(movement_type, user.role)

    try:
        product = _active_product(data["product_id"])
        warehouse = _active_warehouse(data["warehouse_id"])
        touched = [warehouse.id]

        if movement_type == MOVEMENT_ENTREE:
            _change_stock(warehouse.id, product.id, quantity)

        elif movement_type == MOVEMENT_SORTIE:
            if not _change_stock(warehouse.id, product.id, -quantity):
                raise _insufficient(warehouse, product)

        elif movement_type == MOVEMENT_TRANSFERT:
            dest = _active_warehouse(
                data["warehouse_dest_id"], "Entrepôt de destination"
            )
            if dest.id == warehouse.id:
                raise MovementError(
                    "L'entrepôt de destination doit être différent "
                    "de l'entrepôt source.", 400
                )
            if not _change_stock(warehouse.id, product.id, -quantity):
                raise _insufficient(warehouse, product)
            _change_stock(dest.id, product.id, quantity)
            touched.append(dest.id)

        elif movement_type == MOVEMENT_AJUSTEMENT:
            # quantity = écart constaté (positif ou négatif)
            if not _change_stock(warehouse.id, product.id, quantity):
                raise _insufficient(warehouse, product)

        movement = StockMovement(
            type=movement_type,
            product_id=product.id,
            warehouse_id=warehouse.id,
            warehouse_dest_id=data.get("warehouse_dest_id")
            if movement_type == MOVEMENT_TRANSFERT else None,
            quantity=quantity,
            reason=data.get("reason"),
            reference=data.get("reference"),
            user_id=user.id,
        )
        db.session.add(movement)
        db.session.commit()

    except Exception:
        # Aucune écriture partielle : le mouvement ET le stock sont annulés
        db.session.rollback()
        raise

    stocks = [
        WarehouseStock.query.filter_by(
            warehouse_id=wid, product_id=product.id
        ).one()
        for wid in touched
    ]
    return movement, stocks
