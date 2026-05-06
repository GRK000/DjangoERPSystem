import json

from django.test import TestCase

from albaranes.models import Albara
from aurora_agent.tests.factories import create_domain
from aurora_agent.tools.delivery_notes import check_delivery_note_stock, prioritize_delivery_notes
from aurora_agent.tools.operations import get_operational_summary
from aurora_agent.tools.stock import list_low_stock_products


class AgentToolsTests(TestCase):
    def setUp(self):
        self.data = create_domain()

    def test_tools_return_json_serializable(self):
        result = get_operational_summary(self.data["user"], {}, {})
        json.dumps(result)
        self.assertEqual(result["status"], "ok")

    def test_tools_are_read_only(self):
        before = Albara.objects.count()
        list_low_stock_products(self.data["user"], {}, {})
        prioritize_delivery_notes(self.data["user"], {}, {})
        self.assertEqual(Albara.objects.count(), before)

    def test_check_delivery_note_stock_reports_blocker(self):
        result = check_delivery_note_stock(self.data["user"], {"delivery_note_id": self.data["albara"].id}, {})
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["summary"]["preparable"])
        self.assertEqual(result["summary"]["blocked"], 1)
