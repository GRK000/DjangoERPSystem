import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from aurora_agent.services.orchestrator import AuroraOperatorOrchestrator


class Command(BaseCommand):
    help = "Ejecuta evaluaciones smoke de Aurora Operator."

    def add_arguments(self, parser):
        parser.add_argument("--dataset", default="aurora_agent/evals/smoke.json")
        parser.add_argument("--mock", action="store_true")
        parser.add_argument("--user", default=None)

    def handle(self, *args, **options):
        dataset = Path(options["dataset"])
        if not dataset.exists():
            raise CommandError(f"Dataset no encontrado: {dataset}")
        cases = json.loads(dataset.read_text(encoding="utf-8"))
        user = self._get_user(options.get("user"))
        orchestrator = AuroraOperatorOrchestrator(force_mock=options["mock"])
        passed = 0
        failed = []
        last_conversation_id = None
        for case in cases:
            conversation_id = last_conversation_id if case.get("requires_context") else None
            result = orchestrator.run(user, case["message"], conversation_id=conversation_id, page_context={"source": "eval"})
            if result.get("conversation_id"):
                last_conversation_id = result["conversation_id"]
            tools = {item["name"] for item in result.get("tool_calls", [])}
            ok = result.get("status") in case.get("allowed_status", ["ok"])
            expected = set(case.get("expected_tools", []))
            if expected:
                ok = ok and expected.issubset(tools)
            forbidden = set(case.get("forbidden_tools", []))
            if forbidden:
                ok = ok and tools.isdisjoint(forbidden)
            answer = result.get("answer", "")
            missing_text_guard = [
                token for token in case.get("must_not_include", [])
                if token.lower() in answer.lower()
            ]
            if missing_text_guard:
                ok = False
            missing_required_text = [
                token for token in case.get("must_include", [])
                if token.lower() not in answer.lower()
            ]
            if missing_required_text:
                ok = False
            expected_filters = case.get("expected_filters") or {}
            missing_filters = []
            if expected_filters:
                for key, expected_value in expected_filters.items():
                    if not any((call.get("arguments") or {}).get(key) == expected_value for call in result.get("tool_calls", [])):
                        missing_filters.append({key: expected_value})
                if missing_filters:
                    ok = False
            expected_intent = case.get("expected_intent")
            if expected_intent and (result.get("semantic_query") or {}).get("intent") != expected_intent:
                ok = False
            expected_route = case.get("expected_route")
            if expected_route and result.get("route_category") != expected_route:
                ok = False
            if ok:
                passed += 1
            else:
                failed.append({
                    "case": case["message"],
                    "status": result.get("status"),
                    "tools": sorted(tools),
                    "tool_calls": result.get("tool_calls", []),
                    "must_not_include_found": missing_text_guard,
                    "must_include_missing": missing_required_text,
                    "filters_missing": missing_filters,
                    "expected_intent": expected_intent,
                    "actual_intent": (result.get("semantic_query") or {}).get("intent"),
                    "expected_route": expected_route,
                    "actual_route": result.get("route_category"),
                    "answer": answer,
                })
        summary = {"total": len(cases), "passed": passed, "failed": len(failed), "errors": failed}
        self.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2))
        if failed:
            raise CommandError("Agent eval failed")

    def _get_user(self, value):
        User = get_user_model()
        if value:
            lookup = {"id": value} if str(value).isdigit() else {"username": value}
            user = User.objects.filter(**lookup).first()
            if user:
                return user
            raise CommandError(f"Usuario no encontrado: {value}")
        user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if not user:
            user = User.objects.create_user(username="aurora_eval", password=None, is_staff=True)
        return user
