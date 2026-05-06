from django.db.models import Count, Sum

from albaranes.models import Albara, Client, Producte, StockMagatzem
from aurora_agent.services.evidence import evidence_item
from aurora_agent.services.formatter import money

from .analytics import get_sales_statistics, get_top_products
from .base import require_authenticated, tool_response
from .customers import get_top_customers
from .delivery_notes import analyze_stock_blockers, prioritize_delivery_notes
from .stock import list_low_stock_products


def get_operational_summary(user, arguments=None, context=None):
    denied = require_authenticated(user)
    if denied:
        return denied
    status_counts = {row["estat"]: row["total"] for row in Albara.objects.values("estat").annotate(total=Count("id"))}
    delivered = Albara.objects.filter(estat=Albara.Estat.ENTREGAT).aggregate(total=Sum("total"))
    low_stock = StockMagatzem.objects.filter(producte__actiu=True, quantitat__lt=10).count()
    summary = {
        "pending_delivery_notes": status_counts.get(Albara.Estat.PENDENT, 0),
        "in_preparation": status_counts.get(Albara.Estat.EN_PREPARACIO, 0),
        "delivered": status_counts.get(Albara.Estat.ENTREGAT, 0),
        "active_products": Producte.objects.filter(actiu=True).count(),
        "active_customers": Client.objects.filter(actiu=True).count(),
        "low_stock_products": low_stock,
        "delivered_sales": money(delivered["total"]),
    }
    return tool_response(
        "ok",
        summary=summary,
        evidence=[
            evidence_item("metric", "Resumen operativo", "/", summary),
            evidence_item("metric", "Stock bajo", "/stock/", {"count": low_stock}),
        ],
    )


def count_customers(user, arguments=None, context=None):
    denied = require_authenticated(user)
    if denied:
        return denied
    count = Client.objects.filter(actiu=True).count()
    return tool_response(
        "ok",
        summary={"active_customers": count},
        evidence=[evidence_item("metric", "Clientes activos", "/clients/", {"active_customers": count})],
    )


def count_products(user, arguments=None, context=None):
    denied = require_authenticated(user)
    if denied:
        return denied
    count = Producte.objects.filter(actiu=True).count()
    return tool_response(
        "ok",
        summary={"active_products": count},
        evidence=[evidence_item("metric", "Productos activos", "/cataleg/", {"active_products": count})],
    )


def count_delivery_notes(user, arguments=None, context=None):
    denied = require_authenticated(user)
    if denied:
        return denied
    count = Albara.objects.count()
    status_counts = {row["estat"]: row["total"] for row in Albara.objects.values("estat").annotate(total=Count("id"))}
    return tool_response(
        "ok",
        summary={"delivery_notes": count, "status_counts": status_counts},
        evidence=[evidence_item("metric", "Albaranes registrados", "/albarans/", {"delivery_notes": count})],
    )


def count_low_stock_products(user, arguments=None, context=None):
    denied = require_authenticated(user)
    if denied:
        return denied
    count = StockMagatzem.objects.filter(producte__actiu=True, quantitat__lt=10).count()
    return tool_response(
        "ok",
        summary={"low_stock_products": count, "threshold": 10},
        evidence=[evidence_item("metric", "Productos con stock bajo", "/stock/", {"low_stock_products": count})],
    )


def summarize_daily_operations(user, arguments=None, context=None):
    denied = require_authenticated(user)
    if denied:
        return denied
    summary = get_operational_summary(user, arguments, context)
    priority = prioritize_delivery_notes(user, {"limit": 8}, context)
    blockers = analyze_stock_blockers(user, {"limit": 8}, context)
    return tool_response(
        "ok",
        summary={
            "operation": summary.get("summary", {}),
            "priority_count": priority.get("summary", {}).get("count", 0),
            "blocked_delivery_notes": blockers.get("summary", {}).get("blocked_delivery_notes", 0),
        },
        records=[
            {"section": "summary", "data": summary},
            {"section": "priorities", "data": priority},
            {"section": "blockers", "data": blockers},
        ],
        evidence=(summary.get("evidence", []) + priority.get("evidence", []) + blockers.get("evidence", []))[:20],
    )
