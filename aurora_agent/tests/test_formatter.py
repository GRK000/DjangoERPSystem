from django.test import TestCase, override_settings

from aurora_agent.services.formatter import format_final_answer
from aurora_agent.services.orchestrator import AuroraOperatorOrchestrator, route_tools
from aurora_agent.tests.factories import create_domain


@override_settings(AI_PROVIDER="mock", AGENT_ENABLE_REAL_LLM=False)
class AgentFormatterTests(TestCase):
    def setUp(self):
        self.data = create_domain()

    def test_count_customers_answer_is_human_readable(self):
        result = AuroraOperatorOrchestrator(force_mock=True).run(self.data["user"], "cuantos clientes hay?")
        self.assertEqual(result["status"], "ok")
        self.assertIn("Hay 1 cliente activo", result["answer"])

    def test_formatter_does_not_expose_raw_tool_json(self):
        answer = format_final_answer(
            "cuantos clientes hay?",
            [{"name": "count_customers", "status": "ok", "result": {"summary": {"active_customers": 1}, "records": [], "evidence": []}}],
        )
        self.assertNotIn("{", answer)
        self.assertNotIn("}", answer)

    def test_formatter_does_not_expose_internal_tool_names(self):
        result = AuroraOperatorOrchestrator(force_mock=True).run(self.data["user"], "cuantos productos hay?")
        self.assertNotIn("count_products", result["answer"])
        self.assertNotIn("get_", result["answer"])

    def test_simple_count_uses_specific_tool_or_extracts_specific_metric(self):
        tools = route_tools("numero de clientes")
        self.assertEqual(tools[0]["name"], "count_customers")

    def test_destructive_requests_still_blocked(self):
        result = AuroraOperatorOrchestrator(force_mock=True).run(self.data["user"], "Marca todos los albaranes como entregados")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["tool_calls"], [])
