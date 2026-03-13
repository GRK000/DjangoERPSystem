from django.contrib import admin
from .models import (
    Albara, Client, LiniaAlbara, Categoria, Producte,
    Magatzem, StockMagatzem, Empleat, MovimentStock
)


class LiniaAlbaraInline(admin.TabularInline):
    model = LiniaAlbara
    extra = 1
    readonly_fields = ("subtotal",)
    autocomplete_fields = ["producte"]


class StockMagatzemInline(admin.TabularInline):
    model = StockMagatzem
    extra = 1


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nom", "descripcio", "requereix_refrigeracio", "temperatura_maxima")
    list_filter = ("requereix_refrigeracio",)
    search_fields = ("nom", "descripcio")


@admin.register(Producte)
class ProducteAdmin(admin.ModelAdmin):
    list_display = (
        "codi",
        "nom",
        "categoria",
        "preu_unitari",
        "unitat_mesura",
        "iva",
        "es_perible",
        "actiu",
    )
    list_filter = ("categoria", "unitat_mesura", "actiu", "es_perible")
    search_fields = ("codi", "nom", "descripcio")
    ordering = ("codi",)
    inlines = [StockMagatzemInline]


@admin.register(Magatzem)
class MagatzemAdmin(admin.ModelAdmin):
    list_display = ("nom", "adreca", "capacitat_maxima", "te_cambra_frio", "responsable")
    list_filter = ("te_cambra_frio",)
    search_fields = ("nom", "adreca", "responsable")


@admin.register(StockMagatzem)
class StockMagatzemAdmin(admin.ModelAdmin):
    list_display = ("producte", "magatzem", "quantitat", "ubicacio", "data_ultima_entrada")
    list_filter = ("magatzem", "data_ultima_entrada")
    search_fields = ("producte__nom", "producte__codi", "magatzem__nom", "ubicacio")
    autocomplete_fields = ["producte", "magatzem"]


@admin.register(Empleat)
class EmpleatAdmin(admin.ModelAdmin):
    list_display = ("codi_empleat", "user", "telefon", "magatzem_assignat", "carrec", "data_alta")
    list_filter = ("carrec", "magatzem_assignat", "data_alta")
    search_fields = ("codi_empleat", "user__username", "user__first_name", "user__last_name")
    autocomplete_fields = ["user", "magatzem_assignat"]


@admin.register(Albara)
class AlbaraAdmin(admin.ModelAdmin):
    list_display = (
        "numero_albara",
        "client",
        "empleat",
        "magatzem",
        "estat",
        "data_creacio",
        "data_entrega_prevista",
        "base_imposable",
        "total_iva",
        "total",
    )
    list_filter = ("estat", "data_creacio", "data_entrega_prevista", "magatzem")
    search_fields = ("numero_albara", "client__nom_comercial", "client__codi_client")
    ordering = ("-data_creacio",)
    readonly_fields = ("data_creacio", "base_imposable", "total_iva", "total")
    autocomplete_fields = ["client", "empleat", "magatzem"]

    inlines = [LiniaAlbaraInline]


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        "codi_client",
        "nom_comercial",
        "cif",
        "persona_contacte",
        "telefon",
        "email",
        "poblacio",
        "actiu",
    )
    list_filter = ("actiu", "poblacio")
    search_fields = (
        "codi_client",
        "nom_comercial",
        "cif",
        "persona_contacte",
        "email",
    )
    ordering = ("codi_client",)


@admin.register(LiniaAlbara)
class LiniaAlbaraAdmin(admin.ModelAdmin):
    list_display = (
        "nom_producte",
        "albara",
        "quantitat",
        "preu_unitari",
        "descompte_percentatge",
        "subtotal",
    )
    search_fields = ("nom_producte", "albara__numero_albara")
    readonly_fields = ("subtotal",)
    autocomplete_fields = ["albara", "producte"]


@admin.register(MovimentStock)
class MovimentStockAdmin(admin.ModelAdmin):
    list_display = ("producte", "magatzem", "tipus", "quantitat", "data", "albara", "usuari")
    list_filter = ("tipus", "magatzem", "data")
    search_fields = ("producte__nom", "producte__codi", "albara__numero_albara")
    readonly_fields = ("data",)
    ordering = ("-data",)
