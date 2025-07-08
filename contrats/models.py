from django.db import models
from django.utils import timezone
# Create your models here.


from django.db import models
from django.utils import timezone
from datetime import timedelta
from datetime import timedelta
from django.apps import apps


class AssociationUserMoto(models.Model):
    STATUT_PAYMENT_CHOICES = [
        ('achat_direct', 'Achat Direct'),
        ('lease', 'Lease'),
    ]

    validated_user = models.ForeignKey(
        "ValidatedUser",
        on_delete=models.CASCADE,
        related_name='associations_user',
        null=True,
        blank=True
    )
    moto_valide = models.ForeignKey(
        "MotosValides",
        on_delete=models.CASCADE,
        related_name='associations_motos',
        null=True,
        blank=True
    )

    statut = models.CharField(max_length=50, choices=STATUT_PAYMENT_CHOICES, default='Lease')
    created_at = models.DateTimeField(auto_now=True, null=True, blank=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    deleted_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        nom = self.validated_user.nom if self.validated_user else "Sans nom"
        prenom = self.validated_user.prenom if self.validated_user else "Sans prénom"
        moto = self.moto_valide.model if self.moto_valide else "Moto inconnue"
        immatriculation = self.moto_valide.vin if self.moto_valide else "?"

        return f"{prenom} {nom} - Moto: {moto} ({immatriculation})"

    class Meta:
        db_table = 'association_user_motos'
        verbose_name = 'Association utilisateur–moto'


class ValidatedUser(models.Model):
    user_unique_id = models.CharField(max_length=255, unique=True)
    nom = models.CharField(max_length=255)
    prenom = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=255, default='pending')
    password = models.CharField(max_length=255, null=True, blank=True)
    token = models.CharField(max_length=255, null=True, blank=True)
    numero_cni = models.CharField(max_length=255, null=True, blank=True)
    domicile = models.CharField(max_length=255)

    # Documents
    photo_cni_recto = models.FileField(upload_to='documents/chauffeurs/cni/recto/', null=True, blank=True)
    photo_cni_verso = models.FileField(upload_to='documents/chauffeurs/cni/verso/', null=True, blank=True)
    permis_conduire = models.FileField(upload_to='documents/chauffeurs/permis/', null=True, blank=True)
    plan_localisation = models.FileField(upload_to='documents/chauffeurs/localisation/', null=True, blank=True)

    photo = models.CharField(max_length=255, null=True, blank=True)
    link_expiration = models.DateTimeField(null=True, blank=True)
    verification_code = models.CharField(max_length=255, null=True, blank=True)
    verification_code_sent_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'validated_users'


    def __str__(self):
        return f"{self.nom} {self.prenom}"


class MotosValides(models.Model):
    vin = models.CharField(max_length=255, unique=True)
    moto_unique_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    model = models.CharField(max_length=255)
    gps_imei = models.CharField(max_length=255)
    assurance = models.CharField(max_length=255, null=True, blank=True)
    permis = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.model} ({self.vin})"

    class Meta:
        db_table = 'motos_valides'



class BatteriesValides(models.Model):
    id = models.BigAutoField(primary_key=True)
    batterie_unique_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    mac_id = models.CharField(max_length=255, unique=True)
    date_production = models.CharField(max_length=255, null=True, blank=True)
    gps = models.CharField(max_length=255)
    fabriquant = models.CharField(max_length=255)
    statut = models.CharField(max_length=255, default='en attente')
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True, null=True, blank=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f"{self.batterie_unique_id or self.mac_id}"

    class Meta:
        db_table = 'batteries_valides'





class RoleEntite(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'role_entites'


    def __str__(self):
        return self.title


# models Partenaire

class Partenaire(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    numero_cni = models.CharField(max_length=50, unique=True)
    adresse = models.CharField(max_length=255)

    # Documents
    photo_cni_recto = models.FileField(upload_to='documents/partenaires/cni/recto/', null=True, blank=True)
    photo_cni_verso = models.FileField(upload_to='documents/partenaires/cni/verso/', null=True, blank=True)
    justificatif_activite = models.FileField(upload_to='documents/garants/activite/', null=True, blank=True)

    plan_localisation = models.FileField(upload_to='documents/partenaires/localisation/', null=True, blank=True)
    contrat_physique = models.FileField(upload_to='documents/partenaires/contrat/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contrats_partenaire'


    def __str__(self):
        return f"{self.prenom} {self.nom} - {self.numero_cni}"


# Modèle pour les garants
class Garant(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    numero_cni = models.CharField(max_length=50, unique=True)
    adresse = models.CharField(max_length=255)
    occupation = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20)

    # Documents
    cni_document = models.FileField(upload_to='documents/garants/cni/', null=True, blank=True)
    justificatif_domicile = models.FileField(upload_to='documents/garants/domicile/', null=True, blank=True)
    justificatif_activite = models.FileField(upload_to='documents/garants/activite/', null=True, blank=True)
    contrat_physique = models.FileField(upload_to='documents/garants/contrat/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contrats_garant'


        # Indique à Django que la table existe déjà

    def __str__(self):
        return f"{self.prenom} {self.nom} - {self.numero_cni}"


# Modèle abstrait pour tous les types de contrats
class Contrat(models.Model):
    STATUT_CHOICES = [
        ('actif', 'Actif'),
        ('terminé', 'Terminé'),
        ('suspendu', 'Suspendu'),
    ]

    FREQUENCE_PAIEMENT_CHOICES = [
        ('journalier', 'Journalier'),
        ('hebdomadaire', 'Hebdomadaire'),
        ('mensuel', 'Mensuel'),
        ('trimestriel', 'Trimestriel'),
    ]

    reference = models.CharField(max_length=100, unique=True)
    montant_total = models.DecimalField(max_digits=10, decimal_places=2)
    montant_paye = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    montant_restant = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    frequence_paiement = models.CharField(max_length=20, choices=FREQUENCE_PAIEMENT_CHOICES, default='journalier')
    montant_par_paiement = models.DecimalField(max_digits=10, decimal_places=2)

    date_signature = models.DateField()
    date_enregistrement = models.DateField(default=timezone.now)
    date_debut = models.DateField()
    duree_semaines = models.IntegerField(default=61)  # 61 semaines par défaut
    duree_jours = models.IntegerField(default=366)
    date_fin = models.DateField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='actif')
    montant_engage = models.DecimalField(max_digits=10, decimal_places=2,
                                         help_text="Montant que le client s'engage à payer à chaque échéance")

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Calculer le montant restant lors de la sauvegarde
        self.montant_restant = self.montant_total - self.montant_paye

        # Calculer automatiquement la date de fin en fonction de la durée en jours
        if self.date_debut and self.duree_jours:
            self.date_fin = self.date_debut + timedelta(days=self.duree_jours)

        super().save(*args, **kwargs)

    def prolonger_duree(self, jours_supplementaires):
        """Prolonge la durée du contrat du nombre de jours spécifié"""
        self.duree_jours += jours_supplementaires
        self.duree_semaines = self.duree_jours // 7
        self.date_fin = self.date_debut + timedelta(days=self.duree_jours)
        self.save()

    def calculer_montant_par_paiement(self):
        total_jours = self.duree_semaines * 6  # 6 jours par semaine

        if self.frequence_paiement == 'journalier':
            return self.montant_total / total_jours
        elif self.frequence_paiement == 'hebdomadaire':
            return self.montant_total / self.duree_semaines
        elif self.frequence_paiement == 'mensuel':
            return self.montant_total / (self.duree_semaines / 4)
        elif self.frequence_paiement == 'trimestriel':
            return self.montant_total / (self.duree_semaines / 13)
        return 0

    def verifier_terminer_contrat(self):
        """Vérifie si le contrat peut être marqué comme terminé"""
        Penalite = apps.get_model('payments', 'Penalite')
        if self.montant_paye >= self.montant_total and self.montant_restant <= 0:
            # Vérifier qu'il n'y a pas de pénalités en attente
            penalites_en_attente = False

            # Pour ContratChauffeur
            if hasattr(self, 'contrats_chauffeur'):
                penalites_en_attente = Penalite.objects.filter(
                    contrat_chauffeur=self,
                    statut='en_attente'
                ).exists()

            # Pour ContratPartenaire
            elif hasattr(self, 'contrats'):
                penalites_en_attente = Penalite.objects.filter(
                    contrat_partenaire=self,
                    statut='en_attente'
                ).exists()

            # Pour ContratBatterie
            elif hasattr(self, 'contrats_batterie'):
                penalites_en_attente = Penalite.objects.filter(
                    contrat_batterie=self,
                    statut='en_attente'
                ).exists()

            if not penalites_en_attente:
                self.statut = 'terminé'
                self.save()
                return True

        return False


# Contrat Chauffeur
class ContratChauffeur(Contrat):
    association = models.ForeignKey(AssociationUserMoto, on_delete=models.SET_NULL, null=True,
                                    related_name='association_user_motos')

    # Documents
    contrat_physique = models.FileField(upload_to='documents/chauffeurs/contrat/', null=True, blank=True)

    # Garant
    garant = models.ForeignKey(Garant, on_delete=models.SET_NULL, null=True, related_name='contrats_garantis')

    # Caution batterie
    montant_caution_batterie = models.DecimalField(max_digits=10, decimal_places=2, default=50000)
    duree_caution_batterie = models.IntegerField(default=100)  # 100 jours par défaut

    # NOUVEAU CHAMP: Montant engagé pour la batterie
    montant_engage_batterie = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Montant que le chauffeur s'engage à payer à chaque échéance pour la batterie"
    )

    # Congés
    jours_conges_total = models.IntegerField(default=30)  # 30 jours de congés par défaut
    jours_conges_utilises = models.IntegerField(default=0)
    jours_conges_restants = models.IntegerField(default=30)

    class Meta:
        db_table = 'contrats_contratchauffeur'


    def save(self, *args, **kwargs):
        # Calculer les jours de congés restants
        self.jours_conges_restants = self.jours_conges_total - self.jours_conges_utilises

        # Calculer automatiquement la date de fin en fonction de la durée en jours
        if self.date_debut and self.duree_jours:
            self.date_fin = self.date_debut + timedelta(days=self.duree_jours)
        elif self.date_debut and self.duree_semaines:
            self.duree_jours = self.duree_semaines * 7
            self.date_fin = self.date_debut + timedelta(days=self.duree_jours)

        super().save(*args, **kwargs)

    def prolonger_duree(self, jours_supplementaires):
        """Prolonge la durée du contrat du nombre de jours spécifié"""
        self.duree_jours += jours_supplementaires
        self.duree_semaines = self.duree_jours // 7
        self.date_fin = self.date_debut + timedelta(days=self.duree_jours)
        self.save()

    def __str__(self):
        return f"Contrat chauffeur: {self.association.validated_user.prenom} {self.association.validated_user.nom}  - {self.reference}"


# Contrat Partenaire
# Dans models.py de l'application contrats

class ContratPartenaire(Contrat):
    partenaire = models.ForeignKey(
        Partenaire,
        on_delete=models.CASCADE,
        related_name='contrats'
    )
    motos = models.ManyToManyField(MotosValides)
    # Documents
    cni_document = models.FileField(upload_to='documents/partenaires/cni/', null=True, blank=True)
    plan_localisation = models.FileField(upload_to='documents/partenaires/localisation/', null=True, blank=True)
    contrat_physique = models.FileField(upload_to='documents/partenaires/contrat/', null=True, blank=True)

    # Caution batterie
    montant_caution_batterie = models.DecimalField(max_digits=10, decimal_places=2, default=50000)
    duree_caution_batterie = models.IntegerField(default=100)  # 100 jours par défaut

    # NOUVEAU CHAMP: Montant engagé pour la batterie
    montant_engage_batterie = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Montant que le partenaire s'engage à payer à chaque échéance pour la batterie"
    )

    class Meta:
        db_table = 'contrats_contratpartenaire'


    def save(self, *args, **kwargs):
        # Calculer automatiquement la date de fin en fonction de la durée en jours
        if self.date_debut and self.duree_jours:
            self.date_fin = self.date_debut + timedelta(days=self.duree_jours)
        elif self.date_debut and self.duree_semaines:
            self.duree_jours = self.duree_semaines * 7
            self.date_fin = self.date_debut + timedelta(days=self.duree_jours)

        super().save(*args, **kwargs)

    def prolonger_duree(self, jours_supplementaires):
        """Prolonge la durée du contrat du nombre de jours spécifié"""
        self.duree_jours += jours_supplementaires
        self.duree_semaines = self.duree_jours // 7
        self.date_fin = self.date_debut + timedelta(days=self.duree_jours)
        self.save()

    def __str__(self):
        return f"Contrat partenaire: {self.partenaire.nom} {self.partenaire.prenom} - {self.reference}"


# Dans models.py de l'application contrats
class ContratBatterie(Contrat):
    chauffeur = models.ForeignKey(ValidatedUser, on_delete=models.CASCADE, related_name='contrats_batterie', null=True,
                                  blank=True)
    partenaire = models.ForeignKey(Partenaire, on_delete=models.CASCADE, related_name='contrats_batterie', null=True,
                                   blank=True)

    # Caution
    montant_caution = models.DecimalField(max_digits=10, decimal_places=2)
    duree_caution = models.IntegerField(default=100)  # 100 jours par défaut

    # NOUVEAU CHAMP: Montant engagé pour la batterie
    montant_engage_batterie = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Montant que le client s'engage à payer à chaque échéance pour la batterie"
    )

    class Meta:
        db_table = 'contrats_contratbatterie'


    def clean(self):
        from django.core.exceptions import ValidationError

        # Vérifier qu'un seul propriétaire est défini (chauffeur ou partenaire)
        if self.chauffeur and self.partenaire:
            raise ValidationError(
                "Un contrat batterie ne peut pas être associé à la fois à un chauffeur et à un partenaire.")

        if not self.chauffeur and not self.partenaire:
            raise ValidationError("Un contrat batterie doit être associé soit à un chauffeur, soit à un partenaire.")

        super().clean()

    def save(self, *args, **kwargs):
        # Si montant_engage_batterie est défini et différent de 0, utiliser cette valeur
        # pour calculer le montant_par_paiement
        if self.montant_engage_batterie > 0:
            self.montant_par_paiement = self.montant_engage_batterie
        else:
            # Sinon, utiliser le calcul automatique basé sur le montant total
            self.montant_par_paiement = self.calculer_montant_par_paiement()

        super().save(*args, **kwargs)

    def __str__(self):
        if self.chauffeur:
            return f"Contrat batterie: {self.chauffeur.nom} {self.chauffeur.prenom}  - {self.reference}"
        else:
            return f"Contrat batterie: {self.partenaire.prenom} {self.partenaire.nom} - {self.reference}"


# Modèle pour lier les motos à ContratPartenaire
class ContratPartenaireMoto(models.Model):
    contrat = models.ForeignKey(ContratPartenaire, on_delete=models.CASCADE, related_name='motos_associees')
    moto = models.ForeignKey(MotosValides, on_delete=models.CASCADE, related_name='contrats_partenaire',
                             db_column='moto_id')

    class Meta:
        unique_together = ('contrat', 'moto')
        db_table = 'contrats_contratpartenairemoto'


    def __str__(self):
        return f"Contrat {self.contrat.reference} - Moto {self.moto.vin}"


# Modèle pour les congés chauffeur
class CongesChauffeur(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('approuvé', 'Approuvé'),
        ('planifié', 'Planifié'),
        ('en_cours', 'En cours'),
        ('terminé', 'Terminé'),
        ('annulé', 'Annulé'),
        ('rejeté', 'Rejeté'),
    ]

    contrat = models.ForeignKey(ContratChauffeur, on_delete=models.CASCADE, related_name='conges')
    date_debut = models.DateField()
    date_fin = models.DateField()
    nombre_jours = models.IntegerField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    commentaire = models.TextField(blank=True, null=True)
    date_demande = models.DateTimeField(auto_now_add=True)
    date_approbation = models.DateTimeField(null=True, blank=True)
    approuve_par = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'contrats_congeschauffeur'


    def clean(self):
        from django.core.exceptions import ValidationError

        # Vérifier que la date de fin est postérieure à la date de début
        if self.date_fin < self.date_debut:
            raise ValidationError("La date de fin ne peut pas être antérieure à la date de début")

        # Vérifier que le nombre de jours ne dépasse pas le solde disponible
        if self.nombre_jours is not None and self.contrat.jours_conges_restants is not None:
            if self.nombre_jours > self.contrat.jours_conges_restants and self.statut != 'annulé':
                raise ValidationError(
                    f"Le nombre de jours demandés ({self.nombre_jours}) dépasse le solde de congés disponible ({self.contrat.jours_conges_restants})"
                )

    def save(self, *args, **kwargs):
        # Calculer automatiquement le nombre de jours
        if self.date_debut and self.date_fin:
            delta = self.date_fin - self.date_debut
            self.nombre_jours = delta.days + 1  # inclure le jour de fin

        # Gérer le statut et mettre à jour le contrat
        is_new = self.pk is None
        old_instance = None

        if not is_new:
            # Obtenir l'instance avant modification
            old_instance = CongesChauffeur.objects.get(pk=self.pk)

        super().save(*args, **kwargs)

        # Mise à jour du contrat uniquement si le statut a changé
        if is_new and self.statut in ['approuvé', 'planifié', 'en_cours']:
            # Nouveau congé approuvé
            self.contrat.jours_conges_utilises += self.nombre_jours

            # Prolonger automatiquement la durée du contrat
            self.contrat.prolonger_duree(self.nombre_jours)
            self.contrat.save()

        elif not is_new and old_instance and old_instance.statut != self.statut:
            # Changement de statut
            if old_instance.statut in ['approuvé', 'planifié', 'en_cours', 'terminé'] and self.statut in ['annulé',
                                                                                                          'rejeté']:
                # Annulation d'un congé approuvé - réduire la durée du contrat
                self.contrat.jours_conges_utilises -= self.nombre_jours
                self.contrat.prolonger_duree(-self.nombre_jours)  # Réduire la durée
                self.contrat.save()

            elif old_instance.statut in ['en_attente', 'annulé', 'rejeté'] and self.statut in ['approuvé', 'planifié',
                                                                                               'en_cours']:
                # Approbation d'un congé en attente - prolonger la durée du contrat
                self.contrat.jours_conges_utilises += self.nombre_jours
                self.contrat.prolonger_duree(self.nombre_jours)
                self.contrat.save()

    def __str__(self):

        return f"Congé: {self.contrat.association.validated_user.prenom}-{self.contrat.association.validated_user.nom} - {self.date_debut} à {self.date_fin}"

