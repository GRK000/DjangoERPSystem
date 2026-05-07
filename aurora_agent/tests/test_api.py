from django.test import Client as TestClient, TestCase, override_settings
from django.urls import reverse

from aurora_agent.models import AgentConversation, AgentRun
from aurora_agent.tests.factories import create_domain


@override_settings(AI_PROVIDER="mock", AGENT_ENABLE_REAL_LLM=False)
class AgentApiTests(TestCase):
    def setUp(self):
        self.data = create_domain()
        self.client = TestClient()

    def test_api_rejects_unauthenticated_user(self):
        response = self.client.post(reverse("aurora_agent:run"), data='{"message":"hola"}', content_type="application/json")
        self.assertEqual(response.status_code, 401)

    def test_status_works_without_api_key_for_authenticated_user(self):
        self.client.login(username="operator", password="pass")
        response = self.client.get(reverse("aurora_agent:status"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["mock_mode"])

    def test_api_run_authenticated(self):
        self.client.login(username="operator", password="pass")
        response = self.client.post(
            reverse("aurora_agent:run"),
            data='{"message":"Que productos tienen stock bajo?","mock":true}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["tool_calls"])

    def test_conversations_are_isolated_by_user(self):
        self.client.login(username="operator", password="pass")
        own = AgentConversation.objects.create(user=self.data["user"], title="Own")
        AgentConversation.objects.create(user=self.data["other_user"], title="Other")
        response = self.client.get(reverse("aurora_agent:conversation_detail", args=[own.id]))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("aurora_agent:conversations"))
        self.assertEqual(len(response.json()["conversations"]), 1)

    def test_conversation_detail_returns_previous_messages(self):
        self.client.login(username="operator", password="pass")
        run_response = self.client.post(
            reverse("aurora_agent:run"),
            data='{"message":"cuantos clientes hay?","mock":true}',
            content_type="application/json",
        )
        self.assertEqual(run_response.status_code, 200)
        conversation_id = run_response.json()["conversation_id"]

        detail_response = self.client.get(reverse("aurora_agent:conversation_detail", args=[conversation_id]))
        self.assertEqual(detail_response.status_code, 200)
        messages = detail_response.json()["conversation"]["messages"]
        visible_roles = [item["role"] for item in messages if item["role"] in {"user", "assistant"}]
        self.assertEqual(visible_roles, ["user", "assistant"])
        self.assertEqual(messages[-1]["metadata"]["run_id"], run_response.json()["run_id"])
        self.assertTrue(messages[-1]["metadata"]["tool_calls"])

    def test_runs_reject_unauthenticated_user(self):
        response = self.client.get(reverse("aurora_agent:runs"))
        self.assertEqual(response.status_code, 401)

    def test_normal_user_cannot_list_global_runs(self):
        self.client.login(username="operator", password="pass")
        response = self.client.get(reverse("aurora_agent:runs"))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_list_runs_and_detail_has_no_secrets(self):
        self.data["user"].is_staff = True
        self.data["user"].save(update_fields=["is_staff"])
        self.client.login(username="operator", password="pass")
        run_response = self.client.post(
            reverse("aurora_agent:run"),
            data='{"message":"Que productos tienen stock bajo?","mock":true}',
            content_type="application/json",
        )
        run_id = run_response.json()["run_id"]
        response = self.client.get(reverse("aurora_agent:runs"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["runs"])
        detail = self.client.get(reverse("aurora_agent:run_detail", args=[run_id]))
        self.assertEqual(detail.status_code, 200)
        payload = str(detail.json()).lower()
        self.assertNotIn("api_key", payload)
        self.assertNotIn("secret_key", payload)

    def test_user_can_open_own_run_detail_but_not_others(self):
        own_run = AgentRun.objects.create(conversation=AgentConversation.objects.create(user=self.data["user"], title="Own"), user=self.data["user"], input_message="own")
        other_run = AgentRun.objects.create(conversation=AgentConversation.objects.create(user=self.data["other_user"], title="Other"), user=self.data["other_user"], input_message="other")
        self.client.login(username="operator", password="pass")
        self.assertEqual(self.client.get(reverse("aurora_agent:run_detail", args=[own_run.id])).status_code, 200)
        self.assertEqual(self.client.get(reverse("aurora_agent:run_detail", args=[other_run.id])).status_code, 404)
