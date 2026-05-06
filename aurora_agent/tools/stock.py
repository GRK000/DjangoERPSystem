from albaranes.models import MovimentStock, Producte, StockMagatzem
from aurora_agent.services.evidence import evidence_item
from aurora_agent.services.formatter import datetime

from .base import max_results, require_authenticated, tool_response


def serialize_stock(stock):
    return {
        "id": stock.id,
        "product_id": stock.producte_id,
        "sku": stock.producte.codi,
        "product": stock.producte.nom,
        "category": stock.producte.categoria.nom,
        "warehouse": stock.magatzem.nom,
        "quantity": stock.quantitat,
        "location": stock.ubicacio,
        "low_stock": stock.is_stock_baix(),
        "last_entry": stock.data_ultima_entrada.isoformat() if stock.data_ultima_entrada else None,
    }


def list_low_stock_products(user, arguments=None, context=None):
    denied = require_authenticated(user)
    if denied:
        return denied
    qs = StockMagatzem.objects.select_related("producte", "producte__categoria", "magatzem").filter(producte__actiu=True, quantitat__lt=10).order_by("quantitat")
    limit = max_results((arguments or {}).get("limit"))
    rows = [serialize_stock(stock) for stock in qs[:limit]]
    return tool_response(
        "ok" if rows else "empty",
        summary={"count": len(rows), "threshold": 10},
        records=rows,
        evidence=[evidence_item("stock", f"{row['sku']} {row['warehouse']}", "/stock/", {"quantity": row["quantity"]}) for row in rows],
        message="" if rows else "No hay productos por debajo del umbral de stock bajo.",
    )


def get_product_movements(user, arguments=None, context=None):
    denied = require_authenticated(user)
    if denied:
        return denied
    arguments = arguments or {}
    qs = MovimentStock.objects.select_related("producte", "magatzem", "albara", "usuari").order_by("-data")
    if arguments.get("product_id"):
        qs = qs.filter(producte_id=arguments["product_id"])
    elif arguments.get("sku"):
        qs = qs.filter(producte__codi__iexact=arguments["sku"])
    elif arguments.get("query"):
        qs = qs.filter(producte__nom__icontains=arguments["query"])
    else:
        return tool_response("not_available", message="Indica product_id, sku o query para consultar movimientos.")
    rows = []
    for movement in qs[: max_results(arguments.get("limit"))]:
        rows.append({
            "id": movement.id,
            "product": movement.producte.nom,
            "sku": movement.producte.codi,
            "warehouse": movement.magatzem.nom,
            "type": movement.tipus,
            "quantity": movement.quantitat,
            "date": datetime(movement.data),
            "delivery_note": movement.albara.numero_albara if movement.albara else "",
            "user": movement.usuari.username if movement.usuari else "",
            "notes": movement.observacions or "",
        })
    return tool_response(
        "ok" if rows else "empty",
        summary={"count": len(rows)},
        records=rows,
        evidence=[evidence_item("movement", f"{row['type']} {row['sku']}", "/stock/", {"quantity": row["quantity"]}) for row in rows],
    )


def stock_by_product(product_id):
    return list(StockMagatzem.objects.filter(producte_id=product_id).select_related("magatzem"))
