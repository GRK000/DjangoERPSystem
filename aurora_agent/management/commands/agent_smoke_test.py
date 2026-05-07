import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from aurora_agent.services.orchestrator import AuroraOperatorOrchestrator


class Command(BaseCommand):
    help = "Ejecuta una consulta smoke de Aurora Operator."

    def add_arguments(self, parser):
        parser.add_argument("message", nargs="?", default="Que albaranes puedo preparar hoy?")
        parser.add_argument("--user", dest="user", default=None)
        parser.add_argument("--mock", action="store_true")
        parser.add_argument("--json", action="store_true", dest="as_json")

    def handle(self, *args, **options):
        user = self._get_user(options.get("user"))
        orchestrator = AuroraOperatorOrchestrator(force_mock=options["mock"])
        result = orchestrator.run(user, options["message"], page_context={"source": "cli"})
        if result.get("status") not in {"ok", "blocked", "out_of_scope"}:
            raise CommandError(result.get("answer") or "Agent smoke test failed")
        if options["as_json"]:
            self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            self.stdout.write(f"run_id: {result['run_id']}")
            self.stdout.write("tools: " + ", ".join(item["name"] for item in result.get("tool_calls", [])))
            self.stdout.write(result["answer"])

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
            user = User.objects.create_user(username="aurora_cli", password=None, is_staff=True)
        return user
