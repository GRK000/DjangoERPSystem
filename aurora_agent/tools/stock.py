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
    limit = max_results((arguments or {}).get("limit"))
    rows = []
    for product in Producte.objects.filter(actiu=True).select_related("categoria").prefetch_related("stocks__magatzem").order_by("codi"):
        total = product.get_stock_total()
        if total >= 10:
            continue
        stocks = list(product.stocks.all())
        rows.append({
            "product_id": product.id,
            "sku": product.codi,
            "product": product.nom,
            "category": product.categoria.nom,
            "quantity": total,
            "warehouse": ", ".join(stock.magatzem.nom for stock in stocks[:2]),
            "location": ", ".join(stock.ubicacio for stock in stocks[:2]),
            "low_stock": True,
            "url": "/stock/",
        })
        if len(rows) >= limit:
            break
    return tool_response(
        "ok" if rows else "empty",
        summary={"count": len(rows), "threshold": 10},
        records=rows,
        evidence=[evidence_item("stock", f"{row['sku']} {row['warehouse']}", "/stock/", {"quantity": row["quantity"]}) for row in rows],
        message="" if rows else "No hay productos por debajo del umbral de stock bajo.",
    )


def list_out_of_stock_products(user, arguments=None, context=None):
    denied = require_authenticated(user)
    if denied:
        return denied
    limit = max_results((arguments or {}).get("limit"))
    rows = []
    for product in Producte.objects.filter(actiu=True).select_related("categoria").prefetch_related("stocks__magatzem").order_by("codi"):
        if product.get_stock_total() != 0:
            continue
        stocks = list(product.stocks.all())
        rows.append({
            "product_id": product.id,
            "sku": product.codi,
            "product": product.nom,
            "category": product.categoria.nom,
            "quantity": 0,
            "warehouse": ", ".join(stock.magatzem.nom for stock in stocks[:2]) or "Sin almacen",
            "location": ", ".join(stock.ubicacio for stock in stocks[:2]),
            "low_stock": True,
            "url": "/stock/",
        })
        if len(rows) >= limit:
            break
    return tool_response(
        "ok" if rows else "empty",
        summary={"count": len(rows), "stock_filter": "out_of_stock"},
        records=rows,
        evidence=[evidence_item("stock", f"{row['sku']} {row['warehouse']}", "/stock/", {"quantity": row["quantity"]}) for row in rows],
        message="" if rows else "No hay productos sin stock.",
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
