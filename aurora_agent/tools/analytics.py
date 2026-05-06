from django.db.models import Count, Sum

from albaranes.models import Albara, LiniaAlbara
from aurora_agent.services.evidence import evidence_item
from aurora_agent.services.formatter import money

from .base import max_results, require_authenticated, tool_response
from .delivery_notes import get_top_products_from_delivered


def get_sales_statistics(user, arguments=None, context=None):
    denied = require_authenticated(user)
    if denied:
        return denied
    delivered = Albara.objects.filter(estat=Albara.Estat.ENTREGAT)
    totals = delivered.aggregate(total=Sum("total"), total_base=Sum("base_imposable"), total_iva=Sum("total_iva"))
    by_status = {row["estat"]: row["total"] for row in Albara.objects.values("estat").annotate(total=Count("id"))}
    return tool_response(
        "ok",
        summary={
            "delivered_sales": money(totals["total"]),
            "base": money(totals["total_base"]),
            "vat": money(totals["total_iva"]),
            "status_counts": by_status,
        },
        evidence=[evidence_item("metric", "Ventas entregadas", "/estadistiques/", {"total": money(totals["total"])})],
    )


def get_top_products(user, arguments=None, context=None):
    denied = require_authenticated(user)
    if denied:
        return denied
    rows = [
        {
            "product": row["nom_producte"],
            "total_quantity": row["total_quantity"],
            "total_sales": money(row["total_sales"]),
        }
        for row in get_top_products_from_delivered(max_results((arguments or {}).get("limit")))
    ]
    return tool_response(
        "ok" if rows else "empty",
        summary={"count": len(rows)},
        records=rows,
        evidence=[evidence_item("product", row["product"], "/estadistiques/", {"quantity": row["total_quantity"]}) for row in rows],
        message="" if rows else "No hay productos vendidos en albaranes entregados.",
    )
