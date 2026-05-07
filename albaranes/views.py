from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.messages import get_messages
from django.db import transaction
from django.db.models import Count, Sum
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    AlbaraForm,
    ClientForm,
    LiniaAlbaraProducteForm,
    ReposicioStockForm,
)
from .models import (
    Albara,
    Categoria,
    Client,
    LiniaAlbara,
    Magatzem,
    MovimentStock,
    Producte,
    StockInsuficientError,
    StockMagatzem,
)


STATUS_LABELS = {
    Albara.Estat.PENDENT: "Pendent",
    Albara.Estat.EN_PREPARACIO: "En preparacio",
    Albara.Estat.PREPARAT: "Preparat",
    Albara.Estat.ENVIAT: "Enviat",
    Albara.Estat.ENTREGAT: "Entregat",
    Albara.Estat.CANCELAT: "Cancel.lat",
}


def _money(value):
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return value


def _date(value):
    return value.isoformat() if value else None


def _datetime(value):
    if not value:
        return None
    return timezone.localtime(value).isoformat()


def _form_errors(form):
    return {
        field: [error["message"] for error in errors]
        for field, errors in form.errors.get_json_data().items()
    }


def _post_values(request, fields):
    return {field: request.POST.get(field, "") for field in fields}


def _client(client):
    return {
        "id": client.id,
        "codi_client": client.codi_client,
        "nom_comercial": client.nom_comercial,
        "cif": client.cif,
        "persona_contacte": client.persona_contacte,
        "telefon": client.telefon,
        "email": client.email,
        "adreca_entrega": client.adreca_entrega,
        "poblacio": client.poblacio,
        "codi_postal": client.codi_postal,
        "actiu": client.actiu,
    }


def _category(category):
    return {
        "id": category.id,
        "nom": category.nom,
        "descripcio": category.descripcio or "",
        "requereix_refrigeracio": category.requereix_refrigeracio,
        "temperatura_maxima": _money(category.temperatura_maxima),
    }


def _warehouse(warehouse):
    if not warehouse:
        return None
    return {
        "id": warehouse.id,
        "nom": warehouse.nom,
        "adreca": warehouse.adreca,
        "capacitat_maxima": _money(warehouse.capacitat_maxima),
        "te_cambra_frio": warehouse.te_cambra_frio,
        "responsable": warehouse.responsable,
    }


def _product(product, include_stock=True):
    data = {
        "id": product.id,
        "codi": product.codi,
        "nom": product.nom,
        "descripcio": product.descripcio or "",
        "categoria": _category(product.categoria),
        "preu_unitari": _money(product.preu_unitari),
        "unitat_mesura": product.unitat_mesura,
        "iva": _money(product.iva),
        "es_perible": product.es_perible,
        "imatge_url": product.imatge_url or "",
        "actiu": product.actiu,
    }
    if include_stock:
        data["stock_total"] = product.get_stock_total()
    return data


def _employee(employee):
    if not employee:
        return None
    return {
        "id": employee.id,
        "codi_empleat": employee.codi_empleat,
        "nom": employee.user.get_full_name() or employee.user.username,
        "carrec": employee.carrec,
        "magatzem_assignat": _warehouse(employee.magatzem_assignat),
    }


def _line(line):
    return {
        "id": line.id,
        "producte": _product(line.producte, include_stock=False) if line.producte else None,
        "nom_producte": line.nom_producte,
        "quantitat": line.quantitat,
        "preu_unitari": _money(line.preu_unitari),
        "iva": _money(line.iva),
        "descompte_percentatge": _money(line.descompte_percentatge),
        "subtotal": _money(line.subtotal),
        "observacions": line.observacions or "",
        "stock_disponible": getattr(line, "stock_disponible", None),
        "ubicacio": getattr(line, "ubicacio", ""),
        "stock_baix": getattr(line, "stock_baix", False),
    }


def _albara(albara, include_lines=False):
    data = {
        "id": albara.id,
        "numero_albara": albara.numero_albara,
        "client": _client(albara.client),
        "empleat": _employee(albara.empleat),
        "magatzem": _warehouse(albara.magatzem),
        "data_creacio": _datetime(albara.data_creacio),
        "data_entrega_prevista": _date(albara.data_entrega_prevista),
        "estat": albara.estat,
        "estat_label": STATUS_LABELS.get(albara.estat, albara.estat),
        "base_imposable": _money(albara.base_imposable),
        "total_iva": _money(albara.total_iva),
        "total": _money(albara.total),
        "observacions": albara.observacions or "",
        "signatura_client": albara.signatura_client or "",
        "pot_afegir_linies": albara.pot_afegir_linies(),
    }
    if include_lines:
        data["linies"] = [_line(line) for line in albara.linies.all()]
    return data


def _stock(stock):
    return {
        "id": stock.id,
        "producte": _product(stock.producte, include_stock=False),
        "magatzem": _warehouse(stock.magatzem),
        "quantitat": stock.quantitat,
        "data_ultima_entrada": _date(stock.data_ultima_entrada),
        "ubicacio": stock.ubicacio,
        "stock_baix": stock.is_stock_baix(),
    }


def _select_options(model, label_attr="nom"):
    return [
        {"value": item.id, "label": getattr(item, label_attr)}
        for item in model.objects.all()
    ]


def _command_items(user):
    items = [
        {"type": "Pantalla", "label": "Dashboard operatiu", "href": "/"},
        {"type": "Pantalla", "label": "Clients", "href": "/clients/"},
        {"type": "Pantalla", "label": "Cataleg", "href": "/cataleg/"},
        {"type": "Pantalla", "label": "Consulta albara", "href": "/consulta/"},
    ]
    if user.is_authenticated:
        items.extend(
            [
                {"type": "Pantalla", "label": "Albarans", "href": "/albarans/"},
                {"type": "Pantalla", "label": "Preparacio", "href": "/preparacio/"},
                {"type": "Pantalla", "label": "Stock", "href": "/stock/"},
                {"type": "Pantalla", "label": "Estadistiques", "href": "/estadistiques/"},
                {"type": "Pantalla", "label": "Agent Runs", "href": "/agent-runs/"},
            ]
        )

    items.extend(
        {"type": "Client", "label": client.nom_comercial, "href": f"/clients/{client.id}/"}
        for client in Client.objects.filter(actiu=True).order_by("nom_comercial")[:20]
    )
    items.extend(
        {"type": "Producte", "label": f"{product.codi} - {product.nom}", "href": "/cataleg/"}
        for product in Producte.objects.filter(actiu=True).order_by("codi")[:20]
    )
    if user.is_authenticated:
        items.extend(
            {
                "type": "Albara",
                "label": albara.numero_albara,
                "href": f"/albarans/{albara.id}/",
            }
            for albara in Albara.objects.order_by("-data_creacio")[:20]
        )
    return items


def render_app(request, page, payload=None, status=200):
    data = {
        "page": page,
        "payload": payload or {},
        "csrfToken": get_token(request),
        "user": {
            "isAuthenticated": request.user.is_authenticated,
            "username": request.user.username if request.user.is_authenticated else "",
            "isStaff": request.user.is_staff if request.user.is_authenticated else False,
        },
        "messages": [
            {"tags": message.tags, "message": str(message)}
            for message in get_messages(request)
        ],
        "commandItems": _command_items(request.user),
    }
    return render(request, "app.html", {"initial_data": data}, status=status)


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    next_url = request.GET.get("next", "home")
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Benvingut, {username}!")
                return redirect(request.GET.get("next", "home"))
        messages.error(request, "Usuari o contrasenya incorrectes.")
        return render_app(
            request,
            "auth_login",
            {
                "next": next_url,
                "values": _post_values(request, ["username"]),
                "errors": _form_errors(form),
            },
        )

    return render_app(request, "auth_login", {"next": next_url, "values": {}, "errors": {}})


def logout_view(request):
    logout(request)
    return redirect("home")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Compte creat correctament!")
            return redirect("home")
        messages.error(request, "Error al crear el compte. Revisa els camps.")
        return render_app(
            request,
            "auth_register",
            {
                "values": _post_values(request, ["username"]),
                "errors": _form_errors(form),
            },
        )

    return render_app(request, "auth_register", {"values": {}, "errors": {}})


def home(request):
    status_counts = {
        row["estat"]: row["total"]
        for row in Albara.objects.values("estat").annotate(total=Count("id"))
    }
    delivered = Albara.objects.filter(estat=Albara.Estat.ENTREGAT).aggregate(total=Sum("total"))
    recent_albarans = Albara.objects.select_related("client", "magatzem").order_by("-data_creacio")[:6]
    stock_alerts = StockMagatzem.objects.select_related(
        "producte", "producte__categoria", "magatzem"
    ).filter(quantitat__lt=10).order_by("quantitat")[:6]

    return render_app(
        request,
        "home",
        {
            "stats": {
                "total_clients": Client.objects.filter(actiu=True).count(),
                "total_albarans": Albara.objects.count(),
                "total_productes": Producte.objects.filter(actiu=True).count(),
                "albarans_pendents": status_counts.get(Albara.Estat.PENDENT, 0),
                "vendes_entregades": _money(delivered["total"]),
            },
            "status_counts": status_counts,
            "recent_albarans": [_albara(albara) for albara in recent_albarans],
            "stock_alerts": [_stock(stock) for stock in stock_alerts],
        },
    )


def clients_list(request):
    clients = Client.objects.filter(actiu=True).order_by("codi_client")
    return render_app(request, "clients_list", {"clients": [_client(client) for client in clients]})


def client_detail(request, id):
    client = get_object_or_404(Client, pk=id)
    albarans = client.albarans.select_related("client", "magatzem").order_by("-data_creacio")[:10]
    return render_app(
        request,
        "client_detail",
        {"client": _client(client), "albarans": [_albara(albara) for albara in albarans]},
    )


def _client_form_payload(client=None, request=None, form=None):
    fields = [
        "codi_client",
        "nom_comercial",
        "cif",
        "persona_contacte",
        "telefon",
        "email",
        "adreca_entrega",
        "poblacio",
        "codi_postal",
        "actiu",
    ]
    values = _client(client) if client else {"actiu": True}
    if request and request.method == "POST":
        values.update(_post_values(request, fields))
        values["actiu"] = request.POST.get("actiu") == "on"
    return {
        "client": _client(client) if client else None,
        "values": values,
        "errors": _form_errors(form) if form else {},
    }


@login_required()
def client_create(request):
    if request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            messages.success(request, f"Client {client.nom_comercial} creat correctament!")
            return redirect("client_detail", id=client.id)
        return render_app(request, "client_form", _client_form_payload(request=request, form=form))

    return render_app(request, "client_form", _client_form_payload())


def client_edit(request, id):
    client = get_object_or_404(Client, pk=id)

    if request.method == "POST":
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, f"Client {client.nom_comercial} actualitzat!")
            return redirect("client_detail", id=client.id)
        return render_app(
            request,
            "client_form",
            _client_form_payload(client=client, request=request, form=form),
        )

    return render_app(request, "client_form", _client_form_payload(client=client))


def cataleg(request):
    categories = Categoria.objects.prefetch_related("productes").filter(productes__actiu=True).distinct()
    productes = Producte.objects.filter(actiu=True).select_related("categoria").prefetch_related("stocks")
    return render_app(
        request,
        "cataleg",
        {
            "categories": [_category(category) for category in categories],
            "productes": [_product(product) for product in productes],
            "categoria_actual": None,
        },
    )


def cataleg_categoria(request, categoria):
    cat = get_object_or_404(Categoria, nom__iexact=categoria)
    productes = Producte.objects.filter(categoria=cat, actiu=True).select_related("categoria").prefetch_related("stocks")
    categories = Categoria.objects.all()
    return render_app(
        request,
        "cataleg",
        {
            "categories": [_category(category) for category in categories],
            "productes": [_product(product) for product in productes],
            "categoria_actual": _category(cat),
        },
    )


@login_required
def albarans_list(request):
    albarans = Albara.objects.select_related("client", "magatzem", "empleat").all().order_by("-data_creacio")
    return render_app(request, "albarans_list", {"albarans": [_albara(albara) for albara in albarans]})


def _albara_form_payload(request=None, form=None, albara=None):
    fields = ["numero_albara", "client", "magatzem", "data_entrega_prevista", "estat", "observacions"]
    values = {
        "numero_albara": "",
        "client": "",
        "magatzem": "",
        "data_entrega_prevista": "",
        "estat": Albara.Estat.PENDENT,
        "observacions": "",
    }
    if albara:
        values.update(
            {
                "numero_albara": albara.numero_albara,
                "client": albara.client_id,
                "magatzem": albara.magatzem_id or "",
                "data_entrega_prevista": _date(albara.data_entrega_prevista),
                "estat": albara.estat,
                "observacions": albara.observacions or "",
            }
        )
    if request and request.method == "POST":
        values.update(_post_values(request, fields))
    return {
        "albara": _albara(albara) if albara else None,
        "values": values,
        "errors": _form_errors(form) if form else {},
        "options": {
            "clients": _select_options(Client, "nom_comercial"),
            "magatzems": _select_options(Magatzem, "nom"),
            "estats": [{"value": key, "label": STATUS_LABELS.get(key, label)} for key, label in Albara.Estat.choices],
        },
    }


@login_required
def albara_create(request):
    if request.method == "POST":
        form = AlbaraForm(request.POST)
        if form.is_valid():
            albara = form.save()
            messages.success(request, f"Albara {albara.numero_albara} creat correctament!")
            return redirect("albara_detail", id=albara.id)
        return render_app(request, "albara_form", _albara_form_payload(request=request, form=form))

    return render_app(request, "albara_form", _albara_form_payload())


@login_required
def albara_detail(request, id):
    albara = get_object_or_404(
        Albara.objects.select_related("client", "magatzem", "empleat").prefetch_related("linies__producte__categoria"),
        pk=id,
    )
    linies = albara.linies.all()
    estats_possibles = [
        {"value": value, "label": STATUS_LABELS.get(value, label)}
        for value, label in Albara.Estat.choices
        if albara.pot_canviar_estat(value)
    ]

    alertes_stock = []
    if albara.magatzem:
        for linia in linies:
            if linia.producte:
                try:
                    stock = StockMagatzem.objects.get(producte=linia.producte, magatzem=albara.magatzem)
                    if stock.is_stock_baix():
                        alertes_stock.append({"linia": _line(linia), "stock": stock.quantitat})
                except StockMagatzem.DoesNotExist:
                    pass

    return render_app(
        request,
        "albara_detail",
        {
            "albara": _albara(albara, include_lines=True),
            "estats_possibles": estats_possibles,
            "alertes_stock": alertes_stock,
        },
    )


def _line_form_payload(albara, request=None, form=None):
    fields = ["producte", "nom_producte", "quantitat", "preu_unitari", "iva", "descompte_percentatge", "observacions"]
    products = Producte.objects.filter(actiu=True).select_related("categoria")
    if albara.magatzem:
        ids = StockMagatzem.objects.filter(magatzem=albara.magatzem, quantitat__gt=0).values_list("producte_id", flat=True)
        products = products.filter(id__in=ids)
    values = {
        "producte": "",
        "nom_producte": "",
        "quantitat": 1,
        "preu_unitari": "",
        "iva": "0.21",
        "descompte_percentatge": "0",
        "observacions": "",
    }
    if request and request.method == "POST":
        values.update(_post_values(request, fields))
    return {
        "albara": _albara(albara),
        "values": values,
        "errors": _form_errors(form) if form else {},
        "productes": [_product(product, include_stock=False) for product in products],
    }


@login_required
def linia_add(request, id):
    albara = get_object_or_404(Albara, pk=id)

    if not albara.pot_afegir_linies():
        messages.error(request, "No es poden afegir linies en aquest estat")
        return redirect("albara_detail", id=albara.id)

    if request.method == "POST":
        form = LiniaAlbaraProducteForm(request.POST, magatzem=albara.magatzem)
        if form.is_valid():
            linia = form.save(commit=False)
            linia.albara = albara

            if linia.producte and albara.magatzem:
                try:
                    stock = StockMagatzem.objects.get(producte=linia.producte, magatzem=albara.magatzem)
                    if stock.quantitat < linia.quantitat:
                        messages.warning(
                            request,
                            f"Atencio: nomes hi ha {stock.quantitat} unitats disponibles de {linia.producte.nom}",
                        )
                except StockMagatzem.DoesNotExist:
                    messages.warning(request, f"Atencio: {linia.producte.nom} no te stock al magatzem seleccionat")

            linia.save()
            messages.success(request, f"Linia afegida: {linia.nom_producte}")
            return redirect("albara_detail", id=albara.id)
        return render_app(request, "linia_form", _line_form_payload(albara, request=request, form=form))

    return render_app(request, "linia_form", _line_form_payload(albara))


@login_required
def albara_change_state(request, id):
    albara = get_object_or_404(Albara, pk=id)

    if request.method == "POST":
        nou_estat = request.POST.get("nou_estat")
        if nou_estat and albara.pot_canviar_estat(nou_estat):
            try:
                albara.canviar_estat(nou_estat)
                messages.success(request, f"Estat canviat a {STATUS_LABELS.get(albara.estat, albara.estat)}")
            except ValueError as error:
                messages.error(request, str(error))
        else:
            messages.error(request, "Transicio d'estat no permesa")

    return redirect("albara_detail", id=albara.id)


def consulta_form(request):
    return render_app(request, "consulta_form", {})


@login_required
def agent_runs(request):
    if not request.user.is_staff:
        messages.error(request, "Solo staff puede consultar trazas del agente.")
        return redirect("home")
    return render_app(request, "agent_runs", {})


def consulta_result(request):
    numero_albara = request.GET.get("numero")
    albara = Albara.objects.filter(numero_albara=numero_albara).select_related("client", "magatzem", "empleat").first()

    if not albara:
        return render_app(request, "consulta_result", {"error": "Albara no trobat", "numero": numero_albara})

    return render_app(
        request,
        "consulta_result",
        {
            "albara": _albara(albara, include_lines=albara.pot_veure_detall(request.user)),
            "mostrar_detall": albara.pot_veure_detall(request.user),
        },
    )


def preparacio(request):
    empleat = getattr(request.user, "empleat", None)

    if not empleat:
        messages.error(request, "No ets un empleat.")
        return redirect("home")

    albarans = Albara.objects.filter(
        magatzem=empleat.magatzem_assignat,
        estat__in=[Albara.Estat.PENDENT, Albara.Estat.EN_PREPARACIO],
    ).select_related("client", "magatzem", "empleat").prefetch_related("linies__producte__categoria").order_by("-data_creacio")

    for albara in albarans:
        for linia in albara.linies.all():
            if linia.producte:
                try:
                    stock = StockMagatzem.objects.get(producte=linia.producte, magatzem=empleat.magatzem_assignat)
                    linia.stock_disponible = stock.quantitat
                    linia.ubicacio = stock.ubicacio
                    linia.stock_baix = stock.is_stock_baix()
                except StockMagatzem.DoesNotExist:
                    linia.stock_disponible = 0
                    linia.ubicacio = "N/A"
                    linia.stock_baix = True

    return render_app(
        request,
        "preparacio",
        {"albarans": [_albara(albara, include_lines=True) for albara in albarans], "empleat": _employee(empleat)},
    )


def preparacio_marcar_preparat(request, id):
    empleat = request.user.empleat
    albara = get_object_or_404(Albara, pk=id)

    if albara.magatzem != empleat.magatzem_assignat:
        messages.error(request, "Aquest albara no pertany al teu magatzem")
        return redirect("preparacio")

    if albara.estat not in [Albara.Estat.PENDENT, Albara.Estat.EN_PREPARACIO]:
        messages.error(request, "L'albara no es pot marcar com preparat en aquest estat")
        return redirect("preparacio")

    if request.method == "POST":
        try:
            with transaction.atomic():
                for linia in albara.linies.all():
                    if linia.producte:
                        try:
                            stock = StockMagatzem.objects.select_for_update().get(
                                producte=linia.producte,
                                magatzem=albara.magatzem,
                            )
                            if stock.quantitat < linia.quantitat:
                                raise StockInsuficientError(
                                    f"Stock insuficient per {linia.producte.nom}: necessites {linia.quantitat}, nomes hi ha {stock.quantitat}"
                                )

                            stock.quantitat -= linia.quantitat
                            stock.save()

                            MovimentStock.objects.create(
                                producte=linia.producte,
                                magatzem=albara.magatzem,
                                tipus=MovimentStock.TipusMoviment.SORTIDA,
                                quantitat=linia.quantitat,
                                albara=albara,
                                usuari=request.user,
                                observacions=f"Preparacio albara {albara.numero_albara}",
                            )
                        except StockMagatzem.DoesNotExist:
                            raise StockInsuficientError(f"No hi ha stock de {linia.producte.nom} al magatzem")

                albara.estat = Albara.Estat.PREPARAT
                albara.empleat = empleat
                albara.save()
                messages.success(request, f"Albara {albara.numero_albara} marcat com PREPARAT")

        except StockInsuficientError as error:
            messages.error(request, str(error))
            return redirect("preparacio")

    return redirect("preparacio")


def stock_list(request):
    empleat = getattr(request.user, "empleat", None)

    if not empleat:
        messages.error(request, "No ets un empleat.")
        return redirect("home")

    magatzem_id = request.GET.get("magatzem")
    categoria_id = request.GET.get("categoria")

    magatzems = Magatzem.objects.all()
    categories = Categoria.objects.all()
    stocks = StockMagatzem.objects.select_related("producte", "producte__categoria", "magatzem")

    if magatzem_id:
        stocks = stocks.filter(magatzem_id=magatzem_id)
    if categoria_id:
        stocks = stocks.filter(producte__categoria_id=categoria_id)

    stocks = stocks.order_by("magatzem__nom", "producte__nom")

    return render_app(
        request,
        "stock_list",
        {
            "stocks": [_stock(stock) for stock in stocks],
            "magatzems": [_warehouse(magatzem) for magatzem in magatzems],
            "categories": [_category(category) for category in categories],
            "magatzem_seleccionat": magatzem_id or "",
            "categoria_seleccionada": categoria_id or "",
        },
    )


def _stock_reposicio_payload(request=None, form=None):
    fields = ["producte", "magatzem", "quantitat", "ubicacio"]
    values = {"producte": "", "magatzem": "", "quantitat": 1, "ubicacio": ""}
    if request and request.method == "POST":
        values.update(_post_values(request, fields))
    return {
        "values": values,
        "errors": _form_errors(form) if form else {},
        "productes": [_product(product, include_stock=False) for product in Producte.objects.filter(actiu=True).select_related("categoria")],
        "magatzems": [_warehouse(magatzem) for magatzem in Magatzem.objects.all()],
    }


def stock_reposicio(request):
    if request.method == "POST":
        form = ReposicioStockForm(request.POST)
        if form.is_valid():
            producte = form.cleaned_data["producte"]
            magatzem = form.cleaned_data["magatzem"]
            quantitat = form.cleaned_data["quantitat"]
            ubicacio = form.cleaned_data["ubicacio"]

            stock, _created = StockMagatzem.objects.get_or_create(
                producte=producte,
                magatzem=magatzem,
                defaults={"quantitat": 0, "ubicacio": ubicacio},
            )

            stock.quantitat += quantitat
            if ubicacio:
                stock.ubicacio = ubicacio
            stock.save()

            MovimentStock.objects.create(
                producte=producte,
                magatzem=magatzem,
                tipus=MovimentStock.TipusMoviment.ENTRADA,
                quantitat=quantitat,
                usuari=request.user if request.user.is_authenticated else None,
                observacions="Reposicio de stock",
            )
            messages.success(request, f"Reposicio registrada: {quantitat} unitats de {producte.nom}")
            return redirect("stock_list")
        return render_app(request, "stock_reposicio", _stock_reposicio_payload(request=request, form=form))

    return render_app(request, "stock_reposicio", _stock_reposicio_payload())


@login_required
def estadistiques(request):
    albarans_entregats = Albara.objects.filter(estat=Albara.Estat.ENTREGAT).select_related("client", "magatzem")
    total_vendes = albarans_entregats.aggregate(total=Sum("total"), total_base=Sum("base_imposable"), total_iva=Sum("total_iva"))

    productes_mes_venuts = LiniaAlbara.objects.filter(albara__estat=Albara.Estat.ENTREGAT).values("nom_producte").annotate(
        total_quantitat=Sum("quantitat"),
        total_vendes=Sum("subtotal"),
    ).order_by("-total_quantitat")[:10]

    vendes_per_categoria = LiniaAlbara.objects.filter(
        albara__estat=Albara.Estat.ENTREGAT,
        producte__isnull=False,
    ).values("producte__categoria__nom").annotate(
        total_vendes=Sum("subtotal"),
        total_quantitat=Sum("quantitat"),
    ).order_by("-total_vendes")

    ranquing_clients = Client.objects.filter(albarans__estat=Albara.Estat.ENTREGAT).annotate(
        total_compres=Sum("albarans__total"),
        num_albarans=Count("albarans"),
    ).order_by("-total_compres")[:10]

    return render_app(
        request,
        "estadistiques",
        {
            "albarans_entregats": [_albara(albara) for albara in albarans_entregats],
            "total_vendes": {
                "total": _money(total_vendes["total"]),
                "total_base": _money(total_vendes["total_base"]),
                "total_iva": _money(total_vendes["total_iva"]),
            },
            "productes_mes_venuts": [
                {
                    "nom_producte": row["nom_producte"],
                    "total_quantitat": row["total_quantitat"],
                    "total_vendes": _money(row["total_vendes"]),
                }
                for row in productes_mes_venuts
            ],
            "vendes_per_categoria": [
                {
                    "categoria": row["producte__categoria__nom"] or "Sense categoria",
                    "total_quantitat": row["total_quantitat"],
                    "total_vendes": _money(row["total_vendes"]),
                }
                for row in vendes_per_categoria
            ],
            "ranquing_clients": [
                {
                    **_client(client),
                    "total_compres": _money(client.total_compres),
                    "num_albarans": client.num_albarans,
                }
                for client in ranquing_clients
            ],
        },
    )
