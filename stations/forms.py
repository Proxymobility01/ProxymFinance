from django import forms
from django.utils import timezone
from datetime import timedelta
from .models import ChargeCategory, StationCharge, RentabilityAnalysis
from authentication.models import Agence


class ChargeCategoryForm(forms.ModelForm):
    class Meta:
        model = ChargeCategory
        fields = ['code', 'nom', 'description', 'parent']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 310'}),
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Loyer'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
        }


class StationChargeForm(forms.ModelForm):
    class Meta:
        model = StationCharge
        fields = ['station', 'categorie', 'intitule', 'montant', 'periode', 'date_charge', 'commentaire']
        widgets = {
            'station': forms.Select(attrs={'class': 'form-control select2'}),
            'categorie': forms.Select(attrs={'class': 'form-control select2'}),
            'intitule': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Loyer Juin 2025'}),
            'montant': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'periode': forms.Select(attrs={'class': 'form-control select2'}),
            'date_charge': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'commentaire': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['station'].queryset = Agence.objects.order_by('nom_agence')
        self.fields['categorie'].queryset = ChargeCategory.objects.order_by('code')


class RentabilityAnalysisForm(forms.ModelForm):
    class Meta:
        model = RentabilityAnalysis
        fields = ['station', 'nom_analyse', 'type_periode', 'date_debut', 'date_fin']
        widgets = {
            'station': forms.Select(attrs={'class': 'form-select'}),
            'nom_analyse': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Analyse Q2 2025'}),
            'type_periode': forms.Select(attrs={'class': 'form-select', 'id': 'id_type_periode'}),
            'date_debut': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['station'].queryset = Agence.objects.order_by('nom_agence')

        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        self.fields['date_debut'].initial = start_of_month
        self.fields['date_fin'].initial = end_of_month

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')

        if date_debut and date_fin and date_debut > date_fin:
            raise forms.ValidationError("La date de d\u00e9but doit \u00eatre ant\u00e9rieure \u00e0 la date de fin.")

        return cleaned_data


class PeriodFilterForm(forms.Form):
    PERIOD_CHOICES = [
        ('', 'S\u00e9lectionner une p\u00e9riode'),
        ('today', "Aujourd'hui"),
        ('yesterday', 'Hier'),
        ('this_week', 'Cette semaine'),
        ('last_week', 'Semaine derni\u00e8re'),
        ('this_month', 'Ce mois'),
        ('last_month', 'Mois dernier'),
        ('this_quarter', 'Ce trimestre'),
        ('this_year', 'Cette ann\u00e9e'),
        ('custom', 'P\u00e9riode personnalis\u00e9e'),
    ]

    station = forms.ModelChoiceField(
        queryset=Agence.objects.all(),
        required=False,
        empty_label="Toutes les stations",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    periode = forms.ChoiceField(
        choices=PERIOD_CHOICES,
        required=False,

        widget=forms.Select(attrs={'class': 'form-control select2', 'id': 'id_periode'})
    )

    date_debut = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    date_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['station'].queryset = Agence.objects.order_by('nom_agence')

    def get_date_range(self):
        periode = self.cleaned_data.get('periode')
        today = timezone.now().date()

        if periode == 'today':
            return today, today
        elif periode == 'yesterday':
            return today - timedelta(days=1), today - timedelta(days=1)
        elif periode == 'this_week':
            start = today - timedelta(days=today.weekday())
            return start, start + timedelta(days=6)
        elif periode == 'last_week':
            start = today - timedelta(days=today.weekday() + 7)
            return start, start + timedelta(days=6)
        elif periode == 'this_month':
            start = today.replace(day=1)
            end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            return start, end
        elif periode == 'last_month':
            first = today.replace(day=1)
            end = first - timedelta(days=1)
            start = end.replace(day=1)
            return start, end
        elif periode == 'this_quarter':
            quarter = (today.month - 1) // 3 + 1
            start = today.replace(month=(quarter - 1) * 3 + 1, day=1)
            end_month = quarter * 3
            end = (today.replace(month=end_month, day=1) + timedelta(days=31)).replace(day=1) - timedelta(days=1)
            return start, end
        elif periode == 'this_year':
            return today.replace(month=1, day=1), today.replace(month=12, day=31)
        elif periode == 'custom':
            return self.cleaned_data.get('date_debut'), self.cleaned_data.get('date_fin')
        return None, None

    def clean(self):
        cleaned_data = super().clean()
        periode = cleaned_data.get('periode')
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')

        if periode == 'custom':
            if not date_debut or not date_fin:
                raise forms.ValidationError("Les dates sont requises pour une p\u00e9riode personnalis\u00e9e.")
            if date_debut > date_fin:
                raise forms.ValidationError("La date de d\u00e9but doit \u00eatre ant\u00e9rieure \u00e0 la date de fin.")
        return cleaned_data


class QuickAnalysisForm(forms.Form):
    station = forms.ModelChoiceField(
        queryset=Agence.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        label="Station"
    )

    QUICK_PERIODS = [
        ('last_7_days', '7 derniers jours'),
        ('last_30_days', '30 derniers jours'),
        ('current_month', 'Mois en cours'),
        ('last_month', 'Mois dernier'),
        ('current_quarter', 'Trimestre en cours'),
    ]

    periode = forms.ChoiceField(
        choices=QUICK_PERIODS,
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        label="P\u00e9riode d'analyse"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['station'].queryset = Agence.objects.order_by('nom_agence')
