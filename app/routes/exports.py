from io import BytesIO
from app import db
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
import csv
import io

from flask import Response
from flask_restx import Namespace, Resource

from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.warehouse_stock import WarehouseStock

exports_ns = Namespace(
    "exports",
    description="Exportation des données du stock"
)


@exports_ns.route("/stock/csv")
class StockCSVExport(Resource):

    def get(self):
        stocks = WarehouseStock.query.join(
            Product,
            Product.id == WarehouseStock.product_id
        ).join(
            Warehouse,
            Warehouse.id == WarehouseStock.warehouse_id
        ).filter(
            Product.is_archived == False,
            Warehouse.is_archived == False
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
class StockPDFExport(Resource):

    def get(self):
        stocks = WarehouseStock.query.join(
            Product,
            Product.id == WarehouseStock.product_id
        ).join(
            Warehouse,
            Warehouse.id == WarehouseStock.warehouse_id
        ).filter(
            Product.is_archived == False,
            Warehouse.is_archived == False
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

    
