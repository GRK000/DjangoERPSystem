from dataclasses import dataclass, field
from typing import Any, Callable

from django.conf import settings


ToolHandler = Callable[[Any, dict[str, Any] | None, dict[str, Any] | None], dict[str, Any]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    handler: ToolHandler
    input_schema: dict[str, Any] = field(default_factory=dict)
    read_only: bool = True
    required_permissions: tuple[str, ...] = ()
    max_results: int = 20


def max_results(value: Any = None) -> int:
    configured = getattr(settings, "AGENT_MAX_TOOL_RESULTS", 20)
    try:
        requested = int(value or configured)
    except (TypeError, ValueError):
        requested = configured
    return max(1, min(requested, configured, 100))


def tool_response(status="ok", summary=None, records=None, evidence=None, message=""):
    return {
        "status": status,
        "summary": summary or {},
        "records": records or [],
        "evidence": evidence or [],
        "message": message,
    }


def require_authenticated(user):
    if not getattr(user, "is_authenticated", False):
        return tool_response("permission_denied", message="Usuario no autenticado.")
    return None


def safe_str(value):
    return "" if value is None else str(value)
