from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User

from albaranes.models import Albara, Categoria, Client, LiniaAlbara, Magatzem, Producte, StockMagatzem


def create_domain():
    user = User.objects.create_user(username="operator", password="pass", email="operator@example.com")
    other_user = User.objects.create_user(username="other", password="pass")
    category = Categoria.objects.create(nom="Bebidas")
    warehouse = Magatzem.objects.create(nom="Central", adreca="Nave 1", capacitat_maxima=1000, responsable="Ops")
    product = Producte.objects.create(
        codi="BEB001",
        nom="Agua",
        categoria=category,
        preu_unitari=Decimal("1.20"),
        iva=Decimal("0.21"),
        actiu=True,
    )
    StockMagatzem.objects.create(producte=product, magatzem=warehouse, quantitat=5, ubicacio="A-1")
    client = Client.objects.create(
        codi_client="CLI001",
        nom_comercial="Cliente Uno",
        cif="B00000001",
        persona_contacte="Ana",
        telefon="600000000",
        email="client@example.com",
        adreca_entrega="Calle 1",
        poblacio="Madrid",
        codi_postal="28001",
        actiu=True,
    )
    albara = Albara.objects.create(
        numero_albara="ALB-001",
        client=client,
        magatzem=warehouse,
        data_entrega_prevista=date.today(),
        estat=Albara.Estat.PENDENT,
    )
    LiniaAlbara.objects.create(albara=albara, producte=product, nom_producte=product.nom, quantitat=10, preu_unitari=Decimal("1.20"))
    return {"user": user, "other_user": other_user, "product": product, "warehouse": warehouse, "client": client, "albara": albara}
