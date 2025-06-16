# models.py - Version étendue

from django.db import models
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from authentication.models import Agence


class ChargeCategory(models.Model):
    code = models.CharField(max_length=10, unique=True)
    nom = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sous_categories')

    class Meta:
        db_table = "charge_categories"
        verbose_name = "Catégorie de charge"
        verbose_name_plural = "Catégories de charge"

    def __str__(self):
        return f"{self.code} - {self.nom}"


class StationCharge(models.Model):
    station = models.ForeignKey(Agence, on_delete=models.CASCADE, related_name="charges")
    categorie = models.ForeignKey(ChargeCategory, on_delete=models.PROTECT, related_name="charges")
    intitule = models.CharField(max_length=255)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    periode = models.CharField(
        max_length=20,
        choices=[
            ("mois", "Mois"),
            ("annee", "Année"),
            ("semaine", "Semaine"),
            ("jour", "Jour"),
            ("unique", "Ponctuel"),
        ],
        default="mois"
    )
    date_charge = models.DateField()
    commentaire = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "station_charges"
        verbose_name = "Charge de station"
        verbose_name_plural = "Charges de station"

    def __str__(self):
        return f"{self.intitule} - {self.categorie.nom} - {self.station.nom_agence} ({self.date_charge})"


# Nouveau modèle pour les swaps (revenus)
class Swap(models.Model):
    battery_moto_user_association_id = models.BigIntegerField()
    battery_in_id = models.BigIntegerField()
    battery_out_id = models.BigIntegerField()
    swap_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    swap_date = models.DateTimeField(default=timezone.now)
    nom = models.CharField(max_length=255, null=True, blank=True)
    prenom = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    battery_out_soc = models.CharField(max_length=255, null=True, blank=True)
    battery_in_soc = models.CharField(max_length=255, null=True, blank=True)
    agent_user_id = models.BigIntegerField()
    agence = models.ForeignKey(Agence, on_delete=models.CASCADE, related_name="swaps", db_column='id_agence')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "swaps"
        verbose_name = "Swap de batterie"
        verbose_name_plural = "Swaps de batterie"


    def __str__(self):
        return f"Swap {self.id} - {self.agence.nom_agence} ({self.swap_date.date()})"


# Nouveau modèle pour les analyses de rentabilité
class RentabilityAnalysis(models.Model):
    PERIOD_CHOICES = [
        ('day', 'Jour'),
        ('week', 'Semaine'),
        ('month', 'Mois'),
        ('quarter', 'Trimestre'),
        ('year', 'Année'),
        ('custom', 'Période personnalisée'),
    ]

    station = models.ForeignKey(Agence, on_delete=models.CASCADE, related_name="analyses")
    nom_analyse = models.CharField(max_length=255)
    type_periode = models.CharField(max_length=20, choices=PERIOD_CHOICES)
    date_debut = models.DateField()
    date_fin = models.DateField()
    revenus_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    charges_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    benefice_net = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    marge_beneficiaire = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # En pourcentage
    nombre_swaps = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rentability_analyses"
        verbose_name = "Analyse de rentabilité"
        verbose_name_plural = "Analyses de rentabilité"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nom_analyse} - {self.station.nom_agence}"

    def calculate_metrics(self):
        """Calcule les métriques de rentabilité pour la période définie"""
        # Calcul des revenus (swaps)
        revenus = Swap.objects.filter(
            agence=self.station,
            swap_date__date__gte=self.date_debut,
            swap_date__date__lte=self.date_fin,
            swap_price__isnull=False
        ).aggregate(total=Sum('swap_price'))['total'] or 0

        # Calcul des charges
        charges = StationCharge.objects.filter(
            station=self.station,
            date_charge__gte=self.date_debut,
            date_charge__lte=self.date_fin
        ).aggregate(total=Sum('montant'))['total'] or 0

        # Nombre de swaps
        nb_swaps = Swap.objects.filter(
            agence=self.station,
            swap_date__date__gte=self.date_debut,
            swap_date__date__lte=self.date_fin
        ).count()

        # Calculs dérivés
        benefice = revenus - charges
        marge = (benefice / revenus * 100) if revenus > 0 else 0

        # Mise à jour des champs
        self.revenus_total = revenus
        self.charges_total = charges
        self.benefice_net = benefice
        self.marge_beneficiaire = marge
        self.nombre_swaps = nb_swaps
        self.save()

        return {
            'revenus': revenus,
            'charges': charges,
            'benefice': benefice,
            'marge': marge,
            'swaps': nb_swaps
        }

    @staticmethod
    def get_period_dates(period_type, custom_start=None, custom_end=None):
        """Retourne les dates de début et fin selon le type de période"""
        today = timezone.now().date()

        if period_type == 'day':
            return today, today
        elif period_type == 'week':
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            return start, end
        elif period_type == 'month':
            start = today.replace(day=1)
            if today.month == 12:
                end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            return start, end
        elif period_type == 'quarter':
            quarter = (today.month - 1) // 3 + 1
            start = today.replace(month=(quarter - 1) * 3 + 1, day=1)
            end_month = quarter * 3
            if end_month == 12:
                end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = today.replace(month=end_month + 1, day=1) - timedelta(days=1)
            return start, end
        elif period_type == 'year':
            start = today.replace(month=1, day=1)
            end = today.replace(month=12, day=31)
            return start, end
        elif period_type == 'custom':
            return custom_start, custom_end
        else:
            return today, today