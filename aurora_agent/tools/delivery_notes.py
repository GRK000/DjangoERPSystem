from django.db.models import Sum

from albaranes.models import Albara, LiniaAlbara, StockMagatzem
from aurora_agent.services.evidence import evidence_item
from aurora_agent.services.formatter import date, datetime, money

from .base import max_results, require_authenticated, tool_response


def serialize_delivery_note(albara, include_lines=False):
    data = {
        "id": albara.id,
        "code": albara.numero_albara,
        "customer": albara.client.nom_comercial,
        "customer_id": albara.client_id,
        "warehouse": albara.magatzem.nom if albara.magatzem else "",
        "status": albara.estat,
        "status_label": albara.get_estat_display(),
        "created_at": datetime(albara.data_creacio),
        "expected_delivery": date(albara.data_entrega_prevista),
        "total": money(albara.total),
        "base": money(albara.base_imposable),
        "vat": money(albara.total_iva),
        "url": f"/albarans/{albara.id}/",
    }
    if include_lines:
        data["lines"] = [serialize_line(line, albara.magatzem_id) for line in albara.linies.all()]
    return data


def serialize_line(line, warehouse_id=None):
    available = None
    location = ""
    blocked = False
    if line.producte_id and warehouse_id:
        stock = StockMagatzem.objects.filter(producte_id=line.producte_id, magatzem_id=warehouse_id).first()
        if stock:
            available = stock.quantitat
            location = stock.ubicacio
            blocked = stock.quantitat < line.quantitat
        else:
            available = 0
            blocked = True
    return {
        "id": line.id,
        "product_id": line.producte_id,
        "product": line.nom_producte,
        "quantity": line.quantitat,
        "unit_price": money(line.preu_unitari),
        "subtotal": money(line.subtotal),
        "available_stock": available,
        "location": location,
        "blocked": blocked,
    }


def list_delivery_notes(user, arguments=None, context=None):
    denied = require_authenticated(user)
    if denied:
        return denied
    arguments = arguments or {}
    qs = Albara.objects.select_related("client", "magatzem").order_by("-data_creacio")
    status = arguments.get("status")
    if status:
        qs = qs.filter(estat=str(status).upper())
    customer_query = arguments.get("customer_query") or arguments.get("customer")
    if customer_query:
        qs = qs.filter(client__nom_comercial__icontains=customer_query)
    if arguments.get("date_from"):
        qs = qs.filter(data_creacio__date__gte=arguments["date_from"])
    if arguments.get("date_to"):
        qs = qs.filter(data_creacio__date__lte=arguments["date_to"])
    limit = max_results(arguments.get("limit"))
    rows = [serialize_delivery_note(albara) for albara in qs[:limit]]
    return tool_response(
        "ok" if rows else "empty",
        summary={"count": len(rows), "limit": limit},
        records=rows,
        evidence=[evidence_item("albara", row["code"], row["url"], {"status": row["status"]}) for row in rows],
        message="" if rows else "No hay albaranes para estos filtros.",
    )


def get_delivery_note_detail(user, arguments=None, context=None):
    denied = require_authenticated(user)
    if denied:
        return denied
    arguments = arguments or {}
    qs = Albara.objects.select_related("client", "magatzem").prefetch_related("linies__producte")
    albara = None
    if arguments.get("delivery_note_id"):
        albara = qs.filter(id=arguments["delivery_note_id"]).first()
    if not albara and arguments.get("code"):
        albara = qs.filter(numero_albara__iexact=arguments["code"]).first()
    if not albara:
        return tool_response("empty", message="No se encontro el albaran solicitado.")
    row = serialize_delivery_note(albara, include_lines=True)
    return tool_response(
        "ok",
        summary={"code": row["code"], "status": row["status"], "total": row["total"], "lines": len(row["lines"])},
        records=[row],
        evidence=[evidence_item("albara", row["code"], row["url"], {"status": row["status"]})],
    )


def check_delivery_note_stock(user, arguments=None, context=None):
    denied = require_authenticated(user)
    if denied:
        return denied
    detail = get_delivery_note_detail(user, arguments, context)
    if detail["status"] != "ok":
        return detail
    albara = detail["records"][0]
    lines_ok = []
    blocked = []
    for line in albara.get("lines", []):
        if line["available_stock"] is None:
            line["message"] = "Sin producto o sin almacen asignado."
            blocked.append(line)
        elif line["blocked"]:
            line["missing"] = max(line["quantity"] - line["available_stock"], 0)
            blocked.append(line)
        else:
            lines_ok.append(line)
    return tool_response(
        "ok",
        summary={"preparable": not blocked, "lines_ok": len(lines_ok), "blocked": len(blocked)},
        records=[{"delivery_note": albara, "lines_ok": lines_ok, "blocked_lines": blocked}],
        evidence=detail["evidence"],
        message="Preparable." if not blocked else "Hay lineas bloqueadas por stock.",
    )


def analyze_stock_blockers(user, arguments=None, context=None):
    denied = require_authenticated(user)
    if denied:
        return denied
    qs = Albara.objects.filter(estat__in=[Albara.Estat.PENDENT, Albara.Estat.EN_PREPARACIO]).select_related("client", "magatzem").prefetch_related("linies__producte")
    records = []
    evidence = []
    for albara in qs[: max_results((arguments or {}).get("limit"))]:
        result = check_delivery_note_stock(user, {"delivery_note_id": albara.id}, context)
        if result["status"] == "ok" and result["summary"].get("blocked"):
            blocked = result["records"][0]["blocked_lines"]
            records.append({"delivery_note": serialize_delivery_note(albara), "blocked_lines": blocked})
            evidence.append(evidence_item("albara", albara.numero_albara, f"/albarans/{albara.id}/", {"blocked": len(blocked)}))
    return tool_response(
        "ok" if records else "empty",
        summary={"blocked_delivery_notes": len(records)},
        records=records,
        evidence=evidence,
        message="" if records else "No se detectaron bloqueos de stock en albaranes pendientes.",
    )


def prioritize_delivery_notes(user, arguments=None, context=None):
    denied = require_authenticated(user)
    if denied:
        return denied
    qs = Albara.objects.filter(estat__in=[Albara.Estat.PENDENT, Albara.Estat.EN_PREPARACIO]).select_related("client", "magatzem").prefetch_related("linies__producte").order_by("data_creacio")
    ranked = []
    for albara in qs[: max_results((arguments or {}).get("limit"))]:
        stock = check_delivery_note_stock(user, {"delivery_note_id": albara.id}, context)
        blocked = stock["summary"].get("blocked", 0) if stock["status"] == "ok" else 99
        ranked.append({
            **serialize_delivery_note(albara),
            "preparable": blocked == 0,
            "blocked_lines": blocked,
            "priority_score": (0 if blocked == 0 else 100) + (0 if albara.estat == Albara.Estat.EN_PREPARACIO else 10) - float(albara.total or 0) / 10000,
        })
    ranked.sort(key=lambda item: item["priority_score"])
    return tool_response(
        "ok" if ranked else "empty",
        summary={"count": len(ranked), "preparable": sum(1 for item in ranked if item["preparable"])},
        records=ranked,
        evidence=[evidence_item("albara", row["code"], row["url"], {"preparable": row["preparable"]}) for row in ranked],
    )


def get_top_products_from_delivered(limit):
    return LiniaAlbara.objects.filter(albara__estat=Albara.Estat.ENTREGAT).values("nom_producte").annotate(
        total_quantity=Sum("quantitat"),
        total_sales=Sum("subtotal"),
    ).order_by("-total_quantity")[:limit]
