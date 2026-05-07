from albaranes.models import Producte
from aurora_agent.services.evidence import evidence_item
from aurora_agent.services.formatter import money

from .base import max_results, require_authenticated, tool_response


def serialize_product(product):
    return {
        "id": product.id,
        "sku": product.codi,
        "name": product.nom,
        "category": product.categoria.nom,
        "active": product.actiu,
        "unit": product.unitat_mesura,
        "price": money(product.preu_unitari),
        "stock_total": product.get_stock_total(),
        "url": "/cataleg/",
    }


def list_products(user, arguments=None, context=None):
    denied = require_authenticated(user)
    if denied:
        return denied
    arguments = arguments or {}
    status = arguments.get("status") or "active"
    stock_filter = arguments.get("stock_filter") or ""
    qs = Producte.objects.select_related("categoria").prefetch_related("stocks")
    if status == "inactive":
        qs = qs.filter(actiu=False)
    elif status != "all":
        qs = qs.filter(actiu=True)
    if arguments.get("query"):
        qs = qs.filter(nom__icontains=arguments["query"])
    if arguments.get("sku"):
        qs = qs.filter(codi__iexact=arguments["sku"])
    rows = []
    for product in qs.order_by("codi"):
        stock_total = product.get_stock_total()
        if stock_filter == "low_stock" and not (0 < stock_total < 10):
            continue
        if stock_filter == "out_of_stock" and stock_total != 0:
            continue
        rows.append(serialize_product(product))
        if len(rows) >= max_results(arguments.get("limit")):
            break
    return tool_response(
        "ok" if rows else "empty",
        summary={"count": len(rows), "status": status, "stock_filter": stock_filter},
        records=rows,
        evidence=[evidence_item("product", f"{row['sku']} {row['name']}", row["url"], {"stock_total": row["stock_total"]}) for row in rows],
        message="" if rows else "No hay productos para estos filtros.",
    )
