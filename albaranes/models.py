from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from decimal import Decimal

# Excepció stock insuficient
class StockInsuficientError(Exception):
    pass

class Categoria(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    descripcio = models.TextField(blank=True, null=True)
    requereix_refrigeracio = models.BooleanField(default=False)
    temperatura_maxima = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Temperatura màxima permesa (null si no requereix)"
    )

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.nom


class Magatzem(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    adreca = models.CharField(max_length=255)
    capacitat_maxima = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Capacitat en m³"
    )
    te_cambra_frio = models.BooleanField(default=False)
    responsable = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Magatzems"

    def __str__(self):
        return self.nom


class Producte(models.Model):
    class UnitatMesura(models.TextChoices):
        UNITAT = "UNITAT", "Unitat"
        CAIXA = "CAIXA", "Caixa"
        PALET = "PALET", "Palet"
        KG = "KG", "Kg"
        LITRE = "LITRE", "Litre"

    codi = models.CharField(
        max_length=20
        , unique=True
        , help_text="Codi únic del producte (ex: BEB001)"
    )
    nom = models.CharField(max_length=255)
    descripcio = models.TextField(blank=True, null=True)
    categoria = models.ForeignKey(
        Categoria
        , on_delete=models.CASCADE
        , related_name="productes"
    )
    preu_unitari = models.DecimalField(
        max_digits=10
        , decimal_places=2
        , validators=[MinValueValidator(Decimal("0.00"))]
    )
    unitat_mesura = models.CharField(
        max_length=10
        , choices=UnitatMesura.choices
        , default=UnitatMesura.UNITAT
    )
    iva = models.DecimalField(
        max_digits=4
        , decimal_places=2
        , choices=[
            (Decimal("0.04"), "4%"),
            (Decimal("0.10"), "10%"),
            (Decimal("0.21"), "21%"),
        ]
        , default=Decimal("0.21")
    )
    es_perible = models.BooleanField(default=False, help_text="Indica si caduca aviat")
    imatge_url = models.URLField(blank=True, null=True)
    actiu = models.BooleanField(default=True)
    magatzems = models.ManyToManyField(
        Magatzem,
        through='StockMagatzem',
        related_name='productes'
    )

    class Meta:
        verbose_name_plural = "Productes"

    def __str__(self):
        return f"{self.codi} - {self.nom}"

    def get_stock_total(self):
        # stock total a tots els magatzems
        return sum(stockMagatzem.quantitat for stockMagatzem in self.stocks.all())


class StockMagatzem(models.Model):
    producte = models.ForeignKey(
        Producte
        , on_delete=models.CASCADE
        , related_name="stocks"
    )
    magatzem = models.ForeignKey(
        Magatzem
        , on_delete=models.CASCADE
        , related_name="stocks"
    )
    quantitat = models.IntegerField(
        default=0
        , validators=[MinValueValidator(0)]
    )
    data_ultima_entrada = models.DateField(auto_now=True)
    ubicacio = models.CharField(
        max_length=20
        , help_text="Passadís/estanteria (ex: A-12)"
    )

    class Meta:
        verbose_name = "Stock de Magatzem"
        verbose_name_plural = "Stocks de Magatzems"
        unique_together = ['producte', 'magatzem']

    def __str__(self):
        return f"{self.producte.nom}, {self.magatzem.nom}: {self.quantitat} unitats"

    def is_stock_baix(self):
        #  True si stock < 10
        return self.quantitat < 10


class Client(models.Model):
    codi_client = models.CharField(
        max_length=20
        , unique=True
        , help_text="Codi del client"
    )
    nom_comercial = models.CharField(max_length=255)
    cif = models.CharField(max_length=20, unique=True)
    persona_contacte = models.CharField(max_length=255)
    telefon = models.CharField(max_length=20)
    email = models.EmailField()
    adreca_entrega = models.CharField(max_length=255)
    poblacio = models.CharField(max_length=100)
    codi_postal = models.CharField(max_length=10)
    actiu = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Clients"

    def __str__(self):
        return f"{self.codi_client} - {self.nom_comercial}"


class Empleat(models.Model):
    user = models.OneToOneField(
        User
        ,on_delete=models.CASCADE
        , related_name="empleat"
    )
    codi_empleat = models.CharField(
        max_length=20
        , unique=True
        , help_text="Codi únic (ex: EMP001)"
    )
    telefon = models.CharField(max_length=20)
    data_alta = models.DateField(auto_now_add=True)
    magatzem_assignat = models.ForeignKey(
        Magatzem
        , on_delete=models.SET_NULL
        , null=True
        , related_name="empleats"
    )
    carrec = models.CharField(
        max_length=50,
        help_text="Ex: Preparador, Repartidor, Administrador"
    )

    class Meta:
        verbose_name_plural = "Empleats"

    def __str__(self):
        return f"{self.codi_empleat} - {self.user.get_full_name() or self.user.username}"


class Albara(models.Model):

    class Estat(models.TextChoices):
        PENDENT = "PENDENT", "Pendent"
        EN_PREPARACIO = "EN_PREPARACIO", "En preparació"
        PREPARAT = "PREPARAT", "Preparat"
        ENVIAT = "ENVIAT", "Enviat"
        ENTREGAT = "ENTREGAT", "Entregat"
        CANCELAT = "CANCELAT", "Cancel·lat"

    TRANSICIONS_VALIDES = {
        Estat.PENDENT: [Estat.EN_PREPARACIO, Estat.CANCELAT],
        Estat.EN_PREPARACIO: [Estat.PREPARAT, Estat.CANCELAT],
        Estat.PREPARAT: [Estat.ENVIAT, Estat.CANCELAT],
        Estat.ENVIAT: [Estat.ENTREGAT, Estat.CANCELAT],
        Estat.ENTREGAT: [],  # No es pot canviar
        Estat.CANCELAT: [],  # No es pot canviar
    }

    numero_albara = models.CharField(
        max_length=30,
        unique=True,
        help_text="Número únic d'albarà (ex: ALB-2024-001)"
    )
    client = models.ForeignKey(
        Client
        , on_delete=models.CASCADE
        , related_name="albarans"
    )
    empleat = models.ForeignKey(
        Empleat
        , on_delete=models.SET_NULL
        , null=True
        , related_name="albarans"
        , help_text="Qui prepara l'albarà"
    )
    magatzem = models.ForeignKey(
        Magatzem
        , on_delete=models.SET_NULL
        , null=True
        , blank=True
        , related_name="albarans"
        , help_text="D'on surt la mercaderia"
    )
    data_creacio = models.DateTimeField(auto_now_add=True)
    data_entrega_prevista = models.DateField()
    estat = models.CharField(
        max_length=20
        , choices=Estat.choices
        , default=Estat.PENDENT
    )
    base_imposable = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )
    total_iva = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )
    observacions = models.TextField(blank=True, null=True)
    signatura_client = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Nom de qui signa (null si no està entregat)"
    )

    class Meta:
        verbose_name = "Albarà"
        verbose_name_plural = "Albarans"
        ordering = ["-data_creacio"]

    def calcular_totals(self):
        # calcula base_imposable, total_iva i total
        base = Decimal("0.00")
        iva_total = Decimal("0.00")

        for linia in self.linies.all():
            base += linia.subtotal
            iva_linia = linia.subtotal * linia.iva
            iva_total += iva_linia

        self.base_imposable = base
        self.total_iva = iva_total
        self.total = base + iva_total
        self.save(update_fields=["base_imposable", "total_iva", "total"])

    def calcular_total(self):
        self.calcular_totals()

    def pot_afegir_linies(self):
        return self.estat in [
            Albara.Estat.PENDENT,
            Albara.Estat.EN_PREPARACIO
        ]

    def pot_veure_detall(self, user):
        return user.is_authenticated and user.email == self.client.email

    def pot_canviar_estat(self, nou_estat):
        # valida si es pot fer la transició d'estat
        if self.estat == nou_estat:
            return False
        transicions_possibles = self.TRANSICIONS_VALIDES.get(self.estat, [])
        return nou_estat in transicions_possibles

    def canviar_estat(self, nou_estat):
        # canvia l'estat
        if not self.pot_canviar_estat(nou_estat):
            raise ValueError(f"No es pot canviar de {self.get_estat_display()} a {dict(self.Estat.choices).get(nou_estat)}")
        self.estat = nou_estat
        self.save(update_fields=["estat"])

    def __str__(self):
        return self.numero_albara

class LiniaAlbara(models.Model):
    albara = models.ForeignKey(
        Albara,
        on_delete=models.CASCADE,
        related_name="linies"
    )
    producte = models.ForeignKey(
        Producte,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linies_albara"
    )
    nom_producte = models.CharField(max_length=255)
    quantitat = models.IntegerField(
        validators=[MinValueValidator(1)]
    )
    preu_unitari = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    iva = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.21")
    )
    descompte_percentatge = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("100.00"))],
        help_text="Descompte aplicat (0-100)"
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
        default=Decimal("0.00")
    )
    observacions = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Notes especials (ex: substituir si no hi ha stock)"
    )

    class Meta:
        verbose_name = "Línia d'Albarà"
        verbose_name_plural = "Línies d'Albarà"

    def save(self, *args, **kwargs):
        # Calcular subtotal amb descompte
        subtotal_sense_descompte = self.quantitat * self.preu_unitari
        descompte = subtotal_sense_descompte * (self.descompte_percentatge / Decimal("100"))
        self.subtotal = subtotal_sense_descompte - descompte
        super().save(*args, **kwargs)
        self.albara.calcular_totals()

    def __str__(self):
        return f"{self.nom_producte} ({self.quantitat})"


class MovimentStock(models.Model):
    # registre de moviments del stock

    class TipusMoviment(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada"
        SORTIDA = "SORTIDA", "Sortida"
        AJUST = "AJUST", "Ajust"

    producte = models.ForeignKey(
        Producte,
        on_delete=models.CASCADE,
        related_name="moviments"
    )
    magatzem = models.ForeignKey(
        Magatzem,
        on_delete=models.CASCADE,
        related_name="moviments"
    )
    tipus = models.CharField(
        max_length=10,
        choices=TipusMoviment.choices
    )
    quantitat = models.IntegerField()
    data = models.DateTimeField(auto_now_add=True)
    albara = models.ForeignKey(
        Albara,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moviments_stock"
    )
    usuari = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    observacions = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Moviment d'Stock"
        verbose_name_plural = "Moviments d'Stock"
        ordering = ["-data"]

    def __str__(self):
        return f"{self.tipus} - {self.producte.nom} ({self.quantitat})"

