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
    if any(term in text for term in ("borra", "borrar", "elimina", "eliminar", "cambia", "cambiar", "marca", "marcar", "entrega", "prepara ")):
        return "unsafe"
    if "prioriza" in text or "priorizar" in text or "preparables" in text or "puedo preparar" in text:
        return "prioritize"
    if "bloquea" in text or "bloqueos" in text or "bloqueado" in text:
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
    if "stock" in text:
        return "stock"
    if "venta" in text or "iva" in text or "estadistica" in text:
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

    if "stock bajo" in text or "bajo stock" in text:
        filters["status"] = "low_stock"
    if "sin stock" in text or "stock cero" in text:
        filters["status"] = "low_stock"
        filters["stock_zero"] = True

    if "pendiente" in text or "pendientes" in text:
        filters["status"] = "pending"
    elif "entregado" in text or "entregados" in text or "entregadas" in text:
        filters["status"] = "delivered"
    elif "preparable" in text or "preparables" in text:
        filters["status"] = "preparable"
    elif "cancelado" in text or "cancelados" in text:
        filters["status"] = "cancelled"
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
    }


def apply_defaults(query: SemanticQuery) -> None:
    if query.entity in {"customers", "products"} and query.intent == "count" and not query.filters.get("status"):
        query.filters["status"] = "active"
    if query.entity == "delivery_notes" and query.intent == "count" and not query.filters.get("status"):
        query.filters["status"] = "all"


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
