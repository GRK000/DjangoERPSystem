from django import forms
from django.forms import ModelForm
from decimal import Decimal

from .models import Client, Albara, LiniaAlbara, Producte, Magatzem, StockMagatzem


class ClientForm(ModelForm):
    class Meta:
        model = Client
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
        widgets = {
            "codi_client": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "CLI001"
            }),
            "nom_comercial": forms.TextInput(attrs={
                "class": "form-control"
            }),
            "cif": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "B12345678"
            }),
            "persona_contacte": forms.TextInput(attrs={
                "class": "form-control"
            }),
            "telefon": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "612 345 678"
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control"
            }),
            "adreca_entrega": forms.TextInput(attrs={
                "class": "form-control"
            }),
            "poblacio": forms.TextInput(attrs={
                "class": "form-control"
            }),
            "codi_postal": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "08001"
            }),
            "actiu": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
        }


class AlbaraForm(ModelForm):
    class Meta:
        model = Albara
        fields = [
            "numero_albara",
            "client",
            "magatzem",
            "data_entrega_prevista",
            "estat",
            "observacions",
        ]
        widgets = {
            "numero_albara": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "ALB-2024-001"
            }),
            "client": forms.Select(attrs={
                "class": "form-select"
            }),
            "magatzem": forms.Select(attrs={
                "class": "form-select"
            }),
            "data_entrega_prevista": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "estat": forms.Select(attrs={
                "class": "form-select"
            }),
            "observacions": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3
            }),
        }


class LiniaAlbaraForm(ModelForm):
    """Formulari basic per línies d'albarà (sense producte)"""
    class Meta:
        model = LiniaAlbara
        fields = [
            "nom_producte",
            "quantitat",
            "preu_unitari",
            "descompte_percentatge",
            "observacions",
        ]
        widgets = {
            "nom_producte": forms.TextInput(attrs={
                "class": "form-control"
            }),
            "quantitat": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1
            }),
            "preu_unitari": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0"
            }),
            "descompte_percentatge": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "max": "100",
                "placeholder": "0.00"
            }),
            "observacions": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Notes especials..."
            }),
        }


class LiniaAlbaraProducteForm(ModelForm):
    """Formulari per línies d'albarà amb selecció de producte"""
    producte = forms.ModelChoiceField(
        queryset=Producte.objects.filter(actiu=True),
        widget=forms.Select(attrs={"class": "form-select"}),
        required=False,
        label="Producte del catàleg"
    )

    class Meta:
        model = LiniaAlbara
        fields = [
            "producte",
            "nom_producte",
            "quantitat",
            "preu_unitari",
            "iva",
            "descompte_percentatge",
            "observacions",
        ]
        widgets = {
            "nom_producte": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nom del producte"
            }),
            "quantitat": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
                "value": 1
            }),
            "preu_unitari": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0"
            }),
            "iva": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "max": "100",
                "placeholder": "Ej: 21"
            }),
            "descompte_percentatge": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "max": "100",
                "value": "0"
            }),
            "observacions": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Notes especials (ex: substituir si no hi ha stock)"
            }),
        }

    def __init__(self, *args, magatzem=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.magatzem = magatzem

        # Si hi ha magatzem, filtra productes amb stock
        if magatzem:
            productes_amb_stock = StockMagatzem.objects.filter(
                magatzem=magatzem,
                quantitat__gt=0
            ).values_list('producte_id', flat=True)
            self.fields['producte'].queryset = Producte.objects.filter(
                actiu=True,
                id__in=productes_amb_stock
            )

    def clean(self):
        cleaned_data = super().clean()
        producte = cleaned_data.get('producte')

        # Si hi ha producte seleccionat, es copien les seves dades
        if producte:
            cleaned_data['nom_producte'] = producte.nom
            cleaned_data['preu_unitari'] = producte.preu_unitari
            cleaned_data['iva'] = producte.iva

        return cleaned_data


class ReposicioStockForm(forms.Form):
    # Afegir Stock
    producte = forms.ModelChoiceField(
        queryset=Producte.objects.filter(actiu=True),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Producte"
    )
    magatzem = forms.ModelChoiceField(
        queryset=Magatzem.objects.all(),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Magatzem"
    )
    quantitat = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "min": 1
        }),
        label="Quantitat a afegir"
    )
    ubicacio = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "A-12"
        }),
        label="Ubicació (passadís/estanteria)"
    )

