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
        for case in cases:
            result = orchestrator.run(user, case["message"], page_context={"source": "eval"})
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
            if ok:
                passed += 1
            else:
                failed.append({"case": case["message"], "status": result.get("status"), "tools": sorted(tools), "must_not_include_found": missing_text_guard, "answer": answer})
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
