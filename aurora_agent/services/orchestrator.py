import json
import re
import time
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from aurora_agent.models import AgentConversation, AgentMessage, AgentRun, AgentToolCall
from aurora_agent.services.formatter import compact_tool_result, format_final_answer, normalize_text
from aurora_agent.services.llm import get_llm_client
from aurora_agent.services.prompts import PLAN_PROMPT, SYSTEM_PROMPT
from aurora_agent.services.safety import check_input_safety, refusal_payload
from aurora_agent.services.semantic_query import parse_semantic_query, previous_semantic_context, semantic_memory
from aurora_agent.tools.registry import TOOLS, get_tool


ALLOWED_ACTION_TARGETS = {"/", "/albarans/", "/preparacio/", "/stock/", "/cataleg/", "/clients/", "/estadistiques/"}


def parse_json_object(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text or "", flags=re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}
    return {}


def route_tools(message: str, page_context=None, semantic_query=None):
    text = normalize_text(message)
    semantic_query = semantic_query or parse_semantic_query(message)
    entity = semantic_query.entity
    intent = semantic_query.intent
    filters = semantic_query.filters or {}

    if intent == "count":
        if entity == "customers":
            return [{"name": "count_customers", "arguments": {"status": filters.get("status", "active")}}]
        if entity == "products":
            if filters.get("status") == "low_stock":
                return [{"name": "count_low_stock_products", "arguments": {}}]
            if filters.get("status") == "out_of_stock":
                return [{"name": "count_products", "arguments": {"status": "out_of_stock"}}]
            return [{"name": "count_products", "arguments": {"status": filters.get("status", "active")}}]
        if entity == "delivery_notes":
            return [{"name": "count_delivery_notes", "arguments": {"status": filters.get("status", "all")}}]
        if entity == "stock" and filters.get("status") == "low_stock":
            return [{"name": "count_low_stock_products", "arguments": {}}]

    if intent == "list" and entity == "products" and filters.get("status") == "low_stock":
        return [{"name": "list_low_stock_products", "arguments": {"limit": 12}}]
    if entity in {"products", "stock"} and filters.get("status") == "out_of_stock":
        return [{"name": "list_out_of_stock_products", "arguments": {"limit": 12}}]
    if entity == "products" and intent == "list":
        return [{"name": "list_products", "arguments": {"status": filters.get("status", "active"), "stock_filter": filters.get("stock_filter", ""), "limit": 12}}]
    if entity == "customers" and intent == "list":
        return [{"name": "list_customers", "arguments": {"status": filters.get("status", "active"), "limit": 12}}]
    if entity == "delivery_notes" and intent in {"list", "blockers"}:
        status = filters.get("status", "all")
        return [{"name": "analyze_stock_blockers" if status == "blocked" else "list_delivery_notes", "arguments": {"status": status, "blocked": status == "blocked", "preparable": status == "preparable", "limit": 12}}]
    if entity == "sales":
        return [{"name": "get_sales_statistics", "arguments": {"period": filters.get("period", "all")}}]
    if entity == "operations" or intent == "summarize":
        return [{"name": "summarize_daily_operations", "arguments": {}}]
    if intent == "prioritize" and entity in {"delivery_notes", ""}:
        return [{"name": "prioritize_delivery_notes", "arguments": {"limit": 12}}]

    tools = []
    count_question = any(term in text for term in ["cuantos", "cuantas", "numero de", "número de", "total de", "hay "])
    if count_question and "cliente" in text:
        return [{"name": "count_customers", "arguments": {"status": filters.get("status", "active")}}]
    if count_question and "producto" in text and ("stock bajo" in text or "bajo stock" in text):
        return [{"name": "count_low_stock_products", "arguments": {}}]
    if count_question and "producto" in text:
        return [{"name": "count_products", "arguments": {"status": filters.get("status", "active")}}]
    if count_question and ("albaran" in text or "albaranes" in text):
        return [{"name": "count_delivery_notes", "arguments": {"status": filters.get("status", "all")}}]
    if "hay stock bajo" in text:
        return [{"name": "count_low_stock_products", "arguments": {}}]
    if any(word in text for word in ["preparar", "preparables", "prioriza", "priorizar", "pendientes"]):
        tools.append({"name": "prioritize_delivery_notes", "arguments": {"limit": 12}})
    if any(word in text for word in ["bloquea", "bloqueos", "bloqueado", "stock insuficiente"]):
        tools.append({"name": "analyze_stock_blockers", "arguments": {"limit": 12}})
    if "stock bajo" in text or "stock critic" in text or "reponer" in text:
        tools.append({"name": "list_low_stock_products", "arguments": {"limit": 12}})
    if any(word in text for word in ["ventas", "estadisticas", "estadísticas", "iva", "ranking"]):
        tools.extend([
            {"name": "get_sales_statistics", "arguments": {}},
            {"name": "get_top_products", "arguments": {"limit": 10}},
            {"name": "get_top_customers", "arguments": {"limit": 10}},
        ])
    if any(word in text for word in ["producto", "catalogo", "catálogo", "sku"]):
        tools.append({"name": "list_products", "arguments": {"limit": 12}})
    if any(word in text for word in ["albaran", "albarán", "albaranes"]):
        tools.append({"name": "list_delivery_notes", "arguments": {"limit": 12}})
    if any(word in text for word in ["resume", "resumen", "hoy", "operacion", "operación"]):
        tools.insert(0, {"name": "summarize_daily_operations", "arguments": {}})
    if not tools:
        tools.append({"name": "get_operational_summary", "arguments": {}})

    deduped = []
    seen = set()
    for tool in tools:
        if tool["name"] not in seen and tool["name"] in TOOLS:
            deduped.append(tool)
            seen.add(tool["name"])
    return deduped[:6]


def classify_request(message: str, semantic_query=None) -> str:
    text = normalize_text(message)
    semantic_query = semantic_query or parse_semantic_query(message)
    if semantic_query.intent == "unsafe":
        return "unsafe"
    if semantic_query.intent == "help":
        return "app_help"
    if any(term in text for term in ("que dia", "que fecha", "fecha de hoy", "que hora", "hora es")):
        return "utility_date_time"
    if semantic_query.intent == "out_of_scope":
        return "out_of_scope"
    return "erp_query"


def routed_answer(category: str) -> dict[str, Any]:
    if category == "app_help":
        return {
            "answer": "Puedo ayudarte con consultas operativas de Aurora Ops ERP: clientes, productos, stock, albaranes, preparacion, ventas, bloqueos y resumen diario. En esta version soy read-only.",
            "status": "ok",
        }
    if category == "utility_date_time":
        now = timezone.localtime()
        return {
            "answer": f"Hoy es {now.strftime('%d/%m/%Y')} y la hora local del servidor es {now.strftime('%H:%M')}. Para consultas operativas, puedo ayudarte con albaranes, stock, productos, clientes, ventas y preparacion.",
            "status": "ok",
        }
    if category == "out_of_scope":
        return {
            "answer": "Estoy diseñado para consultas operativas de Aurora Ops ERP. Puedo ayudarte con albaranes, stock, productos, clientes, ventas y preparacion.",
            "status": "out_of_scope",
        }
    if category == "unsafe":
        return {
            "answer": "No puedo ayudar con solicitudes que intenten revelar secretos, saltarse instrucciones de seguridad o modificar datos. Aurora Operator V1 es read-only.",
            "status": "blocked",
        }
    return {"answer": "", "status": "ok"}


def plan_with_llm(client, message, page_context):
    try:
        response = client.chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"{PLAN_PROMPT}\nTools disponibles: {list(TOOLS.keys())}\nContexto: {page_context or {}}\nUsuario: {message}"},
            ],
            temperature=0,
            max_tokens=300,
        )
        parsed = parse_json_object(response.content)
        tools = parsed.get("tools") or []
        valid = []
        for item in tools:
            name = item.get("name")
            if name in TOOLS:
                valid.append({"name": name, "arguments": item.get("arguments") or {}})
        return valid[:6]
    except Exception:
        return []


def suggested_actions_for(tool_results):
    actions = []
    statuses = {call["name"]: call for call in tool_results}
    if "prioritize_delivery_notes" in statuses or "list_delivery_notes" in statuses:
        actions.append({"type": "navigate", "label": "Ver albaranes", "target": "/albarans/"})
    if "analyze_stock_blockers" in statuses:
        actions.append({"type": "navigate", "label": "Ver preparacion", "target": "/preparacio/"})
    if "list_low_stock_products" in statuses:
        actions.append({"type": "navigate", "label": "Ver stock", "target": "/stock/"})
    if "get_sales_statistics" in statuses:
        actions.append({"type": "navigate", "label": "Ver estadisticas", "target": "/estadistiques/"})
    safe = []
    seen = set()
    for action in actions:
        if action["target"] in ALLOWED_ACTION_TARGETS and action["target"] not in seen:
            safe.append(action)
            seen.add(action["target"])
    return safe


def deterministic_answer(message, tool_outputs, evidence=None, suggested_actions=None):
    return format_final_answer(message, tool_outputs, evidence=evidence or [], suggested_actions=suggested_actions or [])


def final_with_llm(client, message, tool_outputs):
    grounded = [compact_tool_result(item["result"]) | {"tool": item["name"]} for item in tool_outputs]
    try:
        response = client.chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Pregunta: {message}\nResultados de tools JSON: {json.dumps(grounded, ensure_ascii=False)}\nResponde grounded y breve. No muestres JSON, nombres internos de tools ni claves tecnicas."},
            ],
            temperature=settings.AI_TEMPERATURE,
            max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
        )
        return response
    except Exception:
        return None


class AuroraOperatorOrchestrator:
    def __init__(self, force_mock=False):
        self.force_mock = force_mock
        self.client = get_llm_client(force_mock=force_mock)

    @transaction.atomic
    def run(self, user, message: str, conversation_id=None, page_context=None):
        start = time.perf_counter()
        safety = check_input_safety(message, settings.AGENT_MAX_MESSAGE_LENGTH)
        conversation = self._get_or_create_conversation(user, message, conversation_id)
        semantic_query = parse_semantic_query(message, previous_semantic_context(conversation))
        route_category = classify_request(message, semantic_query)
        AgentMessage.objects.create(
            conversation=conversation,
            role=AgentMessage.Role.USER,
            content=message,
            metadata={"page_context": page_context or {}, "semantic_query": semantic_query.to_dict(), "route_category": route_category},
        )
        run = AgentRun.objects.create(
            conversation=conversation,
            user=user,
            input_message=message,
            provider=self.client.provider,
            model=self.client.model,
        )

        if route_category != "erp_query":
            payload = routed_answer(route_category)
            run.status = AgentRun.Status.BLOCKED if payload["status"] in {"blocked", "out_of_scope"} else AgentRun.Status.OK
            run.final_answer = payload["answer"]
            run.latency_ms = self._elapsed(start)
            run.save(update_fields=["status", "final_answer", "latency_ms"])
            AgentMessage.objects.create(
                conversation=conversation,
                role=AgentMessage.Role.ASSISTANT,
                content=payload["answer"],
                metadata={
                    "status": payload["status"],
                    "run_id": run.id,
                    "tool_calls": [],
                    "semantic_query": semantic_query.to_dict(),
                    "route_category": route_category,
                    "semantic_memory": semantic_memory(semantic_query),
                },
            )
            conversation.save(update_fields=["updated_at"])
            return {
                "conversation_id": conversation.id,
                "run_id": run.id,
                "answer": payload["answer"],
                "evidence": [],
                "suggested_actions": [],
                "tool_calls": [],
                "status": payload["status"],
                "semantic_query": semantic_query.to_dict(),
                "route_category": route_category,
            }

        if not safety.allowed:
            payload = refusal_payload(safety.reason)
            run.status = AgentRun.Status.BLOCKED
            run.final_answer = payload["answer"]
            run.latency_ms = self._elapsed(start)
            run.save(update_fields=["status", "final_answer", "latency_ms"])
            AgentMessage.objects.create(
                conversation=conversation,
                role=AgentMessage.Role.ASSISTANT,
                content=payload["answer"],
                metadata={"status": "blocked", "run_id": run.id, "tool_calls": [], "semantic_query": semantic_query.to_dict(), "semantic_memory": semantic_memory(semantic_query)},
            )
            conversation.save(update_fields=["updated_at"])
            return {**payload, "conversation_id": conversation.id, "run_id": run.id, "semantic_query": semantic_query.to_dict(), "route_category": route_category}

        deterministic_plan = []
        if semantic_query.intent == "count" and semantic_query.entity:
            deterministic_plan = route_tools(message, page_context, semantic_query=semantic_query)
        plan = deterministic_plan if deterministic_plan else [] if self.client.provider == "mock" else plan_with_llm(self.client, message, page_context)
        if not plan:
            plan = route_tools(message, page_context, semantic_query=semantic_query)

        tool_outputs = []
        for item in plan:
            spec = get_tool(item["name"])
            if not spec or not spec.read_only:
                continue
            tool_start = time.perf_counter()
            try:
                result = spec.handler(user, item.get("arguments") or {}, page_context or {})
                status = result.get("status", "ok")
                error = "" if status != "error" else result.get("message", "")
            except Exception as exc:
                result = {"status": "error", "summary": {}, "records": [], "evidence": [], "message": str(exc)}
                status = "error"
                error = str(exc)
            call = AgentToolCall.objects.create(
                run=run,
                conversation=conversation,
                tool_name=spec.name,
                arguments=item.get("arguments") or {},
                result=compact_tool_result(result, record_limit=settings.AGENT_MAX_TOOL_RESULTS),
                status=status,
                latency_ms=self._elapsed(tool_start),
                error_message=error,
            )
            AgentMessage.objects.create(conversation=conversation, role=AgentMessage.Role.TOOL, content=spec.name, metadata={"tool_call_id": call.id, "result": call.result})
            tool_outputs.append({"name": spec.name, "status": status, "arguments": item.get("arguments") or {}, "result": result})

        evidence = []
        for output in tool_outputs:
            evidence.extend(output["result"].get("evidence", []))
        actions = suggested_actions_for(tool_outputs)
        llm_response = None if self.client.provider == "mock" else final_with_llm(self.client, message, tool_outputs)
        answer = llm_response.content if llm_response and llm_response.content else deterministic_answer(message, tool_outputs, evidence, actions)

        run.status = AgentRun.Status.OK
        run.final_answer = answer
        run.latency_ms = self._elapsed(start)
        if llm_response:
            run.prompt_tokens = llm_response.prompt_tokens
            run.completion_tokens = llm_response.completion_tokens
            run.total_tokens = llm_response.total_tokens
        run.save()
        tool_calls = [{"name": output["name"], "status": output["status"], "arguments": output.get("arguments", {})} for output in tool_outputs]
        AgentMessage.objects.create(
            conversation=conversation,
            role=AgentMessage.Role.ASSISTANT,
            content=answer,
            metadata={"evidence": evidence[:20], "suggested_actions": actions, "tool_calls": tool_calls, "run_id": run.id, "status": "ok", "semantic_query": semantic_query.to_dict(), "route_category": route_category, "semantic_memory": semantic_memory(semantic_query)},
        )
        conversation.save(update_fields=["updated_at"])
        return {
            "conversation_id": conversation.id,
            "run_id": run.id,
            "answer": answer,
            "evidence": evidence[:20],
            "suggested_actions": actions,
            "tool_calls": tool_calls,
            "status": "ok",
            "semantic_query": semantic_query.to_dict(),
            "route_category": route_category,
        }

    def _get_or_create_conversation(self, user, message, conversation_id=None):
        if conversation_id:
            existing = AgentConversation.objects.filter(id=conversation_id, user=user).first()
            if existing:
                return existing
        title = (message or "Consulta operativa").strip().splitlines()[0][:150]
        return AgentConversation.objects.create(user=user, title=title or "Consulta operativa")

    @staticmethod
    def _elapsed(start):
        return int((time.perf_counter() - start) * 1000)
