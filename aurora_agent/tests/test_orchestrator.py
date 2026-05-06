from django.test import TestCase, override_settings

from aurora_agent.models import AgentRun, AgentToolCall
from aurora_agent.services.orchestrator import AuroraOperatorOrchestrator
from aurora_agent.tests.factories import create_domain


@override_settings(AI_PROVIDER="mock", AGENT_ENABLE_REAL_LLM=False)
class AgentOrchestratorTests(TestCase):
    def setUp(self):
        self.data = create_domain()

    def test_orchestrator_runs_in_mock(self):
        result = AuroraOperatorOrchestrator(force_mock=True).run(self.data["user"], "Que albaranes puedo preparar hoy?")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["tool_calls"])
        self.assertTrue(AgentRun.objects.exists())
        self.assertTrue(AgentToolCall.objects.exists())

    def test_guardrail_blocks_destructive_request(self):
        result = AuroraOperatorOrchestrator(force_mock=True).run(self.data["user"], "Cambia el stock de todos los productos a 999")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["tool_calls"], [])
