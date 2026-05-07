from decimal import Decimal
import unicodedata

from django.utils import timezone


def money(value):
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return value


def date(value):
    return value.isoformat() if value else None


def datetime(value):
    if not value:
        return None
    return timezone.localtime(value).isoformat()


def compact_tool_result(result, record_limit=10):
    return {
        "status": result.get("status"),
        "summary": result.get("summary", {}),
        "records": result.get("records", [])[:record_limit],
        "evidence": result.get("evidence", [])[:record_limit],
        "message": result.get("message", ""),
    }


def normalize_text(text):
    value = (text or "").lower()
    value = value.replace("Ã¡", "a").replace("Ã©", "e").replace("Ã­", "i").replace("Ã³", "o").replace("Ãº", "u")
    value = value.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    return "".join(ch for ch in unicodedata.normalize("NFKD", value) if not unicodedata.combining(ch))


def plural(value, singular, plural_text=None):
    return singular if value == 1 else (plural_text or f"{singular}s")


def first_result(tool_outputs, name):
    for output in tool_outputs:
        if output.get("name") == name:
            return output.get("result") or {}
    return {}


def metric_from(tool_outputs, key):
    for output in tool_outputs:
        summary = (output.get("result") or {}).get("summary") or {}
        if key in summary:
            return summary[key]
    return None


def format_final_answer(user_message, tool_outputs, evidence=None, suggested_actions=None):
    text = normalize_text(user_message)
    if "sin stock" in text:
        return format_out_of_stock_answer(tool_outputs)
    count_answer = format_count_answer(text, tool_outputs)
    if count_answer:
        return count_answer
    if "bloque" in text:
        return format_blockers_answer(tool_outputs)
    if "stock bajo" in text or "stock critico" in text:
        return format_low_stock_answer(tool_outputs)
    if "prepar" in text or "prioriza" in text or "pendiente" in text:
        return format_preparation_answer(tool_outputs)
    if "venta" in text or "estadistica" in text or "ranking" in text or "base imponible" in text or "iva" in text:
        return format_sales_answer(tool_outputs)
    if "resumen" in text or "resume" in text or "operacion" in text:
        return format_operation_summary(tool_outputs)
    return format_generic_answer(tool_outputs)


def format_count_answer(text, tool_outputs):
    if "cliente" in text or first_result(tool_outputs, "count_customers"):
        result = first_result(tool_outputs, "count_customers")
        summary = result.get("summary") or {}
        status = summary.get("status", "active")
        if result.get("status") == "not_available":
            return result.get("message") or "No puedo distinguir clientes por estado con los datos disponibles."
        key = "inactive_customers" if status == "inactive" else "total_customers" if status == "all" else "active_customers"
        value = summary.get(key)
        if value is not None:
            if status == "inactive":
                return "No hay clientes no activos registrados en el ERP." if value == 0 else f"Hay {value} {plural(value, 'cliente no activo', 'clientes no activos')} registrado{'' if value == 1 else 's'} en el ERP."
            if status == "all":
                return "No hay clientes registrados en el ERP." if value == 0 else f"Hay {value} {plural(value, 'cliente')} registrado{'' if value == 1 else 's'} en el ERP."
            return "No hay clientes activos registrados en el ERP." if value == 0 else f"Hay {value} {plural(value, 'cliente activo')} registrado{'' if value == 1 else 's'} en el ERP."
    if ("producto" in text and "stock bajo" not in text) or first_result(tool_outputs, "count_products"):
        result = first_result(tool_outputs, "count_products")
        summary = result.get("summary") or {}
        status = summary.get("status", "active")
        key = "out_of_stock_products" if status == "out_of_stock" else "low_stock_products" if status == "low_stock" else "inactive_products" if status == "inactive" else "total_products" if status == "all" else "active_products"
        value = summary.get(key)
        if value is not None:
            if status == "out_of_stock":
                return "No hay productos sin stock." if value == 0 else f"Hay {value} {plural(value, 'producto')} sin stock."
            if status == "low_stock":
                return "No hay productos con stock bajo." if value == 0 else f"Hay {value} {plural(value, 'producto')} con stock bajo."
            if status == "inactive":
                return "No hay productos no activos registrados en el ERP." if value == 0 else f"Hay {value} {plural(value, 'producto no activo', 'productos no activos')} registrado{'' if value == 1 else 's'} en el ERP."
            if status == "all":
                return "No hay productos registrados en el ERP." if value == 0 else f"Hay {value} {plural(value, 'producto')} registrado{'' if value == 1 else 's'} en el ERP."
            return "No hay productos activos registrados en el ERP." if value == 0 else f"Hay {value} {plural(value, 'producto activo')} registrado{'' if value == 1 else 's'} en el ERP."
    if "albaran" in text or "albaranes" in text or first_result(tool_outputs, "count_delivery_notes"):
        result = first_result(tool_outputs, "count_delivery_notes")
        summary = result.get("summary") or {}
        status = summary.get("status", "all")
        value = summary.get("delivery_notes")
        if value is not None:
            suffix = {
                "pending": "pendientes",
                "delivered": "entregados",
                "preparable": "preparables",
                "cancelled": "cancelados",
                "all": "registrados",
            }.get(status, "registrados")
            return f"No hay albaranes {suffix} en el ERP." if value == 0 else f"Hay {value} {plural(value, 'albaran', 'albaranes')} {suffix} en el ERP."
    if "stock bajo" in text or "bajo stock" in text:
        value = metric_from(tool_outputs, "low_stock_products")
        if value is not None:
            return "No hay productos con stock bajo." if value == 0 else f"Hay {value} {plural(value, 'producto')} con stock bajo."
    return ""


def format_low_stock_answer(tool_outputs):
    result = first_result(tool_outputs, "list_low_stock_products")
    records = result.get("records") or []
    count = (result.get("summary") or {}).get("count", len(records))
    if count == 0:
        return "No hay productos con stock bajo."
    lines = "\n".join(f"- {row.get('product')}: {row.get('quantity')} unidades disponibles en {row.get('warehouse')}" for row in records[:8])
    recommendation = "\n\nRecomendacion: revisa reposicion antes de preparar albaranes pendientes."
    return f"Hay {count} {plural(count, 'producto')} con stock bajo:\n{lines}{recommendation}"


def format_out_of_stock_answer(tool_outputs):
    result = first_result(tool_outputs, "list_out_of_stock_products")
    records = result.get("records") or []
    count = (result.get("summary") or {}).get("count", len(records))
    if count == 0:
        return "No hay productos sin stock."
    lines = "\n".join(f"- {row.get('product')}: 0 unidades en {row.get('warehouse')}" for row in records[:8])
    return f"Hay {count} {plural(count, 'producto')} sin stock:\n{lines}\n\nRecomendacion: prioriza reposicion o sustituye lineas bloqueadas."


def format_preparation_answer(tool_outputs):
    priority = first_result(tool_outputs, "prioritize_delivery_notes")
    summary = priority.get("summary") or {}
    records = priority.get("records") or []
    if priority:
        count = summary.get("count", len(records))
        preparable = summary.get("preparable", 0)
        if count == 0:
            return "No hay albaranes pendientes para preparar ahora."
        preparable_rows = [row for row in records if row.get("preparable")]
        blocked_rows = [row for row in records if not row.get("preparable")]
        if not preparable_rows:
            return f"No hay albaranes preparables con el stock actual. Hay {len(blocked_rows)} albaranes bloqueados o pendientes de revision."
        lines = "\n".join(f"- {row.get('code')} · {row.get('customer')}" for row in preparable_rows[:6])
        blocked_line = f"\n\nHay {len(blocked_rows)} albaran{'es' if len(blocked_rows) != 1 else ''} bloqueado{'s' if len(blocked_rows) != 1 else ''} por falta de stock." if blocked_rows else ""
        return f"Puedes preparar {preparable} albaranes pendientes con el stock actual:\n{lines}{blocked_line}\n\nRecomendacion: prepara primero los albaranes sin bloqueos y revisa stock antes de prometer entregas."
    return format_blockers_answer(tool_outputs) if first_result(tool_outputs, "analyze_stock_blockers") else format_generic_answer(tool_outputs)


def format_blockers_answer(tool_outputs):
    blockers = first_result(tool_outputs, "analyze_stock_blockers")
    blocked = (blockers.get("summary") or {}).get("blocked_delivery_notes")
    if blocked is not None:
        if blocked == 0:
            return "No se detectan albaranes bloqueados por stock en preparacion."
        lines = []
        for item in blockers.get("records", [])[:5]:
            dn = item.get("delivery_note", {})
            products = ", ".join(line.get("product", "") for line in item.get("blocked_lines", [])[:3])
            lines.append(f"- {dn.get('code')} · {dn.get('customer')}: {products}")
        return f"Hay {blocked} albaranes bloqueados por stock:\n" + "\n".join(lines)
    return format_generic_answer(tool_outputs)


def format_sales_answer(tool_outputs):
    stats = first_result(tool_outputs, "get_sales_statistics")
    summary = stats.get("summary") or {}
    if summary:
        total = summary.get("delivered_sales", 0)
        base = summary.get("base", 0)
        vat = summary.get("vat", 0)
        delivered = (summary.get("status_counts") or {}).get("ENTREGAT", 0)
        return f"Las ventas entregadas suman {total:.2f} EUR sobre {delivered} albaranes entregados. Base imponible: {base:.2f} EUR. IVA: {vat:.2f} EUR."
    return format_generic_answer(tool_outputs)


def format_operation_summary(tool_outputs):
    summary_tool = first_result(tool_outputs, "summarize_daily_operations")
    summary = (summary_tool.get("summary") or {}).get("operation") or (first_result(tool_outputs, "get_operational_summary").get("summary") or {})
    if not summary:
        return format_generic_answer(tool_outputs)
    return (
        f"Operacion actual: {summary.get('pending_delivery_notes', 0)} albaranes pendientes, "
        f"{summary.get('in_preparation', 0)} en preparacion, "
        f"{summary.get('low_stock_products', 0)} productos con stock bajo y "
        f"{summary.get('active_customers', 0)} clientes activos."
    )


def format_generic_answer(tool_outputs):
    for output in tool_outputs:
        result = output.get("result") or {}
        if result.get("status") == "permission_denied":
            return result.get("message") or "No tienes permisos para consultar esos datos."
        if result.get("status") == "error":
            return result.get("message") or "No se pudo completar la consulta."
    for output in tool_outputs:
        result = output.get("result") or {}
        summary = result.get("summary") or {}
        if summary:
            readable = ", ".join(f"{humanize_key(key)}: {value}" for key, value in summary.items() if not isinstance(value, dict))
            if readable:
                return f"Datos disponibles: {readable}."
        message = result.get("message")
        if message:
            return message
    return "No he encontrado datos suficientes para responder con seguridad."


def humanize_key(key):
    labels = {
        "pending_delivery_notes": "albaranes pendientes",
        "in_preparation": "en preparacion",
        "delivered": "entregados",
        "active_products": "productos activos",
        "inactive_products": "productos no activos",
        "total_products": "productos registrados",
        "active_customers": "clientes activos",
        "inactive_customers": "clientes no activos",
        "total_customers": "clientes registrados",
        "low_stock_products": "productos con stock bajo",
        "delivered_sales": "ventas entregadas",
        "count": "total",
    }
    return labels.get(key, str(key).replace("_", " "))
