from dataclasses import asdict, dataclass, field
import re
from typing import Any

from aurora_agent.services.formatter import normalize_text


@dataclass
class SemanticQuery:
    intent: str = "summarize"
    entity: str = ""
    filters: dict[str, Any] = field(default_factory=dict)
    metric: str = ""
    text_query: str = ""
    is_followup: bool = False

    def to_dict(self):
        return asdict(self)


def parse_semantic_query(message: str, previous_context: dict[str, Any] | None = None) -> SemanticQuery:
    text = normalize_text(message)
    previous_context = previous_context or {}
    query = SemanticQuery(
        intent=detect_intent(text),
        entity=detect_entity(text),
        filters=detect_filters(text),
        metric="",
        text_query=text,
    )
    query.metric = "count" if query.intent == "count" else "ranking" if "ranking" in text or "top" in text else "blockers" if "bloque" in text else ""
    query.is_followup = is_followup(text, query.entity)

    if query.is_followup and previous_context:
        if not query.entity:
            query.entity = previous_context.get("last_entity") or previous_context.get("entity") or ""
        if not query.metric:
            query.metric = previous_context.get("last_metric") or previous_context.get("metric") or "count"
        if query.intent in {"summarize", "help"}:
            query.intent = previous_context.get("last_intent") or previous_context.get("intent") or "count"
        previous_filters = previous_context.get("last_filters") or previous_context.get("filters") or {}
        query.filters = {**previous_filters, **query.filters}

    apply_defaults(query)
    return query


def detect_intent(text: str) -> str:
    if is_unsafe_text(text):
        return "unsafe"
    if is_help_text(text):
        return "help"
    if is_out_of_scope_text(text):
        return "out_of_scope"
    if any(term in text for term in ("borra", "borrar", "elimina", "eliminar", "cambia", "cambiar", "marca", "marcar", "prepara ")):
        return "unsafe"
    if "prioriza" in text or "priorizar" in text or "preparables" in text or "puedo preparar" in text:
        return "prioritize"
    if "bloquea" in text or "bloqueos" in text or "bloqueado" in text or "bloqueados" in text:
        return "blockers"
    if "analiza" in text or "analisis" in text:
        return "analyze"
    if any(term in text for term in ("cuanto", "cuantos", "cuanta", "cuantas", "numero", "total", "hay")):
        return "count"
    if any(term in text for term in ("lista", "listar", "dime", "cuales", "que ")):
        return "list"
    if "ayuda" in text or "help" in text:
        return "help"
    return "summarize"


def detect_entity(text: str) -> str:
    if "cliente" in text:
        return "customers"
    if "producto" in text or "catalogo" in text or "sku" in text:
        return "products"
    if "albaran" in text or "albaranes" in text:
        return "delivery_notes"
    if "operacion" in text or "operativa" in text or "hoy" in text:
        return "operations"
    if "stock" in text or "reponer" in text:
        return "stock"
    if "venta" in text or "ventas" in text or "iva" in text or "base imponible" in text or "estadistica" in text:
        return "sales"
    return ""


def detect_filters(text: str) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    inactive_patterns = (
        "no activo",
        "no activos",
        "no activa",
        "no activas",
        "inactivo",
        "inactivos",
        "desactivado",
        "desactivados",
        "deshabilitado",
        "deshabilitados",
    )
    if any(pattern in text for pattern in inactive_patterns):
        filters["status"] = "inactive"
    elif re.search(r"\bactivos?\b", text):
        filters["status"] = "active"
    elif "todos" in text or "todas" in text:
        filters["status"] = "all"

    if "stock bajo" in text or "bajo stock" in text or "stock critico" in text:
        filters["status"] = "low_stock"
    if "sin stock" in text or "stock cero" in text:
        filters["status"] = "out_of_stock"
        filters["stock_filter"] = "out_of_stock"
    elif filters.get("status") == "low_stock":
        filters["stock_filter"] = "low_stock"

    if "pendiente" in text or "pendientes" in text:
        filters["status"] = "pending"
    elif "en preparacion" in text or "preparacion" in text:
        filters["status"] = "in_preparation"
    elif "preparado" in text or "preparados" in text:
        filters["status"] = "prepared"
    elif "enviado" in text or "enviados" in text:
        filters["status"] = "sent"
    elif "entregado" in text or "entregados" in text or "entregadas" in text:
        filters["status"] = "delivered"
    elif "preparable" in text or "preparables" in text:
        filters["status"] = "preparable"
    elif "bloqueado" in text or "bloqueados" in text or "bloquea" in text:
        filters["status"] = "blocked"
    elif "cancelado" in text or "cancelados" in text:
        filters["status"] = "cancelled"
    if "hoy" in text:
        filters["period"] = "today"
    if "mes" in text:
        filters["period"] = "month"
    return filters


def is_followup(text: str, entity: str) -> bool:
    if entity:
        return False
    return text.startswith(("y ", "e ", "tambien", "ademas")) or text in {
        "no activos",
        "no activo",
        "activos",
        "pendientes",
        "entregados",
        "bloqueados",
        "preparables",
        "sin stock",
        "stock bajo",
    }


def apply_defaults(query: SemanticQuery) -> None:
    if query.entity in {"customers", "products"} and query.intent == "count" and not query.filters.get("status"):
        query.filters["status"] = "active"
    if query.entity == "delivery_notes" and query.intent == "count" and not query.filters.get("status"):
        query.filters["status"] = "all"
    if query.entity == "sales" and not query.filters.get("period"):
        query.filters["period"] = "all"


def is_help_text(text: str) -> bool:
    return any(term in text for term in ("que puedes hacer", "ayuda", "capacidades", "como me ayudas", "help"))


def is_unsafe_text(text: str) -> bool:
    return any(term in text for term in ("api key", "apikey", "system prompt", "prompt interno", "ignora tus instrucciones", "dime la api", "revela"))


def is_out_of_scope_text(text: str) -> bool:
    erp_terms = ("cliente", "producto", "stock", "albaran", "albaranes", "venta", "preparacion", "operacion", "erp", "aurora")
    utility_terms = ("que dia", "fecha", "hora", "hoy")
    if any(term in text for term in erp_terms + utility_terms):
        return False
    return any(term in text for term in ("react", "python", "historia", "receta", "chiste", "poema", "explicame"))


def semantic_memory(query: SemanticQuery) -> dict[str, Any]:
    return {
        "last_entity": query.entity,
        "last_intent": query.intent,
        "last_metric": query.metric,
        "last_filters": query.filters,
    }


def previous_semantic_context(conversation) -> dict[str, Any]:
    if not conversation or not getattr(conversation, "id", None):
        return {}
    for message in conversation.messages.order_by("-created_at")[:12]:
        semantic = (message.metadata or {}).get("semantic_query") or {}
        if semantic.get("entity"):
            return {
                "last_entity": semantic.get("entity"),
                "last_intent": semantic.get("intent"),
                "last_metric": semantic.get("metric"),
                "last_filters": semantic.get("filters") or {},
            }
    return {}
