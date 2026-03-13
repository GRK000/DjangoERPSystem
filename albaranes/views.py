from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.db.models import Sum, Count
from django.db import transaction

from .models import (Client, Albara, Categoria, Producte, Magatzem, StockMagatzem, LiniaAlbara, MovimentStock, StockInsuficientError)
from .forms import (ClientForm, AlbaraForm, ReposicioStockForm, LiniaAlbaraProducteForm)

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Benvingut, {username}!')
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
        else:
            messages.error(request, 'Usuari o contrasenya incorrectes.')
    else:
        form = AuthenticationForm()

    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Compte creat correctament!')
            return redirect('home')
        else:
            messages.error(request, 'Error al crear el compte. Revisa els camps.')
    else:
        form = UserCreationForm()

    return render(request, 'auth/register.html', {'form': form})


# home
def home(request):
    context = {
        'total_clients': Client.objects.filter(actiu=True).count(),
        'total_albarans': Albara.objects.count(),
        'total_productes': Producte.objects.filter(actiu=True).count(),
        'albarans_pendents': Albara.objects.filter(estat=Albara.Estat.PENDENT).count(),
    }
    return render(request, "index.html", context)

# clients
def clients_list(request):
    clients = Client.objects.filter(actiu=True).order_by("codi_client")
    return render(request, "clients/list.html", {
        "clients": clients
    })


def client_detail(request, id):
    client = get_object_or_404(Client, pk=id)
    albarans = client.albarans.all().order_by('-data_creacio')[:10]
    return render(request, "clients/details.html", {
        "client": client,
        "albarans": albarans
    })


@login_required()
def client_create(request):
    if request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            messages.success(request, f'Client {client.nom_comercial} creat correctament!')
            return redirect("client_detail", id=client.id)
    else:
        form = ClientForm()

    return render(request, "clients/form.html", {
        "form": form
    })


def client_edit(request, id):
    client = get_object_or_404(Client, pk=id)

    if request.method == "POST":
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, f'Client {client.nom_comercial} actualitzat!')
            return redirect("client_detail", id=client.id)
    else:
        form = ClientForm(instance=client)

    return render(request, "clients/form.html", {
        "form": form,
        "client": client
    })

def cataleg(request):
    categories = Categoria.objects.prefetch_related(
        'productes'
    ).filter(productes__actiu=True).distinct()

    productes = Producte.objects.filter(actiu=True).select_related('categoria')

    return render(request, "cataleg/cataleg.html", {
        "categories": categories,
        "productes": productes,
    })


def cataleg_categoria(request, categoria):
    cat = get_object_or_404(Categoria, nom__iexact=categoria)
    productes = Producte.objects.filter(categoria=cat, actiu=True)
    categories = Categoria.objects.all()

    return render(request, "cataleg/cataleg.html", {
        "categories": categories,
        "productes": productes,
        "categoria_actual": cat,
    })


# albarans
@login_required
def albarans_list(request):
    albarans = Albara.objects.select_related("client", "magatzem", "empleat").all().order_by("-data_creacio")
    return render(request, "albarans/list.html", {
        "albarans": albarans
    })


@login_required
def albara_create(request):
    if request.method == "POST":
        form = AlbaraForm(request.POST)
        if form.is_valid():
            albara = form.save()
            messages.success(request, f'Albarà {albara.numero_albara} creat correctament!')
            return redirect("albara_detail", id=albara.id)
    else:
        form = AlbaraForm()

    return render(request, "albarans/form.html", {
        "form": form
    })


@login_required
def albara_detail(request, id):
    albara = get_object_or_404(Albara.objects.select_related("client", "magatzem", "empleat"), pk=id)
    linies = albara.linies.all()

    # estats possibles per al canvi
    estats_possibles = []
    for estat in Albara.Estat.choices:
        if albara.pot_canviar_estat(estat[0]):
            estats_possibles.append(estat)

    # Comprovar stock baix per les línies
    alertes_stock = []
    if albara.magatzem:
        for linia in linies:
            if linia.producte:
                try:
                    stock = StockMagatzem.objects.get(
                        producte=linia.producte,
                        magatzem=albara.magatzem
                    )
                    if stock.is_stock_baix():
                        alertes_stock.append({
                            'linia': linia,
                            'stock': stock.quantitat
                        })
                except StockMagatzem.DoesNotExist:
                    pass

    return render(request, "albarans/details.html", {
        "albara": albara,
        "linies": linies,
        "estats_possibles": estats_possibles,
        "alertes_stock": alertes_stock,
    })


@login_required
def linia_add(request, id):
    albara = get_object_or_404(Albara, pk=id)

    if not albara.pot_afegir_linies():
        messages.error(request, "No es poden afegir línies en aquest estat")
        return redirect("albara_detail", id=albara.id)

    if request.method == "POST":
        form = LiniaAlbaraProducteForm(request.POST, magatzem=albara.magatzem)
        if form.is_valid():
            linia = form.save(commit=False)
            linia.albara = albara

            # Verificar stock disponible
            if linia.producte and albara.magatzem:
                try:
                    stock = StockMagatzem.objects.get(
                        producte=linia.producte,
                        magatzem=albara.magatzem
                    )
                    if stock.quantitat < linia.quantitat:
                        messages.warning(
                            request,
                            f"Atenció: només hi ha {stock.quantitat} unitats disponibles de {linia.producte.nom}"
                        )
                except StockMagatzem.DoesNotExist:
                    messages.warning(
                        request,
                        f"Atenció: {linia.producte.nom} no té stock al magatzem seleccionat"
                    )

            linia.save()
            messages.success(request, f'Línia afegida: {linia.nom_producte}')
            return redirect("albara_detail", id=albara.id)
    else:
        form = LiniaAlbaraProducteForm(magatzem=albara.magatzem)

    return render(request, "linies/form.html", {
        "form": form,
        "albara": albara
    })


@login_required
def albara_change_state(request, id):
    albara = get_object_or_404(Albara, pk=id)

    if request.method == "POST":
        nou_estat = request.POST.get("nou_estat")

        if nou_estat and albara.pot_canviar_estat(nou_estat):
            try:
                albara.canviar_estat(nou_estat)
                messages.success(request, f'Estat canviat a {albara.get_estat_display()}')
            except ValueError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Transició d'estat no permesa")

    return redirect("albara_detail", id=albara.id)


def consulta_form(request):
    return render(request, "consulta/consulta_form.html")

def consulta_result(request):
    numero_albara = request.GET.get("numero")

    albara = Albara.objects.filter(numero_albara=numero_albara).first()

    if not albara:
        return render(request, "consulta/consulta_resultat.html", {
            "error": "Albarà no trobat"
        })

    mostrar_detall = albara.pot_veure_detall(request.user)

    return render(request, "consulta/consulta_resultat.html", {
        "albara": albara,
        "mostrar_detall": mostrar_detall
    })


def preparacio(request):
    empleat = getattr(request.user, "empleat", None)

    if not empleat:
        messages.error(request, "No ets un empleat.")
        return redirect("home")

    albarans = Albara.objects.filter(
        magatzem=empleat.magatzem_assignat,
        estat__in=[Albara.Estat.PENDENT, Albara.Estat.EN_PREPARACIO]
    ).order_by("-data_creacio")

    # Afegir info de stock per cada línia
    for albara in albarans:
        for linia in albara.linies.all():
            if linia.producte:
                try:
                    stock = StockMagatzem.objects.get(
                        producte=linia.producte,
                        magatzem=empleat.magatzem_assignat
                    )
                    linia.stock_disponible = stock.quantitat
                    linia.ubicacio = stock.ubicacio
                    linia.stock_baix = stock.is_stock_baix()
                except StockMagatzem.DoesNotExist:
                    linia.stock_disponible = 0
                    linia.ubicacio = "N/A"
                    linia.stock_baix = True

    return render(request, "preparacio/preparacio.html", {
        "albarans": albarans,
        "empleat": empleat,
    })


def preparacio_marcar_preparat(request, id):
    empleat = request.user.empleat
    albara = get_object_or_404(Albara, pk=id)

    if albara.magatzem != empleat.magatzem_assignat:
        messages.error(request, "Aquest albarà no pertany al teu magatzem")
        return redirect('preparacio')

    if albara.estat not in [Albara.Estat.PENDENT, Albara.Estat.EN_PREPARACIO]:
        messages.error(request, "L'albarà no es pot marcar com preparat en aquest estat")
        return redirect('preparacio')

    if request.method == "POST":
        try:
            with transaction.atomic():
                for linia in albara.linies.all():
                    if linia.producte:
                        try:
                            stock = StockMagatzem.objects.select_for_update().get(
                                producte=linia.producte,
                                magatzem=albara.magatzem
                            )

                            if stock.quantitat < linia.quantitat:
                                raise StockInsuficientError(
                                    f"Stock insuficient per {linia.producte.nom}: "
                                    f"necessites {linia.quantitat}, només hi ha {stock.quantitat}"
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
                                observacions=f"Preparació albarà {albara.numero_albara}"
                            )

                        except StockMagatzem.DoesNotExist:
                            raise StockInsuficientError(
                                f"No hi ha stock de {linia.producte.nom} al magatzem"
                        )

                albara.estat = Albara.Estat.PREPARAT
                albara.empleat = empleat
                albara.save()

                messages.success(request, f'Albarà {albara.numero_albara} marcat com PREPARAT')

        except StockInsuficientError as e:
            messages.error(request, str(e))
            return redirect('preparacio')

    return redirect('preparacio')


# stock
def stock_list(request):
    empleat = getattr(request.user, "empleat", None)

    if not empleat:
        messages.error(request, "No ets un empleat.")
        return redirect("home")

    magatzem_id = request.GET.get('magatzem')
    categoria_id = request.GET.get('categoria')

    magatzems = Magatzem.objects.all()
    categories = Categoria.objects.all()

    stocks = StockMagatzem.objects.select_related('producte', 'producte__categoria', 'magatzem')

    if magatzem_id:
        stocks = stocks.filter(magatzem_id=magatzem_id)

    if categoria_id:
        stocks = stocks.filter(producte__categoria_id=categoria_id)

    stocks = stocks.order_by('magatzem__nom', 'producte__nom')

    return render(request, "stock/stock_list.html", {
        "stocks": stocks,
        "magatzems": magatzems,
        "categories": categories,
        "magatzem_seleccionat": magatzem_id,
        "categoria_seleccionada": categoria_id,
    })


def stock_reposicio(request):
    if request.method == "POST":
        form = ReposicioStockForm(request.POST)
        if form.is_valid():
            producte = form.cleaned_data['producte']
            magatzem = form.cleaned_data['magatzem']
            quantitat = form.cleaned_data['quantitat']
            ubicacio = form.cleaned_data['ubicacio']

            stock, created = StockMagatzem.objects.get_or_create(
                producte=producte,
                magatzem=magatzem,
                defaults={'quantitat': 0, 'ubicacio': ubicacio}
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
                usuari=request.user,
                observacions="Reposició de stock"
            )

            return redirect('stock_list')
    else:
        form = ReposicioStockForm()

    return render(request, "stock/reposicio.html", {
        "form": form
    })

@login_required
def estadistiques(request):
    albarans_entregats = Albara.objects.filter(
        estat=Albara.Estat.ENTREGAT
    ).select_related('client', 'magatzem')

    total_vendes = albarans_entregats.aggregate(
        total=Sum('total'),
        total_base=Sum('base_imposable'),
        total_iva=Sum('total_iva')
    )

    productes_mes_venuts = LiniaAlbara.objects.filter(
        albara__estat=Albara.Estat.ENTREGAT
    ).values(
        'nom_producte'
    ).annotate(
        total_quantitat=Sum('quantitat'),
        total_vendes=Sum('subtotal')
    ).order_by('-total_quantitat')[:10]

    # Vendes per categoria
    vendes_per_categoria = LiniaAlbara.objects.filter(
        albara__estat=Albara.Estat.ENTREGAT,
        producte__isnull=False
    ).values(
        'producte__categoria__nom'
    ).annotate(
        total_vendes=Sum('subtotal'),
        total_quantitat=Sum('quantitat')
    ).order_by('-total_vendes')

    # top clients per compra
    ranquing_clients = Client.objects.filter(
        albarans__estat=Albara.Estat.ENTREGAT
    ).annotate(
        total_compres=Sum('albarans__total'),
        num_albarans=Count('albarans')
    ).order_by('-total_compres')[:10]

    return render(request, "estadistiques/estadistiques.html", {
        "albarans_entregats": albarans_entregats,
        "total_vendes": total_vendes,
        "productes_mes_venuts": productes_mes_venuts,
        "vendes_per_categoria": vendes_per_categoria,
        "ranquing_clients": ranquing_clients,
    })