from .models import AgentConversation, AgentFeedback, AgentMessage, AgentRun


def message_to_dict(message: AgentMessage):
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "metadata": message.metadata or {},
        "created_at": message.created_at.isoformat(),
    }


def conversation_to_dict(conversation: AgentConversation, include_messages=False):
    data = {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
    }
    if include_messages:
        data["messages"] = [message_to_dict(message) for message in conversation.messages.all()]
    return data


def _cap(value, limit=1200):
    value = "" if value is None else str(value)
    return value if len(value) <= limit else value[:limit] + "..."


def run_to_dict(run: AgentRun, include_detail=False):
    assistant_message = run.conversation.messages.filter(metadata__run_id=run.id, role=AgentMessage.Role.ASSISTANT).first()
    semantic = (assistant_message.metadata or {}).get("semantic_query") if assistant_message else {}
    route_category = (assistant_message.metadata or {}).get("route_category") if assistant_message else ""
    feedback = run.feedback.order_by("-created_at").first()
    data = {
        "id": run.id,
        "user": run.user.username,
        "conversation_id": run.conversation_id,
        "conversation_title": run.conversation.title,
        "input": _cap(run.input_message, 600),
        "answer": _cap(run.final_answer, 900),
        "status": run.status,
        "intent": (semantic or {}).get("intent", ""),
        "entity": (semantic or {}).get("entity", ""),
        "filters": (semantic or {}).get("filters", {}),
        "semantic_query": semantic or {},
        "route_category": route_category,
        "provider": run.provider,
        "model": run.model,
        "mock": run.provider == "mock",
        "latency_ms": run.latency_ms,
        "feedback": feedback.rating if isinstance(feedback, AgentFeedback) else "",
        "created_at": run.created_at.isoformat(),
    }
    if include_detail:
        data["tool_calls"] = [
            {
                "id": call.id,
                "name": call.tool_name,
                "arguments": call.arguments,
                "status": call.status,
                "latency_ms": call.latency_ms,
                "summary": (call.result or {}).get("summary", {}),
                "message": (call.result or {}).get("message", ""),
                "records": (call.result or {}).get("records", [])[:5],
            }
            for call in run.tool_calls.all()
        ]
        data["error_message"] = _cap(run.error_message, 900)
    return data
