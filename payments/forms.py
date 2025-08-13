from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
from datetime import time
from .models import Paiement, Penalite, NotificationPaiement, ReglePenalite


class PaiementForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = [
            'montant_moto', 'montant_batterie', 'montant_total',
            'date_paiement', 'methode_paiement',
            'reference_transaction', 'notes', 'est_penalite',
            'statut_paiement'
        ]
        widgets = {
            'montant_moto': forms.NumberInput(attrs={'class': 'form-control'}),
            'montant_batterie': forms.NumberInput(attrs={'class': 'form-control'}),
            'montant_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'date_paiement': forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'}),
            'methode_paiement': forms.Select(attrs={'class': 'form-control'}),
            'reference_transaction': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'est_penalite': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'statut_paiement': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, contrat_type=None, contrat_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.contrat_type = contrat_type
        self.contrat_id = contrat_id

    def save(self, commit=True):
        paiement = super().save(commit=False)

        # Générer une référence si absente
        if not paiement.reference:
            import uuid
            paiement.reference = f"PMT-{uuid.uuid4().hex[:8].upper()}"

        from contrats.models import ContratChauffeur, ContratPartenaire, ContratBatterie

        if self.contrat_type == 'chauffeur':
            paiement.contrat_chauffeur = ContratChauffeur.objects.get(id=self.contrat_id)
            paiement.type_contrat = 'chauffeur'
        elif self.contrat_type == 'partenaire':
            paiement.contrat_partenaire = ContratPartenaire.objects.get(id=self.contrat_id)
            paiement.type_contrat = 'partenaire'
        elif self.contrat_type == 'batterie':
            paiement.contrat_batterie = ContratBatterie.objects.get(id=self.contrat_id)
            paiement.type_contrat = 'batterie'

        if not paiement.heure_paiement:
            paiement.heure_paiement = timezone.now().time()

        if commit:
            paiement.save()
        return paiement

# Dans payments/forms.py

class PaiementRapideForm(forms.Form):
    montant = forms.DecimalField(
        label=_('Montant Engagé'),
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'montant_principal'})
    )

    montant_batterie = forms.DecimalField(
        label=_('Montant batterie'),
        required=False,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'montant_batterie'})
    )

    methode_paiement = forms.ChoiceField(
        label=_('Méthode de paiement'),
        choices=Paiement.METHODE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    reference_transaction = forms.CharField(
        label=_('Référence transaction'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    pardonner_penalite_jour = forms.BooleanField(
        label=_('Pardonner la pénalité du jour'),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'pardonner_penalite_jour'})
    )

    justification_pardon = forms.CharField(
        label=_('Justification du pardon (obligatoire)'),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'id': 'justification_pardon'})
    )

    notes = forms.CharField(
        label=_('Notes'),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )

    def __init__(self, *args, **kwargs):
        self.penalite_jour = kwargs.pop('penalite_jour', None)
        super().__init__(*args, **kwargs)

        if not self.penalite_jour:
            self.fields['pardonner_penalite_jour'].widget = forms.HiddenInput()
            self.fields['justification_pardon'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('pardonner_penalite_jour') and not cleaned_data.get('justification_pardon'):
            self.add_error('justification_pardon', _('Une justification est obligatoire pour pardonner une pénalité'))
        return cleaned_data

    def clean_montant(self):
        montant = self.cleaned_data['montant']
        if montant <= 0:
            raise forms.ValidationError("Le montant principal doit être positif.")
        return montant

    def clean_montant_batterie(self):
        return self.cleaned_data.get('montant_batterie') or 0



class PenaliteForm(forms.ModelForm):
    """Formulaire pour créer une pénalité"""

    class Meta:
        model = Penalite
        fields = ['montant', 'motif', 'description', 'type_penalite']
        widgets = {
            'montant': forms.NumberInput(attrs={'class': 'form-control'}),
            'motif': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'type_penalite': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Rendre le champ type_penalite obligatoire
        self.fields['type_penalite'].required = True

        # Mettre à jour le choix des motifs selon le type de pénalité
        self.fields['type_penalite'].help_text = _(
            "Le type de pénalité détermine le montant recommandé. 'Moto + Batterie' pour les contrats chauffeur/partenaire avec batterie, 'Batterie uniquement' pour les contrats de batterie seule."
        )



class GestionPenaliteForm(forms.Form):
    """Formulaire amélioré pour gérer une pénalité existante"""
    ACTION_CHOICES = [
        ('payer', 'Encaisser la pénalité'),
        ('annuler', 'Annuler la pénalité'),
        ('reporter', 'Reporter la pénalité'),
    ]

    action = forms.ChoiceField(
        label=_('Action à effectuer'),
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'action_penalite'})
    )

    raison = forms.CharField(
        label=_('Raison / Commentaire'),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'id': 'raison_penalite'})
    )

    montant_paiement = forms.DecimalField(
        label=_('Montant du paiement'),
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'montant_paiement_penalite'})
    )

    methode_paiement = forms.ChoiceField(
        label=_('Méthode de paiement'),
        required=False,
        choices=Paiement.METHODE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'methode_paiement_penalite'})
    )

    date_report = forms.DateField(
        label=_('Reporter au'),
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date', 'id': 'date_report'})
    )

    envoyer_notification = forms.BooleanField(
        label=_('Envoyer une notification au client'),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'envoyer_notification'})
    )

    def __init__(self, *args, **kwargs):
        self.penalite = kwargs.pop('penalite', None)
        super().__init__(*args, **kwargs)

        if self.penalite:
            self.fields['montant_paiement'].initial = self.penalite.montant

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        raison = cleaned_data.get('raison')
        montant_paiement = cleaned_data.get('montant_paiement')
        methode_paiement = cleaned_data.get('methode_paiement')
        date_report = cleaned_data.get('date_report')

        if action == 'annuler' and not raison:
            self.add_error('raison', _('Une raison est requise pour annuler une pénalité'))

        if action == 'payer':
            if not montant_paiement:
                self.add_error('montant_paiement', _('Le montant du paiement est requis'))
            if not methode_paiement:
                self.add_error('methode_paiement', _('La méthode de paiement est requise'))

        if action == 'reporter' and not date_report:
            self.add_error('date_report', _('La date de report est requise'))

        return cleaned_data


# Dans forms.py de l'application payments

class GestionPenalitesMultiplesForm(forms.Form):
    """Formulaire pour gérer plusieurs pénalités en même temps"""
    ACTION_CHOICES = [
        ('payer', 'Encaisser toutes les pénalités sélectionnées'),
        ('annuler', 'Annuler toutes les pénalités sélectionnées'),
        ('reporter', 'Reporter toutes les pénalités sélectionnées'),
    ]

    action = forms.ChoiceField(
        label=_('Action groupée'),
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'action_groupee'})
    )

    penalites_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )

    raison = forms.CharField(
        label=_('Raison / Commentaire'),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'id': 'raison_groupee'})
    )

    montant_total = forms.DecimalField(
        label=_('Montant total'),
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'id': 'montant_total'})
    )

    methode_paiement = forms.ChoiceField(
        label=_('Méthode de paiement'),
        required=False,
        choices=Paiement.METHODE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'methode_paiement_groupee'})
    )

    date_report = forms.DateField(
        label=_('Reporter au'),
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date', 'id': 'date_report_groupee'})
    )

    envoyer_notification = forms.BooleanField(
        label=_('Envoyer une notification aux clients'),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'envoyer_notification_groupee'})
    )


class ReglePenaliteForm(forms.ModelForm):
    """Formulaire pour configurer les règles de pénalités"""

    class Meta:
        model = ReglePenalite
        fields = [
            'nom_regle', 'type_contrat', 'heure_debut_leger',
            'heure_debut_grave', 'montant_penalite_leger',
            'montant_penalite_grave', 'est_active'
        ]
        widgets = {
            'nom_regle': forms.TextInput(attrs={'class': 'form-control'}),
            'type_contrat': forms.Select(attrs={'class': 'form-control'}),
            'heure_debut_leger': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'heure_debut_grave': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'montant_penalite_leger': forms.NumberInput(attrs={'class': 'form-control'}),
            'montant_penalite_grave': forms.NumberInput(attrs={'class': 'form-control'}),
            'est_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        heure_debut_leger = cleaned_data.get('heure_debut_leger')
        heure_debut_grave = cleaned_data.get('heure_debut_grave')

        if heure_debut_leger and heure_debut_grave and heure_debut_leger >= heure_debut_grave:
            self.add_error('heure_debut_grave', _(
                "L'heure de début pour pénalité grave doit être postérieure à l'heure de début pour pénalité légère"
            ))

        return cleaned_data


class RechercheAvanceeForm(forms.Form):
    """Formulaire de recherche et filtrage avancé amélioré"""

    TYPE_CONTRAT_CHOICES = [
        ('', 'Tous les types'),
        ('chauffeur', 'Contrats chauffeur'),
        ('partenaire', 'Contrats partenaire'),
        ('batterie', 'Contrats batterie'),
    ]

    STATUT_CHOICES = [
        ('', 'Tous les statuts'),
        ('actif', 'Actif'),
        ('suspendu', 'Suspendu'),
        ('terminé', 'Terminé'),
    ]

    FREQUENCE_CHOICES = [
        ('', 'Toutes les fréquences'),
        ('journalier', 'Journalier'),
        ('hebdomadaire', 'Hebdomadaire'),
        ('mensuel', 'Mensuel'),
        ('trimestriel', 'Trimestriel'),
    ]

    STATUT_PAIEMENT_CHOICES = [
        ('', 'Tous les statuts'),
        ('a_jour', 'À jour'),
        ('retard', 'En retard'),
        ('penalites', 'Avec pénalités'),
    ]

    TRIER_PAR_CHOICES = [
        ('date_paiement', 'Date de paiement (récent → ancien)'),
        ('-date_paiement', 'Date de paiement (ancien → récent)'),
        ('montant', 'Montant (croissant)'),
        ('-montant', 'Montant (décroissant)'),
        ('client', 'Nom du client (A → Z)'),
        ('-client', 'Nom du client (Z → A)'),
    ]

    q = forms.CharField(
        label=_('Recherche (nom, référence, CNI...)'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Rechercher...', 'id': 'recherche_q'})
    )

    type_contrat = forms.ChoiceField(
        label=_('Type de contrat'),
        choices=TYPE_CONTRAT_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    statut = forms.ChoiceField(
        label=_('Statut contrat'),
        choices=STATUT_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    statut_paiement = forms.ChoiceField(
        label=_('Statut paiement'),
        choices=STATUT_PAIEMENT_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    frequence = forms.ChoiceField(
        label=_('Fréquence de paiement'),
        choices=FREQUENCE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    date_debut = forms.DateField(
        label=_('Date de début (après le)'),
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'})
    )

    date_fin = forms.DateField(
        label=_('Date de fin (avant le)'),
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'})
    )

    trier_par = forms.ChoiceField(
        label=_('Trier par'),
        choices=TRIER_PAR_CHOICES,
        required=False,
        initial='date_paiement',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    vue_calendrier = forms.BooleanField(
        label=_('Vue calendrier'),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )