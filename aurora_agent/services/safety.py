from dataclasses import dataclass


DESTRUCTIVE_TERMS = (
    "borra",
    "borrar",
    "elimina",
    "eliminar",
    "cambia",
    "cambiar",
    "modifica",
    "modificar",
    "actualiza",
    "actualizar",
    "marca",
    "marcar",
    "entrega",
    "entregar",
    "crea",
    "crear",
    "inserta",
    "insertar",
    "edita",
    "editar",
    "stock a",
    "999",
)

SECRET_TERMS = (
    "api key",
    "apikey",
    "secreto",
    "secret",
    "system prompt",
    "prompt interno",
    "revela tu prompt",
    "ignora las instrucciones",
)


@dataclass
class SafetyResult:
    allowed: bool
    reason: str = ""
    category: str = "ok"


def check_input_safety(message: str, max_length: int) -> SafetyResult:
    text = (message or "").strip()
    lowered = text.lower()
    if not text:
        return SafetyResult(False, "El mensaje esta vacio.", "empty")
    if len(text) > max_length:
        return SafetyResult(False, f"El mensaje supera el limite de {max_length} caracteres.", "too_long")
    if any(term in lowered for term in SECRET_TERMS):
        return SafetyResult(False, "No puedo revelar prompts internos, secretos ni configuracion sensible.", "secret_request")
    imperative_prepare = lowered.startswith(("prepara ", "preparar "))
    if imperative_prepare or any(term in lowered for term in DESTRUCTIVE_TERMS):
        return SafetyResult(
            False,
            "Aurora Operator V1 es read-only. Puedo analizar y proponer un plan, pero no modificar albaranes, stock ni registros.",
            "write_request",
        )
    return SafetyResult(True)


def refusal_payload(reason: str):
    return {
        "answer": (
            "Resumen breve: solicitud bloqueada por seguridad.\n\n"
            f"Datos clave: {reason}\n\n"
            "Recomendacion operativa: revisa los datos desde el ERP y ejecuta cualquier cambio manualmente con confirmacion humana.\n\n"
            "Evidencia usada: no se consultaron tools porque la solicitud pedia una accion no permitida."
        ),
        "evidence": [],
        "suggested_actions": [
            {"type": "navigate", "label": "Ver albaranes", "target": "/albarans/"},
            {"type": "navigate", "label": "Ver stock", "target": "/stock/"},
        ],
        "tool_calls": [],
        "status": "blocked",
    }
