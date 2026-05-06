from decimal import Decimal

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
    return (text or "").lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")


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
    count_answer = format_count_answer(text, tool_outputs)
    if count_answer:
        return count_answer
    if "stock bajo" in text or "stock critico" in text:
        return format_low_stock_answer(tool_outputs)
    if "prepar" in text or "prioriza" in text or "pendiente" in text:
        return format_preparation_answer(tool_outputs)
    if "venta" in text or "estadistica" in text or "ranking" in text:
        return format_sales_answer(tool_outputs)
    if "resumen" in text or "resume" in text or "operacion" in text:
        return format_operation_summary(tool_outputs)
    return format_generic_answer(tool_outputs)


def format_count_answer(text, tool_outputs):
    if "cliente" in text:
        value = metric_from(tool_outputs, "active_customers")
        if value is not None:
            return "No hay clientes activos registrados en el ERP." if value == 0 else f"Hay {value} {plural(value, 'cliente activo')} registrado{'' if value == 1 else 's'} en el ERP."
    if "producto" in text and "stock bajo" not in text:
        value = metric_from(tool_outputs, "active_products")
        if value is not None:
            return "No hay productos activos registrados en el ERP." if value == 0 else f"Hay {value} {plural(value, 'producto activo')} registrado{'' if value == 1 else 's'} en el ERP."
    if "albaran" in text or "albaranes" in text:
        value = metric_from(tool_outputs, "delivery_notes")
        if value is None:
            value = metric_from(tool_outputs, "total_delivery_notes")
        if value is not None:
            return "No hay albaranes registrados en el ERP." if value == 0 else f"Hay {value} {plural(value, 'albaran', 'albaranes')} registrado{'' if value == 1 else 's'} en el ERP."
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
    names = ", ".join(f"{row.get('sku')} {row.get('product')} ({row.get('quantity')} uds)" for row in records[:5])
    suffix = f" Principales: {names}." if names else ""
    return f"Hay {count} {plural(count, 'producto')} con stock bajo.{suffix}"


def format_preparation_answer(tool_outputs):
    priority = first_result(tool_outputs, "prioritize_delivery_notes")
    summary = priority.get("summary") or {}
    records = priority.get("records") or []
    if priority:
        count = summary.get("count", len(records))
        preparable = summary.get("preparable", 0)
        if count == 0:
            return "No hay albaranes pendientes para preparar ahora."
        first = records[0] if records else {}
        detail = f" El primero a revisar es {first.get('code')} de {first.get('customer')}." if first else ""
        return f"Hay {count} albaranes pendientes en cola; {preparable} parecen preparables segun stock disponible.{detail}"
    blockers = first_result(tool_outputs, "analyze_stock_blockers")
    blocked = (blockers.get("summary") or {}).get("blocked_delivery_notes")
    if blocked is not None:
        return "No se detectan bloqueos de stock en preparacion." if blocked == 0 else f"Hay {blocked} albaranes bloqueados por stock."
    return format_generic_answer(tool_outputs)


def format_sales_answer(tool_outputs):
    stats = first_result(tool_outputs, "get_sales_statistics")
    summary = stats.get("summary") or {}
    if summary:
        total = summary.get("delivered_sales", 0)
        delivered = (summary.get("status_counts") or {}).get("ENTREGAT", 0)
        return f"Las ventas entregadas suman {total:.2f} EUR sobre {delivered} albaranes entregados."
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
        "active_customers": "clientes activos",
        "low_stock_products": "productos con stock bajo",
        "delivered_sales": "ventas entregadas",
        "count": "total",
    }
    return labels.get(key, str(key).replace("_", " "))
