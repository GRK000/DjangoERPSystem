from django.test import TestCase, override_settings

from albaranes.models import Client
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

    def test_count_inactive_customers(self):
        Client.objects.create(
            codi_client="CLI002",
            nom_comercial="Cliente Dos",
            cif="B00000002",
            persona_contacte="Luis",
            telefon="600000001",
            email="inactive@example.com",
            adreca_entrega="Calle 2",
            poblacio="Madrid",
            codi_postal="28002",
            actiu=False,
        )
        result = AuroraOperatorOrchestrator(force_mock=True).run(self.data["user"], "Dime cuantos clientes no activos hay")
        self.assertEqual(result["tool_calls"][0]["name"], "count_customers")
        self.assertEqual(result["tool_calls"][0]["arguments"]["status"], "inactive")
        self.assertIn("Hay 1 cliente no activo", result["answer"])
        self.assertNotIn("Hay 1 cliente activo", result["answer"])

    def test_count_active_customers(self):
        result = AuroraOperatorOrchestrator(force_mock=True).run(self.data["user"], "Dime cuantos clientes activos hay")
        self.assertEqual(result["tool_calls"][0]["arguments"]["status"], "active")
        self.assertIn("Hay 1 cliente activo", result["answer"])

    def test_followup_inactive_customers_uses_previous_customer_context(self):
        orchestrator = AuroraOperatorOrchestrator(force_mock=True)
        first = orchestrator.run(self.data["user"], "Dime cuantos clientes activos hay")
        second = orchestrator.run(self.data["user"], "y no activos?", conversation_id=first["conversation_id"])
        self.assertEqual(second["tool_calls"][0]["name"], "count_customers")
        self.assertEqual(second["tool_calls"][0]["arguments"]["status"], "inactive")
        self.assertIn("clientes no activos", second["answer"])

    def test_inactive_filter_does_not_return_active_answer(self):
        result = AuroraOperatorOrchestrator(force_mock=True).run(self.data["user"], "Dime cuantos clientes no activos hay")
        self.assertNotIn("cliente activo registrado", result["answer"])
