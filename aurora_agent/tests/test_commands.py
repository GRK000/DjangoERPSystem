from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from aurora_agent.tests.factories import create_domain


@override_settings(AI_PROVIDER="mock", AGENT_ENABLE_REAL_LLM=False)
class AgentCommandTests(TestCase):
    def setUp(self):
        create_domain()

    def test_agent_smoke_test_mock(self):
        out = StringIO()
        call_command("agent_smoke_test", "--mock", "Que albaranes puedo preparar hoy?", stdout=out)
        self.assertIn("run_id:", out.getvalue())

    def test_agent_eval_mock(self):
        out = StringIO()
        call_command("agent_eval", "--mock", "--dataset", "aurora_agent/evals/smoke.json", stdout=out)
        self.assertIn('"failed": 0', out.getvalue())
