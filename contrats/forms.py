from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from .models import (
    ValidatedUser,
    AssociationUserMoto,
    Partenaire,
    Garant,
    ContratChauffeur,
    ContratPartenaire,
    ContratBatterie,
    MotosValides,
    BatteriesValides,
    ValidatedUser,
    CongesChauffeur
)


# Ajoutez ce formulaire dans votre forms.py

class AssociationUserMotoForm(forms.ModelForm):
    """Formulaire pour créer/modifier une association chauffeur-moto."""

    class Meta:
        model = AssociationUserMoto
        fields = ['validated_user', 'moto_valide', 'statut']
        labels = {
            'validated_user': _('Chauffeur'),
            'moto_valide': _('Moto'),
            'statut': _('Statut du paiement'),
        }
        widgets = {
            'validated_user': forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Sélectionner un chauffeur'
            }),
            'moto_valide': forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Sélectionner une moto'
            }),
            'statut': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtrer les chauffeurs disponibles (non associés à une moto active)
        chauffeurs_associes = AssociationUserMoto.objects.values_list('validated_user_id', flat=True)

        # Si on modifie une association existante, inclure le chauffeur actuel
        if self.instance.pk and self.instance.validated_user_id:
            chauffeurs_associes = chauffeurs_associes.exclude(validated_user_id=self.instance.validated_user_id)

        self.fields['validated_user'].queryset = ValidatedUser.objects.exclude(
            id__in=chauffeurs_associes
        ).order_by('nom', 'prenom')

        # Filtrer les motos disponibles (non associées à un chauffeur)
        motos_associees = AssociationUserMoto.objects.values_list('moto_valide_id', flat=True)

        # Si on modifie une association existante, inclure la moto actuelle
        if self.instance.pk and self.instance.moto_valide_id:
            motos_associees = motos_associees.exclude(moto_valide_id=self.instance.moto_valide_id)

        self.fields['moto_valide'].queryset = MotosValides.objects.exclude(
            id__in=motos_associees
        ).order_by('model')

        # Rendre les champs obligatoires
        self.fields['validated_user'].required = True
        self.fields['moto_valide'].required = True

    def clean(self):
        """Validation globale du formulaire."""
        cleaned_data = super().clean()
        validated_user = cleaned_data.get('validated_user')
        moto_valide = cleaned_data.get('moto_valide')

        # Vérifier qu'une association avec les mêmes éléments n'existe pas déjà
        if validated_user and moto_valide:
            existing_association = AssociationUserMoto.objects.filter(
                validated_user=validated_user,
                moto_valide=moto_valide
            )

            # Si on modifie, exclure l'instance actuelle
            if self.instance.pk:
                existing_association = existing_association.exclude(pk=self.instance.pk)

            if existing_association.exists():
                raise ValidationError(
                    _("Une association entre ce chauffeur et cette moto existe déjà.")
                )

        # Vérifier que le chauffeur n'est pas déjà associé à une autre moto
        if validated_user:
            other_associations = AssociationUserMoto.objects.filter(
                validated_user=validated_user
            )

            if self.instance.pk:
                other_associations = other_associations.exclude(pk=self.instance.pk)

            if other_associations.exists():
                self.add_error('validated_user', _(
                    f"Ce chauffeur est déjà associé à la moto: {other_associations.first().moto_valide}"
                ))

        # Vérifier que la moto n'est pas déjà associée à un autre chauffeur
        if moto_valide:
            other_associations = AssociationUserMoto.objects.filter(
                moto_valide=moto_valide
            )

            if self.instance.pk:
                other_associations = other_associations.exclude(pk=self.instance.pk)

            if other_associations.exists():
                self.add_error('moto_valide', _(
                    f"Cette moto est déjà associée au chauffeur: {other_associations.first().validated_user}"
                ))

        return cleaned_data

    def save(self, commit=True):
        """Sauvegarder l'association."""
        instance = super().save(commit=False)

        # Générer automatiquement les timestamps si nécessaire
        if not instance.created_at:
            from django.utils import timezone
            instance.created_at = timezone.now()

        if commit:
            instance.save()

        return instance


# À ajouter dans contrats/forms.py

# Formulaire pour les motos (à ajouter dans forms.py)
class MotoForm(forms.ModelForm):
    """Formulaire pour ajouter/modifier une moto."""

    class Meta:
        model = MotosValides
        fields = ['vin', 'model', 'gps_imei', 'assurance', 'permis']
        labels = {
            'vin': _('Numéro VIN'),
            'model': _('Modèle'),
            'gps_imei': _('IMEI GPS'),
            'assurance': _('Assurance'),
            'permis': _('Permis'),
        }
        widgets = {
            'vin': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Numéro VIN unique'
            }),
            'model': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Modèle de la moto'
            }),
            'gps_imei': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'IMEI du GPS'
            }),
            'assurance': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Numéro d\'assurance (optionnel)'
            }),
            'permis': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Numéro de permis (optionnel)'
            }),
        }

    def clean_vin(self):
        """Vérifier que le VIN est unique."""
        vin = self.cleaned_data['vin']
        if MotosValides.objects.filter(vin=vin).exclude(id=self.instance.id).exists():
            raise ValidationError(_("Ce numéro VIN est déjà utilisé par une autre moto."))
        return vin

    def clean_gps_imei(self):
        """Vérifier le format de l'IMEI."""
        imei = self.cleaned_data['gps_imei']
        # Vérification basique de l'IMEI (15 chiffres)
        if not imei.isdigit() or len(imei) != 15:
            raise ValidationError(_("L'IMEI doit contenir exactement 15 chiffres."))
        return imei





class ChauffeurForm(forms.ModelForm):
    """Formulaire pour ajouter/modifier un chauffeur."""

    class Meta:
        model = ValidatedUser
        fields = [
            'nom', 'prenom', 'email', 'phone', 'numero_cni',
            'domicile', 'photo_cni_recto', 'photo_cni_verso',
            'permis_conduire', 'plan_localisation'
        ]
        labels = {
            'nom': _('Nom'),
            'prenom': _('Prénom'),
            'email': _('Adresse email'),
            'phone': _('Téléphone'),
            'numero_cni': _('Numéro CNI'),
            'domicile': _('Adresse du domicile'),
            'photo_cni_recto': _('Photo CNI (Recto)'),
            'photo_cni_verso': _('Photo CNI (Verso)'),
            'permis_conduire': _('Permis de conduire'),
            'plan_localisation': _('Plan de localisation'),
        }
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'prenom': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_cni': forms.TextInput(attrs={'class': 'form-control'}),
            'domicile': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        """Vérifier que l'email est unique."""
        email = self.cleaned_data['email']
        if ValidatedUser.objects.filter(email=email).exclude(id=self.instance.id).exists():
            raise ValidationError(_("Cet email est déjà utilisé par un autre chauffeur."))
        return email

    def clean_phone(self):
        """Vérifier le format du numéro de téléphone."""
        phone = self.cleaned_data['phone']
        # Vérification basique du format (peut être adapté selon les besoins)
        if not phone.isdigit() or len(phone) < 8:
            raise ValidationError(_("Numéro de téléphone invalide. Il doit contenir au moins 8 chiffres."))
        return phone

    def clean_numero_cni(self):
        """Vérifier que le numéro CNI est unique."""
        numero_cni = self.cleaned_data['numero_cni']
        if ValidatedUser.objects.filter(numero_cni=numero_cni).exclude(id=self.instance.id).exists():
            raise ValidationError(_("Ce numéro CNI est déjà utilisé par un autre chauffeur."))
        return numero_cni


class PartenaireForm(forms.ModelForm):
    """Formulaire pour ajouter/modifier un partenaire."""

    class Meta:
        model = Partenaire
        fields = [
            'nom', 'prenom', 'email', 'phone', 'numero_cni',
            'adresse', 'photo_cni_recto', 'photo_cni_verso',
            'justificatif_activite', 'plan_localisation', 'contrat_physique'
        ]
        labels = {
            'nom': _('Nom'),
            'prenom': _('Prénom'),
            'email': _('Adresse email'),
            'phone': _('Téléphone'),
            'numero_cni': _('Numéro CNI'),
            'adresse': _('Adresse'),
            'photo_cni_recto': _('Photo CNI (Recto)'),
            'photo_cni_verso': _('Photo CNI (Verso)'),
            'justificatif_activite': _('Justificatif d\'activité'),
            'plan_localisation': _('Plan de localisation'),
            'contrat_physique': _('Contrat physique'),
        }
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Entrez le nom'}),
            'prenom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Entrez le prénom'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'exemple@email.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 77 123 45 67'}),
            'numero_cni': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Numéro de CNI'}),
            'adresse': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Adresse complète'}),
            'photo_cni_recto': forms.FileInput(attrs={'class': 'form-control-file'}),
            'photo_cni_verso': forms.FileInput(attrs={'class': 'form-control-file'}),
            'justificatif_activite': forms.FileInput(attrs={'class': 'form-control-file'}),
            'plan_localisation': forms.FileInput(attrs={'class': 'form-control-file'}),
            'contrat_physique': forms.FileInput(attrs={'class': 'form-control-file'}),
        }

    def clean_email(self):
        """Vérifier que l'email est unique."""
        email = self.cleaned_data.get('email')
        if email:
            # Vérifier l'unicité seulement s'il y a un email
            qs = Partenaire.objects.filter(email=email)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(_("Cet email est déjà utilisé par un autre partenaire."))
        return email

    def clean_phone(self):
        """Vérifier le format du numéro de téléphone."""
        phone = self.cleaned_data.get('phone')
        if phone:
            # Enlever les espaces et vérifier que c'est un nombre
            phone_digits = ''.join(filter(str.isdigit, phone))
            if len(phone_digits) < 8:
                raise ValidationError(_("Le numéro de téléphone doit contenir au moins 8 chiffres."))
            # Standardiser le format
            return phone_digits
        return phone

    def clean_numero_cni(self):
        """Vérifier que le numéro CNI est unique."""
        numero_cni = self.cleaned_data.get('numero_cni')
        if numero_cni:
            qs = Partenaire.objects.filter(numero_cni=numero_cni)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(_("Ce numéro CNI est déjà utilisé par un autre partenaire."))
        return numero_cni

    def clean(self):
        """Validation globale du formulaire."""
        cleaned_data = super().clean()

        # Vérification conditionnelle des documents
        # Par exemple, si un partenaire nouveau est créé, certains documents pourraient être obligatoires
        # if not self.instance.pk:  # Nouveau partenaire
        #    required_docs = ['photo_cni_recto', 'photo_cni_verso']
        #    for doc in required_docs:
        #        if not cleaned_data.get(doc):
        #            self.add_error(doc, _("Ce document est obligatoire pour un nouveau partenaire."))

        return cleaned_data


class GarantForm(forms.ModelForm):
    """Formulaire pour ajouter/modifier un garant."""

    class Meta:
        model = Garant
        fields = [
            'nom', 'prenom', 'numero_cni', 'adresse',
            'occupation', 'telephone', 'cni_document',
            'justificatif_domicile', 'justificatif_activite',
            'contrat_physique'
        ]
        labels = {
            'nom': _('Nom'),
            'prenom': _('Prénom'),
            'numero_cni': _('Numéro CNI'),
            'adresse': _('Adresse'),
            'occupation': _('Profession/Occupation'),
            'telephone': _('Téléphone'),
            'cni_document': _('Document CNI'),
            'justificatif_domicile': _('Justificatif de domicile'),
            'justificatif_activite': _('Justificatif d\'activité'),
            'contrat_physique': _('Contrat physique'),
        }
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'prenom': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_cni': forms.TextInput(attrs={'class': 'form-control'}),
            'adresse': forms.TextInput(attrs={'class': 'form-control'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_numero_cni(self):
        """Vérifier que le numéro CNI est unique."""
        numero_cni = self.cleaned_data['numero_cni']
        if Garant.objects.filter(numero_cni=numero_cni).exclude(id=self.instance.id).exists():
            raise ValidationError(_("Ce numéro CNI est déjà utilisé par un autre garant."))
        return numero_cni

    def clean_telephone(self):
        """Vérifier le format du numéro de téléphone."""
        telephone = self.cleaned_data['telephone']
        # Vérification basique du format (peut être adapté selon les besoins)
        if not telephone.isdigit() or len(telephone) < 8:
            raise ValidationError(_("Numéro de téléphone invalide. Il doit contenir au moins 8 chiffres."))
        return telephone


class ContratChauffeurForm(forms.ModelForm):
    """Formulaire pour ajouter/modifier un contrat chauffeur."""

    class Meta:
        model = ContratChauffeur
        fields = [
            'reference', 'association', 'montant_total', 'montant_engage',
            'frequence_paiement', 'date_signature', 'date_debut',
            'duree_semaines', 'montant_caution_batterie', 'duree_caution_batterie',
            'montant_engage_batterie',  # NOUVEAU CHAMP
            'garant', 'contrat_physique', 'statut'
        ]
        labels = {
            'reference': _('Référence du contrat'),
            'association': _('Association chauffeur-moto'),  # Corrigé
            'montant_total': _('Montant total (FCFA)'),
            'montant_engage': _('Montant engagé par échéance - Moto (FCFA)'),
            'frequence_paiement': _('Fréquence de paiement'),
            'date_signature': _('Date de signature'),
            'date_debut': _('Date de début'),
            'duree_semaines': _('Durée (semaines)'),
            'montant_caution_batterie': _('Montant caution batterie (FCFA)'),
            'duree_caution_batterie': _('Durée caution batterie (jours)'),
            'montant_engage_batterie': _('Montant engagé par échéance - Batterie (FCFA)'),
            'garant': _('Garant'),
            'contrat_physique': _('Contrat physique'),
            'statut': _('Statut'),
        }
        widgets = {
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'association': forms.Select(attrs={'class': 'form-control select2'}),  # Corrigé
            'montant_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'montant_engage': forms.NumberInput(attrs={'class': 'form-control'}),
            'frequence_paiement': forms.Select(attrs={'class': 'form-control'}),
            'date_signature': forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'}),
            'date_debut': forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'}),
            'duree_semaines': forms.NumberInput(attrs={'class': 'form-control'}),
            'montant_caution_batterie': forms.NumberInput(attrs={'class': 'form-control'}),
            'duree_caution_batterie': forms.NumberInput(attrs={'class': 'form-control'}),
            'montant_engage_batterie': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Montant par échéance pour la batterie',
                'step': '0.01'
            }),
            'garant': forms.Select(attrs={'class': 'form-control select2'}),
            'contrat_physique': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        """Validation globale du formulaire."""
        cleaned_data = super().clean()
        association = cleaned_data.get('association')
        montant_engage_batterie = cleaned_data.get('montant_engage_batterie')
        montant_engage = cleaned_data.get('montant_engage')

        # Vérifier si l'association est déjà utilisée par un autre contrat actif
        if association:
            contrats_actifs = ContratChauffeur.objects.filter(
                association=association,
                statut='actif'
            ).exclude(id=self.instance.id)

            if contrats_actifs.exists():
                self.add_error('association',
                               _("Cette association chauffeur-moto est déjà utilisée par un contrat actif."))

        # Vérifier que le montant engagé batterie est positif
        if montant_engage_batterie is not None and montant_engage_batterie <= 0:
            self.add_error('montant_engage_batterie', _("Le montant engagé pour la batterie doit être supérieur à 0."))

        # Vérifier que le montant engagé est positif
        if montant_engage is not None and montant_engage <= 0:
            self.add_error('montant_engage', _("Le montant engagé doit être supérieur à 0."))

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Exclure les associations déjà utilisées par d'autres contrats
        associations_utilisees = ContratChauffeur.objects.filter(
            statut='actif'
        ).values_list('association_id', flat=True)

        # Si on édite un contrat existant, on autorise aussi l'association courante
        if self.instance.pk and self.instance.association_id:
            associations_utilisees = associations_utilisees.exclude(association_id=self.instance.association_id)

        self.fields['association'].queryset = AssociationUserMoto.objects.exclude(
            id__in=associations_utilisees
        ).select_related('validated_user', 'moto_valide')

        # CORRECTION : Utiliser 'model' au lieu de 'marque' et 'modele'
        def format_association_label(obj):
            if obj.validated_user and obj.moto_valide:
                return f"{obj.validated_user.prenom} {obj.validated_user.nom} - {obj.moto_valide.model} ({obj.moto_valide.vin})"
            elif obj.validated_user:
                return f"{obj.validated_user.prenom} {obj.validated_user.nom} - Moto non définie"
            elif obj.moto_valide:
                return f"Chauffeur non défini - {obj.moto_valide.model} ({obj.moto_valide.vin})"
            else:
                return "Association incomplète"

        # Appliquer le formatage personnalisé
        self.fields['association'].label_from_instance = format_association_label


class ContratPartenaireForm(forms.ModelForm):
    """Formulaire pour ajouter/modifier un contrat partenaire."""
    class Meta:
        model = ContratPartenaire
        fields = [
            'reference', 'partenaire', 'motos', 'montant_total','montant_engage',
            'frequence_paiement', 'date_signature', 'date_debut',
            'duree_semaines', 'montant_caution_batterie', 'duree_caution_batterie',
            'cni_document', 'plan_localisation', 'contrat_physique', 'statut'
        ]
        labels = {
            'reference': _('Référence du contrat'),
            'partenaire': _('Partenaire'),
            'motos': _('Motos'),
            'montant_total': _('Montant total (FCFA)'),
            'frequence_paiement': _('Fréquence de paiement'),
            'date_signature': _('Date de signature'),
            'date_debut': _('Date de début'),
            'duree_semaines': _('Durée (semaines)'),
            'montant_caution_batterie': _('Montant caution batterie (FCFA)'),
            'duree_caution_batterie': _('Durée caution batterie (jours)'),
            'cni_document': _('Document CNI'),
            'plan_localisation': _('Plan de localisation'),
            'contrat_physique': _('Contrat physique'),
            'statut': _('Statut'),
            'montant_engage': _('Montant engagé par échéance - Moto (FCFA)'),
        }
        widgets = {
            'reference': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'partenaire': forms.Select(attrs={'class': 'form-control select2'}),
            'motos': forms.SelectMultiple(attrs={'class': 'form-control select2', 'multiple': 'multiple'}),
            'montant_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'frequence_paiement': forms.Select(attrs={'class': 'form-control'}),
            'date_signature': forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'}),
            'date_debut': forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'}),
            'duree_semaines': forms.NumberInput(attrs={'class': 'form-control'}),
            'montant_caution_batterie': forms.NumberInput(attrs={'class': 'form-control'}),
            'duree_caution_batterie': forms.NumberInput(attrs={'class': 'form-control'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
            'montant_engage': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtrer les motos utilisées par un chauffeur (via l'association)
        motos_utilisees_chauffeur = ContratChauffeur.objects.filter(
            statut='actif',
            association__isnull=False
        ).values_list('association__moto_valide_id', flat=True)

        # Exclure les motos déjà associées à d'autres partenaires
        autres_contrats_partenaire = ContratPartenaire.objects.filter(statut='actif').exclude(id=self.instance.id)
        motos_utilisees_partenaire = []

        for contrat in autres_contrats_partenaire:
            motos_utilisees_partenaire.extend(contrat.motos.values_list('id', flat=True))

        motos_utilisees = list(motos_utilisees_chauffeur) + motos_utilisees_partenaire
        motos_disponibles = MotosValides.objects.exclude(id__in=motos_utilisees)

        # Si on édite un contrat existant, inclure les motos actuellement associées
        if self.instance.pk:
            motos_actuelles = self.instance.motos.all()
            if motos_actuelles:
                motos_disponibles = motos_disponibles | motos_actuelles

        self.fields['motos'].queryset = motos_disponibles



    def clean(self):
        """Validation globale du formulaire."""
        cleaned_data = super().clean()
        motos = cleaned_data.get('motos')

        if not motos or len(motos) == 0:
            self.add_error('motos', _("Vous devez sélectionner au moins une moto."))

        return cleaned_data


class ContratBatterieForm(forms.ModelForm):
    """Formulaire pour ajouter/modifier un contrat batterie."""

    class Meta:
        model = ContratBatterie
        fields = [
            'reference', 'chauffeur', 'partenaire', 'montant_total', 'montant_engage',
            'frequence_paiement', 'date_signature', 'date_debut',
            'duree_semaines', 'montant_caution', 'duree_caution', 'statut'
        ]
        labels = {
            'reference': _('Référence du contrat'),
            'chauffeur': _('Chauffeur'),
            'partenaire': _('Partenaire'),
            'montant_total': _('Montant total (FCFA)'),
            'frequence_paiement': _('Fréquence de paiement'),
            'montant_engage': _('Montant engagé par échéance (FCFA)'),
            'date_signature': _('Date de signature'),
            'date_debut': _('Date de début'),
            'duree_semaines': _('Durée (semaines)'),
            'montant_caution': _('Montant caution (FCFA)'),
            'duree_caution': _('Durée caution (jours)'),
            'statut': _('Statut'),
        }
        widgets = {
            'montant_engage': forms.NumberInput(attrs={'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'chauffeur': forms.Select(attrs={'class': 'form-control select2'}),
            'partenaire': forms.Select(attrs={'class': 'form-control select2'}),
            'montant_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'frequence_paiement': forms.Select(attrs={'class': 'form-control'}),
            'date_signature': forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'}),
            'date_debut': forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'}),
            'duree_semaines': forms.NumberInput(attrs={'class': 'form-control'}),
            'montant_caution': forms.NumberInput(attrs={'class': 'form-control'}),
            'duree_caution': forms.NumberInput(attrs={'class': 'form-control'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ici, on ne gère plus du tout les batteries !

    def clean(self):
        cleaned_data = super().clean()
        # Plus aucune vérification de batterie ici !
        return cleaned_data


class CongesChauffeurForm(forms.ModelForm):
    """Formulaire pour ajouter/modifier un congé."""

    class Meta:
        model = CongesChauffeur
        fields = ['contrat', 'date_debut', 'date_fin', 'commentaire']
        labels = {
            'contrat': _('Contrat du chauffeur'),
            'date_debut': _('Date de début'),
            'date_fin': _('Date de fin'),
            'commentaire': _('Commentaire (optionnel)'),
        }
        widgets = {
            'contrat': forms.Select(attrs={'class': 'form-control select2'}),
            'date_debut': forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'}),
            'commentaire': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtrer uniquement les contrats actifs
        self.fields['contrat'].queryset = ContratChauffeur.objects.filter(statut='actif')

    def clean(self):
        """Validation globale du formulaire."""
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        contrat = cleaned_data.get('contrat')

        # Vérifier que la date de fin est postérieure à la date de début
        if date_debut and date_fin and date_fin < date_debut:
            self.add_error('date_fin', _("La date de fin ne peut pas être antérieure à la date de début."))

        # Vérifier que le chauffeur a suffisamment de jours de congés restants
        if contrat and date_debut and date_fin:
            nombre_jours = (date_fin - date_debut).days + 1

            if nombre_jours > contrat.jours_conges_restants:
                self.add_error('date_fin', _(
                    f"Ce congé représente {nombre_jours} jours, mais le chauffeur ne dispose que de "
                    f"{contrat.jours_conges_restants} jours de congés restants."
                ))

        return cleaned_data


class StatutCongeForm(forms.Form):
    """Formulaire pour modifier le statut d'un congé."""

    STATUT_CHOICES = CongesChauffeur.STATUT_CHOICES

    statut = forms.ChoiceField(
        choices=STATUT_CHOICES,
        label=_('Nouveau statut'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    commentaire = forms.CharField(
        label=_('Commentaire (optionnel)'),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )