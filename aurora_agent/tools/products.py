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
    qs = Producte.objects.filter(actiu=True).select_related("categoria").prefetch_related("stocks")
    if arguments.get("query"):
        qs = qs.filter(nom__icontains=arguments["query"])
    if arguments.get("sku"):
        qs = qs.filter(codi__iexact=arguments["sku"])
    rows = [serialize_product(product) for product in qs.order_by("codi")[: max_results(arguments.get("limit"))]]
    return tool_response(
        "ok" if rows else "empty",
        summary={"count": len(rows)},
        records=rows,
        evidence=[evidence_item("product", f"{row['sku']} {row['name']}", row["url"], {"stock_total": row["stock_total"]}) for row in rows],
    )
