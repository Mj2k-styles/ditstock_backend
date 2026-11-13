from io import BytesIO
from app import db
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from app.models.stock_movement import StockMovement
import csv
import io

from flask import Response
from flask_restx import Namespace, Resource

from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.warehouse_stock import WarehouseStock
from app.constants import ROLE_GESTIONNAIRE
from app.utils.decorators import roles_required

exports_ns = Namespace(
    "exports",
    description="Exportation des données du stock"
)


@exports_ns.route("/stock/csv")
@exports_ns.doc(security="Bearer")
class StockCSVExport(Resource):

    @roles_required(ROLE_GESTIONNAIRE)
    def get(self):
        stocks = WarehouseStock.query.join(
            Product,
            Product.id == WarehouseStock.product_id
        ).join(
            Warehouse,
            Warehouse.id == WarehouseStock.warehouse_id
        ).filter(
            Product.is_archived.is_(False),
            Warehouse.is_archived.is_(False)
        ).all()

        output = io.StringIO(newline="")
        writer = csv.writer(output, delimiter=";")

        writer.writerow([
            "SKU",
            "Produit",
            "Entrepot",
            "Quantite",
            "Seuil minimum",
            "Prix unitaire",
            "Valeur du stock"
        ])
        for stock in stocks:
            product = db.session.get(Product, stock.product_id)
            warehouse = db.session.get(Warehouse, stock.warehouse_id)

            writer.writerow([
                product.sku,
                product.name,
                warehouse.name,
                stock.quantity,
                product.minimum_stock,
                product.unit_price,
                stock.quantity * product.unit_price
            ])
        csv_content = "\ufeff" + output.getvalue()

        return Response(
            csv_content,
            mimetype="text/csv; charset=utf-8",
            headers={
                "Content-Disposition":
                    "attachment; filename=etat_du_stock.csv"
            }
        )


@exports_ns.route("/stock/pdf")
@exports_ns.doc(security="Bearer")
class StockPDFExport(Resource):

    @roles_required(ROLE_GESTIONNAIRE)
    def get(self):
        stocks = WarehouseStock.query.join(
            Product,
            Product.id == WarehouseStock.product_id
        ).join(
            Warehouse,
            Warehouse.id == WarehouseStock.warehouse_id
        ).filter(
            Product.is_archived.is_(False),
            Warehouse.is_archived.is_(False)
        ).all()

        buffer = BytesIO()

        document = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            title="Etat du stock"
        )

        styles = getSampleStyleSheet()
        elements = []

        elements.append(
            Paragraph("ETAT DU STOCK", styles["Title"])
        )
        elements.append(Spacer(1, 20))

        data = [[
            "SKU",
            "Produit",
            "Entrepot",
            "Quantite",
            "Seuil",
            "Prix unitaire",
            "Valeur"
        ]]

        for stock in stocks:
            product = db.session.get(Product, stock.product_id)
            warehouse = db.session.get(Warehouse, stock.warehouse_id)

            data.append([
                product.sku,
                product.name,
                warehouse.name,
                stock.quantity,
                product.minimum_stock,
                str(product.unit_price),
                str(stock.quantity * product.unit_price)
            ])

        table = Table(data, repeatRows=1)

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (3, 1), (-1, -1), "CENTER"),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.lightgrey])
        ]))

        elements.append(table)
        document.build(elements)

        buffer.seek(0)

        return Response(
            buffer.getvalue(),
            mimetype="application/pdf",
            headers={
                "Content-Disposition":
                    "attachment; filename=etat_du_stock.pdf"
            }
        )


@exports_ns.route("/movements/csv")
@exports_ns.doc(security="Bearer")
class MovementCSVExport(Resource):

    @roles_required(ROLE_GESTIONNAIRE)
    def get(self):
        movements = StockMovement.query.order_by(
            StockMovement.created_at.desc()
        ).all()

        output = io.StringIO(newline="")
        writer = csv.writer(output, delimiter=";")

        writer.writerow([
            "ID",
            "Type",
            "SKU",
            "Produit",
            "Entrepot source",
            "Entrepot destination",
            "Quantite",
            "Motif",
            "Reference",
            "Date"
        ])

        for movement in movements:
            writer.writerow([
                movement.id,
                movement.type,
                movement.product.sku,
                movement.product.name,
                movement.warehouse.name,
                movement.warehouse_dest.name
                if movement.warehouse_dest else "",
                movement.quantity,
                movement.reason or "",
                movement.reference or "",
                movement.created_at.strftime("%d/%m/%Y %H:%M:%S")
            ])

        csv_content = "\ufeff" + output.getvalue()

        return Response(
            csv_content,
            mimetype="text/csv; charset=utf-8",
            headers={
                "Content-Disposition":
                    "attachment; filename=historique_mouvements.csv"
            }
        )


@exports_ns.route("/movements/pdf")
@exports_ns.doc(security="Bearer")
class MovementPDFExport(Resource):

    @roles_required(ROLE_GESTIONNAIRE)
    def get(self):
        movements = StockMovement.query.order_by(
            StockMovement.created_at.desc()
        ).all()

        buffer = BytesIO()

        document = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            title="Historique des mouvements"
        )

        styles = getSampleStyleSheet()
        elements = []

        elements.append(
            Paragraph("HISTORIQUE DES MOUVEMENTS", styles["Title"])
        )
        elements.append(Spacer(1, 20))

        data = [[
            "ID",
            "Type",
            "SKU",
            "Produit",
            "Entrepot source",
            "Entrepot destination",
            "Quantite",
            "Motif",
            "Date"
        ]]

        for movement in movements:
            data.append([
                movement.id,
                movement.type,
                movement.product.sku,
                movement.product.name,
                movement.warehouse.name,
                movement.warehouse_dest.name
                if movement.warehouse_dest else "-",
                movement.quantity,
                movement.reason or "-",
                movement.created_at.strftime("%d/%m/%Y %H:%M")
            ])

        table = Table(data, repeatRows=1)

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.lightgrey])
        ]))

        elements.append(table)
        document.build(elements)

        buffer.seek(0)

        return Response(
            buffer.getvalue(),
            mimetype="application/pdf",
            headers={
                "Content-Disposition":
                    "attachment; filename=historique_mouvements.pdf"
            }
        )
