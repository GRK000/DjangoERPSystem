from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from albaranes.models import Albara, Client, Producte, StockMagatzem


class SeedDemoDataTests(TestCase):
    def call_seed(self, *args):
        call_command("seed_demo_data", *args, "--quiet", stdout=StringIO())

    def test_seed_creates_demo_data(self):
        self.call_seed("--reset")
        self.assertGreaterEqual(Client.objects.filter(codi_client__startswith="CLI-DEMO-").count(), 6)
        self.assertGreaterEqual(Producte.objects.filter(codi__startswith="PROD-DEMO-").count(), 10)
        self.assertGreaterEqual(Albara.objects.filter(numero_albara__startswith="ALB-DEMO-").count(), 5)

    def test_seed_is_idempotent(self):
        self.call_seed("--reset")
        counts = (
            Client.objects.count(),
            Producte.objects.count(),
            Albara.objects.count(),
        )
        self.call_seed()
        self.assertEqual(counts, (Client.objects.count(), Producte.objects.count(), Albara.objects.count()))

    def test_reset_recreates_demo(self):
        self.call_seed("--reset")
        Client.objects.filter(codi_client="CLI-DEMO-001").update(nom_comercial="Changed")
        self.call_seed("--reset")
        self.assertEqual(Client.objects.get(codi_client="CLI-DEMO-001").nom_comercial, "Cliente Demo Norte")

    def test_seed_generates_blocked_delivery_note_and_low_stock(self):
        self.call_seed("--reset")
        low_stock = StockMagatzem.objects.filter(producte__codi__startswith="PROD-DEMO-", quantitat__lt=10).count()
        self.assertGreaterEqual(low_stock, 3)
        blocked = Albara.objects.get(numero_albara="ALB-DEMO-003")
        self.assertTrue(blocked.linies.filter(producte__stocks__quantitat__lt=1).exists())
