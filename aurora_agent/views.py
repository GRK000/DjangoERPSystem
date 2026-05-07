import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .models import AgentConversation, AgentFeedback, AgentRun
from .permissions import require_api_auth
from .serializers import conversation_to_dict, run_to_dict
from .services.llm import agent_status
from .services.orchestrator import AuroraOperatorOrchestrator
from .services.rate_limit import check_rate_limit


SUGGESTIONS = [
    "Que albaranes puedo preparar hoy?",
    "Que productos tienen stock bajo?",
    "Resume la operacion de hoy",
    "Que bloquea la preparacion?",
    "Prioriza los albaranes pendientes",
]


def json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return None


@require_http_methods(["GET"])
@require_api_auth
def status(request):
    return JsonResponse(agent_status())


@require_http_methods(["GET"])
@require_api_auth
def suggestions(request):
    return JsonResponse({"suggestions": SUGGESTIONS})


@require_http_methods(["GET", "POST"])
@require_api_auth
def conversations(request):
    if request.method == "GET":
        qs = AgentConversation.objects.filter(user=request.user).order_by("-updated_at")[:30]
        return JsonResponse({"conversations": [conversation_to_dict(item) for item in qs]})
    body = json_body(request)
    if body is None:
        return JsonResponse({"detail": "JSON invalido."}, status=400)
    title = (body.get("title") or "Consulta operativa").strip()[:160]
    conversation = AgentConversation.objects.create(user=request.user, title=title or "Consulta operativa")
    return JsonResponse({"conversation": conversation_to_dict(conversation)}, status=201)


@require_http_methods(["GET"])
@require_api_auth
def conversation_detail(request, conversation_id):
    conversation = AgentConversation.objects.filter(id=conversation_id, user=request.user).prefetch_related("messages").first()
    if not conversation:
        return JsonResponse({"detail": "Conversacion no encontrada."}, status=404)
    return JsonResponse({"conversation": conversation_to_dict(conversation, include_messages=True)})


@require_http_methods(["POST"])
@require_api_auth
def run(request):
    if not check_rate_limit(request.user):
        return JsonResponse({"detail": "Rate limit excedido. Espera unos segundos."}, status=429)
    body = json_body(request)
    if body is None:
        return JsonResponse({"detail": "JSON invalido."}, status=400)
    message = (body.get("message") or "").strip()
    if len(message) > settings.AGENT_MAX_MESSAGE_LENGTH:
        return JsonResponse({"detail": f"Mensaje demasiado largo. Maximo {settings.AGENT_MAX_MESSAGE_LENGTH} caracteres."}, status=400)
    if not message:
        return JsonResponse({"detail": "El mensaje es obligatorio."}, status=400)
    orchestrator = AuroraOperatorOrchestrator(force_mock=bool(body.get("mock", False)))
    payload = orchestrator.run(
        request.user,
        message,
        conversation_id=body.get("conversation_id"),
        page_context=body.get("page_context") or {},
    )
    return JsonResponse(payload, status=200 if payload.get("status") != "error" else 500)


@require_http_methods(["POST"])
@require_api_auth
def feedback(request):
    body = json_body(request)
    if body is None:
        return JsonResponse({"detail": "JSON invalido."}, status=400)
    run_obj = AgentRun.objects.filter(id=body.get("run_id"), user=request.user).first()
    if not run_obj:
        return JsonResponse({"detail": "Run no encontrado."}, status=404)
    rating = body.get("rating")
    if rating not in {AgentFeedback.Rating.USEFUL, AgentFeedback.Rating.NOT_USEFUL}:
        return JsonResponse({"detail": "Rating invalido."}, status=400)
    feedback_obj, _ = AgentFeedback.objects.update_or_create(
        run=run_obj,
        user=request.user,
        defaults={"rating": rating, "comment": (body.get("comment") or "")[:1000]},
    )
    return JsonResponse({"feedback": {"id": feedback_obj.id, "rating": feedback_obj.rating}})


@require_http_methods(["GET"])
@require_api_auth
def runs(request):
    if not request.user.is_staff:
        return JsonResponse({"detail": "Solo staff puede consultar trazas globales."}, status=403)
    qs = AgentRun.objects.select_related("user", "conversation").prefetch_related("feedback").order_by("-created_at")
    status_filter = request.GET.get("status")
    mock_filter = request.GET.get("mock")
    user_filter = request.GET.get("user")
    query = request.GET.get("q")
    if status_filter:
        qs = qs.filter(status=status_filter)
    if mock_filter in {"true", "false"}:
        qs = qs.filter(provider="mock") if mock_filter == "true" else qs.exclude(provider="mock")
    if user_filter:
        qs = qs.filter(user__username__icontains=user_filter)
    if query:
        qs = qs.filter(input_message__icontains=query)
    return JsonResponse({"runs": [run_to_dict(run) for run in qs[:50]]})


@require_http_methods(["GET"])
@require_api_auth
def run_detail(request, run_id):
    qs = AgentRun.objects.select_related("user", "conversation").prefetch_related("tool_calls", "feedback")
    if request.user.is_staff:
        run_obj = qs.filter(id=run_id).first()
    else:
        run_obj = qs.filter(id=run_id, user=request.user).first()
    if not run_obj:
        return JsonResponse({"detail": "Run no encontrado."}, status=404)
    return JsonResponse({"run": run_to_dict(run_obj, include_detail=True)})
