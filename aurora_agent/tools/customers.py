from django.db.models import Count, Sum

from albaranes.models import Albara, Client
from aurora_agent.services.evidence import evidence_item
from aurora_agent.services.formatter import money

from .base import max_results, require_authenticated, tool_response


def get_top_customers(user, arguments=None, context=None):
    denied = require_authenticated(user)
    if denied:
        return denied
    rows = []
    qs = Client.objects.filter(albarans__estat=Albara.Estat.ENTREGAT).annotate(
        total_sales=Sum("albarans__total"),
        delivery_notes=Count("albarans"),
    ).order_by("-total_sales")[: max_results((arguments or {}).get("limit"))]
    for client in qs:
        rows.append({
            "id": client.id,
            "code": client.codi_client,
            "name": client.nom_comercial,
            "delivery_notes": client.delivery_notes,
            "total_sales": money(client.total_sales),
            "url": f"/clients/{client.id}/",
        })
    return tool_response(
        "ok" if rows else "empty",
        summary={"count": len(rows)},
        records=rows,
        evidence=[evidence_item("client", row["name"], row["url"], {"total_sales": row["total_sales"]}) for row in rows],
        message="" if rows else "No hay clientes con albaranes entregados.",
    )


def list_customers(user, arguments=None, context=None):
    denied = require_authenticated(user)
    if denied:
        return denied
    arguments = arguments or {}
    status = arguments.get("status") or "active"
    qs = Client.objects.all().order_by("codi_client")
    if status == "inactive":
        qs = qs.filter(actiu=False)
    elif status != "all":
        status = "active"
        qs = qs.filter(actiu=True)
    rows = [
        {
            "id": client.id,
            "code": client.codi_client,
            "name": client.nom_comercial,
            "active": client.actiu,
            "contact": client.persona_contacte,
            "email": client.email,
            "url": f"/clients/{client.id}/",
        }
        for client in qs[: max_results(arguments.get("limit"))]
    ]
    return tool_response(
        "ok" if rows else "empty",
        summary={"count": len(rows), "status": status},
        records=rows,
        evidence=[evidence_item("client", row["name"], row["url"], {"active": row["active"]}) for row in rows],
        message="" if rows else "No hay clientes para estos filtros.",
    )
