from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from albaranes.models import (
    Albara,
    Categoria,
    Client,
    Empleat,
    LiniaAlbara,
    Magatzem,
    MovimentStock,
    Producte,
    StockMagatzem,
)


DEMO_PREFIX = "DEMO-"
DEMO_ALB_PREFIX = "ALB-DEMO-"
DEMO_CLIENT_PREFIX = "CLI-DEMO-"
DEMO_PRODUCT_PREFIX = "PROD-DEMO-"


class Command(BaseCommand):
    help = "Crea datos demo reproducibles para Aurora Ops ERP."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Elimina y recrea solo datos demo.")
        parser.add_argument("--quiet", action="store_true", help="Reduce salida por consola.")
        parser.add_argument("--small", action="store_true", help="Crea una demo minima.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset_demo()

        created = self._seed(small=options["small"])
        if not options["quiet"]:
            self.stdout.write(self.style.SUCCESS(
                "Demo Aurora Ops lista: "
                f"{created['clients']} clientes, {created['products']} productos, "
                f"{created['stocks']} stocks, {created['delivery_notes']} albaranes."
            ))

    def _reset_demo(self):
        albarans = Albara.objects.filter(numero_albara__startswith=DEMO_ALB_PREFIX)
        MovimentStock.objects.filter(albara__in=albarans).delete()
        LiniaAlbara.objects.filter(albara__in=albarans).delete()
        albarans.delete()
        MovimentStock.objects.filter(observacions__startswith=DEMO_PREFIX).delete()
        StockMagatzem.objects.filter(producte__codi__startswith=DEMO_PRODUCT_PREFIX).delete()
        Producte.objects.filter(codi__startswith=DEMO_PRODUCT_PREFIX).delete()
        Client.objects.filter(codi_client__startswith=DEMO_CLIENT_PREFIX).delete()
        Empleat.objects.filter(codi_empleat__startswith=DEMO_PREFIX).delete()
        User = get_user_model()
        User.objects.filter(username__startswith="demo_operator").delete()
        Magatzem.objects.filter(nom__startswith="Demo ").delete()
        Categoria.objects.filter(nom__startswith="Demo ").delete()

    def _seed(self, small=False):
        categories = self._categories()
        warehouses = self._warehouses(small)
        employee = self._employee(warehouses[0])
        clients = self._clients(small)
        products = self._products(categories, small)
        stocks = self._stocks(products, warehouses, small)
        movements = self._movements(products, warehouses)
        albarans = self._delivery_notes(clients, products, warehouses[0], employee, small)
        return {
            "clients": len(clients),
            "products": len(products),
            "stocks": stocks,
            "movements": movements,
            "delivery_notes": len(albarans),
        }

    def _categories(self):
        specs = [
            ("Demo Componentes Industriales", "Piezas tecnicas para preparacion y mantenimiento."),
            ("Demo Embalaje Logistico", "Material auxiliar para expedicion."),
        ]
        rows = []
        for name, description in specs:
            category, _ = Categoria.objects.update_or_create(
                nom=name,
                defaults={"descripcio": description, "requereix_refrigeracio": False},
            )
            rows.append(category)
        return rows

    def _warehouses(self, small):
        specs = [
            ("Demo Almacen Norte", "Poligono Norte nave 4", Decimal("1800.00"), "Laura Demo"),
            ("Demo Hub Sur", "Centro logistico Sur muelle 2", Decimal("950.00"), "Marc Demo"),
        ]
        if small:
            specs = specs[:1]
        rows = []
        for name, address, capacity, manager in specs:
            warehouse, _ = Magatzem.objects.update_or_create(
                nom=name,
                defaults={
                    "adreca": address,
                    "capacitat_maxima": capacity,
                    "te_cambra_frio": False,
                    "responsable": manager,
                },
            )
            rows.append(warehouse)
        return rows

    def _employee(self, warehouse):
        User = get_user_model()
        user, _ = User.objects.update_or_create(
            username="demo_operator",
            defaults={"email": "demo.operator@aurora.local", "first_name": "Demo", "last_name": "Operator", "is_staff": True},
        )
        user.set_password("demo")
        user.save(update_fields=["password", "email", "first_name", "last_name", "is_staff"])
        employee, _ = Empleat.objects.update_or_create(
            codi_empleat=f"{DEMO_PREFIX}OPS-01",
            defaults={"user": user, "telefon": "600100100", "magatzem_assignat": warehouse, "carrec": "Preparador demo"},
        )
        return employee

    def _clients(self, small):
        specs = [
            ("001", "Cliente Demo Norte", True, "B66000001", "Aina Norte"),
            ("002", "Cliente Demo Sur", True, "B66000002", "Bruno Sur"),
            ("003", "Cliente Demo Levante", True, "B66000003", "Clara Levante"),
            ("004", "Cliente Demo Centro", True, "B66000004", "Dani Centro"),
            ("005", "Cliente Demo Inactivo", False, "B66000005", "Eva Inactiva"),
            ("006", "Cliente Demo Pausado", False, "B66000006", "Ferran Pausado"),
        ]
        if small:
            specs = specs[:3] + specs[4:5]
        rows = []
        for suffix, name, active, cif, contact in specs:
            client, _ = Client.objects.update_or_create(
                codi_client=f"{DEMO_CLIENT_PREFIX}{suffix}",
                defaults={
                    "nom_comercial": name,
                    "cif": cif,
                    "persona_contacte": contact,
                    "telefon": f"600200{suffix}",
                    "email": f"cliente.demo.{suffix}@aurora.local",
                    "adreca_entrega": f"Calle Demo {suffix}",
                    "poblacio": "Barcelona",
                    "codi_postal": f"080{suffix.zfill(2)}",
                    "actiu": active,
                },
            )
            rows.append(client)
        return rows

    def _products(self, categories, small):
        active_specs = [
            ("001", "Producto Demo Rodamiento 6204", Decimal("7.40"), 2),
            ("002", "Producto Demo Tornillo M8", Decimal("0.18"), 4),
            ("003", "Producto Demo Junta EPDM", Decimal("1.90"), 1),
            ("004", "Producto Demo Sensor inductivo", Decimal("18.50"), 0),
            ("005", "Producto Demo Correa A32", Decimal("12.20"), 24),
            ("006", "Producto Demo Caja reforzada", Decimal("2.80"), 40),
            ("007", "Producto Demo Etiqueta termica", Decimal("0.05"), 120),
            ("008", "Producto Demo Film tecnico", Decimal("8.75"), 32),
            ("009", "Producto Demo Valvula 1/2", Decimal("14.10"), 18),
            ("010", "Producto Demo Guia lineal", Decimal("31.90"), 15),
        ]
        inactive_specs = [
            ("011", "Producto Demo Obsoleto A", Decimal("5.00"), 0, False),
            ("012", "Producto Demo Obsoleto B", Decimal("9.50"), 0, False),
        ]
        specs = [(code, name, price, qty, True) for code, name, price, qty in active_specs] + inactive_specs
        if small:
            specs = specs[:6] + specs[-1:]
        rows = []
        for index, (suffix, name, price, _qty, active) in enumerate(specs):
            product, _ = Producte.objects.update_or_create(
                codi=f"{DEMO_PRODUCT_PREFIX}{suffix}",
                defaults={
                    "nom": name,
                    "descripcio": f"Referencia demo para Aurora Ops: {name}.",
                    "categoria": categories[index % len(categories)],
                    "preu_unitari": price,
                    "unitat_mesura": Producte.UnitatMesura.UNITAT,
                    "iva": Decimal("0.21"),
                    "es_perible": False,
                    "actiu": active,
                },
            )
            product.demo_quantity = _qty
            rows.append(product)
        return rows

    def _stocks(self, products, warehouses, small):
        count = 0
        for index, product in enumerate(products):
            quantity = getattr(product, "demo_quantity", 10)
            warehouse = warehouses[index % len(warehouses)]
            StockMagatzem.objects.update_or_create(
                producte=product,
                magatzem=warehouse,
                defaults={"quantitat": quantity, "ubicacio": f"D-{index + 1:02d}"},
            )
            count += 1
            if not small and len(warehouses) > 1 and product.actiu and quantity > 0:
                StockMagatzem.objects.update_or_create(
                    producte=product,
                    magatzem=warehouses[0],
                    defaults={"quantitat": quantity, "ubicacio": f"N-{index + 1:02d}"},
                )
        return count

    def _movements(self, products, warehouses):
        count = 0
        for product in products[:8]:
            movement, created = MovimentStock.objects.get_or_create(
                producte=product,
                magatzem=warehouses[0],
                tipus=MovimentStock.TipusMoviment.ENTRADA,
                quantitat=max(getattr(product, "demo_quantity", 10), 1),
                observacions=f"{DEMO_PREFIX}entrada inicial reproducible",
            )
            count += int(created or bool(movement.id))
        return count

    def _delivery_notes(self, clients, products, warehouse, employee, small):
        today = timezone.localdate()
        specs = [
            ("001", clients[0], Albara.Estat.PENDENT, [(products[4], 3), (products[5], 4)], "Preparable hoy"),
            ("002", clients[1], Albara.Estat.PENDENT, [(products[6], 20), (products[8], 2)], "Preparable prioridad media"),
            ("003", clients[2], Albara.Estat.PENDENT, [(products[0], 6), (products[3], 2)], "Bloqueado por stock"),
            ("004", clients[3 if len(clients) > 3 else 0], Albara.Estat.EN_PREPARACIO, [(products[9], 1), (products[5], 3)], "En preparacion"),
            ("005", clients[0], Albara.Estat.ENTREGAT, [(products[4], 2), (products[8], 2), (products[6], 10)], "Entregado demo"),
        ]
        if small:
            specs = specs[:3]
        rows = []
        for suffix, client, status, lines, notes in specs:
            albara, _ = Albara.objects.update_or_create(
                numero_albara=f"{DEMO_ALB_PREFIX}{suffix}",
                defaults={
                    "client": client,
                    "empleat": employee,
                    "magatzem": warehouse,
                    "data_entrega_prevista": today + timedelta(days=1),
                    "estat": status,
                    "observacions": f"{DEMO_PREFIX}{notes}",
                    "signatura_client": "Cliente Demo Norte" if status == Albara.Estat.ENTREGAT else "",
                },
            )
            LiniaAlbara.objects.filter(albara=albara).delete()
            for product, quantity in lines:
                LiniaAlbara.objects.create(
                    albara=albara,
                    producte=product,
                    nom_producte=product.nom,
                    quantitat=quantity,
                    preu_unitari=product.preu_unitari,
                    iva=product.iva,
                )
            albara.calcular_totals()
            if status == Albara.Estat.ENTREGAT:
                for line in albara.linies.all():
                    MovimentStock.objects.get_or_create(
                        producte=line.producte,
                        magatzem=warehouse,
                        tipus=MovimentStock.TipusMoviment.SORTIDA,
                        quantitat=line.quantitat,
                        albara=albara,
                        observacions=f"{DEMO_PREFIX}salida por entrega demo",
                    )
            rows.append(albara)
        return rows
