from django.db import models

# Create your models here.

from django.db import models
from django.utils import timezone
from django.conf import settings
import uuid
from decimal import Decimal
from datetime import  timedelta, date, time
from contrats.models import ValidatedUser

from django.db.models import Sum


class Paiement(models.Model):
    METHODE_CHOICES = [
        ('espece', 'Espèces'),
        ('mobile_money', 'Mobile Money'),
        ('virement', 'Virement bancaire'),
        ('cheque', 'Chèque'),
    ]

    TYPE_CONTRAT_CHOICES = [
        ('chauffeur_batterie', 'Contrat Chauffeur & Batterie'),
        ('partenaire_batterie', 'Contrat Partenaire & Batterie'),
        ('batterie_uniquement', 'Contrat Batterie Uniquement'),
    ]

    STATUS_CHOICES = [
        ('complet', 'Paiement complet'),
        ('partiel', 'Paiement partiel'),
        ('avance', 'Paiement en avance'),
    ]

    reference = models.CharField(max_length=100, unique=True)
    montant_moto = models.DecimalField(max_digits=10, decimal_places=2)
    montant_batterie = models.DecimalField(max_digits=10, decimal_places=2)
    montant_total = models.DecimalField(max_digits=10, decimal_places=2)
    date_paiement = models.DateField()
    date_enregistrement = models.DateTimeField(default=timezone.now)
    methode_paiement = models.CharField(max_length=50, choices=METHODE_CHOICES)
    reference_transaction = models.CharField(max_length=100, blank=True, null=True)

    # Liens vers les contrats
    contrat_chauffeur = models.ForeignKey('contrats.ContratChauffeur', on_delete=models.CASCADE, null=True, blank=True,
                                          related_name='paiements')
    contrat_partenaire = models.ForeignKey('contrats.ContratPartenaire', on_delete=models.CASCADE, null=True,
                                           blank=True, related_name='paiements')
    contrat_batterie = models.ForeignKey('contrats.ContratBatterie', on_delete=models.CASCADE, null=True, blank=True,
                                         related_name='paiements')

    type_contrat = models.CharField(max_length=20, choices=TYPE_CONTRAT_CHOICES)
    statut_paiement = models.CharField(max_length=20, choices=STATUS_CHOICES, default='complet')
    statut_paiement_batterie = models.CharField(max_length=20, choices=STATUS_CHOICES, default='complet')
    statut_paiement_moto = models.CharField(max_length=20, choices=STATUS_CHOICES, default='complet')
    user_agence = models.ForeignKey('authentication.UserAgence', on_delete=models.CASCADE, null=True, blank=True,
                                    related_name='paiements')

    est_penalite = models.BooleanField(default=False)
    inclut_penalites = models.BooleanField(default=False,
                                           help_text="Indique si ce paiement inclut des pénalités existantes")
    montant_penalites_inclus = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Heures de paiement pour déterminer les pénalités
    heure_paiement = models.TimeField(null=True, blank=True, help_text="Heure à laquelle le paiement a été effectué")

    notes = models.TextField(blank=True, null=True)

    # Utilisateur qui a enregistré le paiement
    enregistre_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                       related_name='paiements_enregistres')

    class Meta:
        db_table = 'payments_paiement'
        ordering = ['-date_paiement', '-date_enregistrement']

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and not self.est_penalite:
            # Si c'est un nouveau paiement (non pénalité), mettre à jour le contrat
            self._update_contract_amounts()
            self._check_contract_completion()

        super().save(*args, **kwargs)

    def _update_contract_amounts(self):
        """Met à jour les montants du contrat et réajuste la durée si nécessaire"""
        contract = self._get_associated_contract()
        if contract:
            # Mettre à jour les montants
            contract.montant_paye += self.montant_moto
            contract.montant_restant = contract.montant_total - contract.montant_paye
            contract.derniere_date_paiement = self.date_paiement

            # Réajuster la durée si nécessaire
            self._reajuster_duree_contrat(contract)

            contract.save()

    def _reajuster_duree_contrat(self, contract):
        """Réajuste la durée du contrat en fonction des paiements effectués"""
        if contract.montant_paye > 0 and contract.montant_total > 0:
            # Calculer le pourcentage payé
            pourcentage_paye = (contract.montant_paye / contract.montant_total) * 100

            # Calculer la durée écoulée depuis le début du contrat
            aujourdhui = date.today()
            duree_ecoulee = (aujourdhui - contract.date_debut).days

            # Si le pourcentage payé est différent du pourcentage de temps écoulé, ajuster la durée
            if duree_ecoulee > 0:
                pourcentage_temps = (duree_ecoulee / contract.duree_jours) * 100

                # Si le client paie plus vite que prévu, réduire la durée
                if pourcentage_paye > pourcentage_temps + 10:  # +10% de marge
                    nouvelle_duree = int(duree_ecoulee * (contract.montant_total / contract.montant_paye))
                    if nouvelle_duree < contract.duree_jours:
                        contract.duree_jours = nouvelle_duree
                        contract.duree_semaines = nouvelle_duree // 7
                        contract.date_fin = contract.date_debut + timedelta(days=nouvelle_duree)

                # Si le client paie plus lentement, augmenter la durée
                elif pourcentage_paye < pourcentage_temps - 10:  # -10% de marge
                    nouvelle_duree = int(duree_ecoulee * (contract.montant_total / contract.montant_paye))
                    if nouvelle_duree > contract.duree_jours:
                        contract.duree_jours = nouvelle_duree
                        contract.duree_semaines = nouvelle_duree // 7
                        contract.date_fin = contract.date_debut + timedelta(days=nouvelle_duree)

    def _check_contract_completion(self):
        """Vérifie si le contrat est terminé et met à jour son statut"""
        contract = self._get_associated_contract()
        if contract and contract.montant_paye >= contract.montant_total:
            # Vérifier qu'il n'y a pas de pénalités en attente
            penalites_en_attente = False

            if self.type_contrat == 'chauffeur':
                penalites_en_attente = Penalite.objects.filter(
                    contrat_chauffeur=contract,
                    statut='en_attente'
                ).exists()
            elif self.type_contrat == 'partenaire':
                penalites_en_attente = Penalite.objects.filter(
                    contrat_partenaire=contract,
                    statut='en_attente'
                ).exists()
            elif self.type_contrat == 'batterie':
                penalites_en_attente = Penalite.objects.filter(
                    contrat_batterie=contract,
                    statut='en_attente'
                ).exists()

            if not penalites_en_attente:
                contract.statut = 'terminé'
                contract.save()

    def _get_associated_contract(self):
        if self.contrat_chauffeur:
            return self.contrat_chauffeur
        elif self.contrat_partenaire:
            return self.contrat_partenaire
        elif self.contrat_batterie:
            return self.contrat_batterie
        return None

    def get_contract_link(self):
        """Retourne un lien vers le contrat associé pour les templates"""
        contract = self._get_associated_contract()
        if not contract:
            return None

        if self.type_contrat == 'chauffeur':
            return f"/contrats/chauffeur/{contract.id}/"
        elif self.type_contrat == 'partenaire':
            return f"/contrats/partenaire/{contract.id}/"
        elif self.type_contrat == 'batterie':
            return f"/contrats/batterie/{contract.id}/"
        return None

    def get_client_info(self):
        """Retourne les informations du client"""
        contract = self._get_associated_contract()
        if not contract:
            return {"nom": "Inconnu", "type": "Inconnu"}

        if self.type_contrat == 'chauffeur':
            chauffeur = None
            # On passe par l'association pour trouver le chauffeur lié
            if hasattr(contract, 'association') and contract.association and hasattr(contract.association,
                                                                                     'validated_user'):
                chauffeur = contract.association.validated_user
            if chauffeur:
                return {
                    "nom": f"{chauffeur.prenom} {chauffeur.nom}",
                    "type": "Chauffeur",
                    "id": chauffeur.id,
                    "telephone": chauffeur.phone
                }

        elif self.type_contrat == 'partenaire':
            return {
                "nom": f"{contract.partenaire.prenom} {contract.partenaire.nom}",
                "type": "Partenaire",
                "id": contract.partenaire.id,
                "telephone": contract.partenaire.phone
            }
        elif self.type_contrat == 'batterie':
            if contract.chauffeur:
                return {
                    "nom": f"{contract.chauffeur.prenom} {contract.chauffeur.nom}",
                    "type": "Chauffeur",
                    "id": contract.chauffeur.id,
                    "telephone": contract.chauffeur.phone
                }
            elif contract.partenaire:
                return {
                    "nom": f"{contract.partenaire.prenom} {contract.partenaire.nom}",
                    "type": "Partenaire",
                    "id": contract.partenaire.id,
                    "telephone": contract.partenaire.phone
                }
        return {"nom": "Inconnu", "type": "Inconnu"}

    def __str__(self):
        return f"Paiement {self.reference} - {self.montant_moto} FCFA"


class PaiementPenalite(models.Model):
    reference = models.CharField(max_length=100, unique=True)
    penalite = models.ForeignKey('Penalite', on_delete=models.CASCADE, related_name='paiements')  # ✅ one-to-many
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    date_paiement = models.DateField()
    date_enregistrement = models.DateTimeField(default=timezone.now)
    methode_paiement = models.CharField(
        max_length=50,
        choices=[
            ('espece', 'Espèces'),
            ('mobile_money', 'Mobile Money'),
            ('virement', 'Virement bancaire'),
            ('cheque', 'Chèque')
        ]
    )
    reference_transaction = models.CharField(max_length=100, blank=True, null=True)
    enregistre_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    user_agence = models.ForeignKey(
        'authentication.UserAgence',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='paiements_penalites'
    )


    def montant_total_paye(self):
        return self.paiements.aggregate(total=Sum('montant'))['total'] or 0

    def est_payee_completement(self):
        return self.montant_total_paye() >= self.montant

    class Meta:
        db_table = 'payments_paiementpenalite'
        ordering = ['-date_paiement', '-date_enregistrement']

    def __str__(self):
        return f"Pénalité payée {self.reference} - {self.montant} FCFA"



class Penalite(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('payee', 'Payée'),
        ('annulee', 'Annulée'),
        ('reportee', 'Reportée'),
    ]

    MOTIF_CHOICES = [
        ('retard_paiement', 'Retard de paiement (12h-14h)'),
        ('retard_grave', 'Retard grave de paiement (après 14h)'),
        ('absence_non_justifiee', 'Absence non justifiée'),
        ('autre', 'Autre'),
    ]

    TYPE_CONTRAT_CHOICES = [
        ('combine', 'Moto + Batterie'),
        ('batterie_seule', 'Batterie uniquement'),
    ]

    contrat_chauffeur = models.ForeignKey('contrats.ContratChauffeur', on_delete=models.CASCADE, null=True, blank=True,
                                          related_name='penalites')
    contrat_partenaire = models.ForeignKey('contrats.ContratPartenaire', on_delete=models.CASCADE, null=True,
                                           blank=True, related_name='penalites')
    contrat_batterie = models.ForeignKey('contrats.ContratBatterie', on_delete=models.CASCADE, null=True, blank=True,
                                         related_name='penalites')

    type_penalite = models.CharField(max_length=20, choices=TYPE_CONTRAT_CHOICES, default='combine')

    montant = models.DecimalField(max_digits=10, decimal_places=2)
    montant_payé = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date_creation = models.DateTimeField(default=timezone.now)
    motif = models.CharField(max_length=50, choices=MOTIF_CHOICES)
    description = models.TextField(blank=True, null=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')


    cree_par = models.ForeignKey('authentication.Employe', on_delete=models.SET_NULL, null=True, related_name='penalites_creees')

    raison_annulation = models.TextField(blank=True, null=True)
    date_modification = models.DateTimeField(null=True, blank=True)
    modifie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='penalites_modifiees',
        verbose_name="Modifié par"
    )  # Champs pour tracer les paiements manqués
    date_paiement_manque = models.DateField(null=True, blank=True,
                                            help_text="Date du paiement qui n'a pas été effectué à temps")
    contrat_reference = models.CharField(max_length=100, blank=True, null=True,
                                         help_text="Référence du contrat concerné")

    # Champ pour la raison du pardon/annulation
    raison_annulation = models.TextField(blank=True, null=True,
                                         help_text="Raison du pardon ou de l'annulation de la pénalité")
    pardonnee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='penalites_pardonnees',
        verbose_name="Pardonnée par"
    )
    date_pardon = models.DateTimeField(null=True, blank=True, help_text="Date à laquelle la pénalité a été pardonnée")

    class Meta:
        db_table = 'payments_penalite'
        ordering = ['-date_creation']

    def get_client(self):
        if self.contrat_chauffeur:
            return self.contrat_chauffeur.association.validated_user
        elif self.contrat_partenaire:
            return self.contrat_partenaire.partenaire
        elif self.contrat_batterie:
            if self.contrat_batterie.chauffeur:
                return self.contrat_batterie.chauffeur
            elif self.contrat_batterie.partenaire:
                return self.contrat_batterie.partenaire
        return None

    def get_montant_contrat(self):
        """Retourne le montant du paiement attendu pour le contrat associé"""
        if self.contrat_chauffeur:
            return self.contrat_chauffeur.montant_par_paiement
        elif self.contrat_partenaire:
            return self.contrat_partenaire.montant_par_paiement
        elif self.contrat_batterie:
            return self.contrat_batterie.montant_par_paiement
        return Decimal('0.00')

    def montant_total_paye(self):
        return self.paiements.aggregate(total=Sum('montant'))['total'] or 0

    def est_payee_completement(self):
        return self.montant_total_paye() >= self.montant

    def get_contract_type_display(self):
        """Retourne le type de contrat pour l'affichage"""
        if self.contrat_chauffeur:
            return "Chauffeur"
        elif self.contrat_partenaire:
            return "Partenaire"
        elif self.contrat_batterie:
            return "Batterie"
        return "Inconnu"

    def get_contract_reference(self):
        """Retourne la référence du contrat associé"""
        if self.contrat_chauffeur:
            return self.contrat_chauffeur.reference
        elif self.contrat_partenaire:
            return self.contrat_partenaire.reference
        elif self.contrat_batterie:
            return self.contrat_batterie.reference
        return self.contrat_reference  # Fallback sur le champ enregistré

    def __str__(self):
        client = self.get_client()
        if client:
            return f"Pénalité {self.id} - {client.prenom} {client.nom} - {self.montant} FCFA"
        return f"Pénalité {self.id} - {self.montant} FCFA"




class NotificationPaiement(models.Model):
    STATUT_CHOICES = [
        ('programmee', 'Programmée'),
        ('envoyee', 'Envoyée'),
        ('echouee', 'Échouée'),
    ]

    TYPE_CHOICES = [
        ('rappel', 'Rappel de paiement'),
        ('retard', 'Alerte de retard'),
        ('penalite', 'Notification de pénalité'),
        ('confirmation', 'Confirmation de paiement'),
    ]

    chauffeur = models.ForeignKey(ValidatedUser, on_delete=models.CASCADE)
    partenaire = models.ForeignKey('contrats.Partenaire', on_delete=models.CASCADE, null=True, blank=True,
                                   related_name='notifications')

    type_notification = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.TextField()
    date_programmee = models.DateTimeField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='programmee')

    date_envoi = models.DateTimeField(null=True, blank=True)
    raison_echec = models.TextField(null=True, blank=True)

    contrat_chauffeur = models.ForeignKey('contrats.ContratChauffeur', on_delete=models.CASCADE, null=True, blank=True,
                                          related_name='notifications')
    contrat_partenaire = models.ForeignKey('contrats.ContratPartenaire', on_delete=models.CASCADE, null=True,
                                           blank=True, related_name='notifications')
    contrat_batterie = models.ForeignKey('contrats.ContratBatterie', on_delete=models.CASCADE, null=True, blank=True,
                                         related_name='notifications')

    penalite = models.ForeignKey('Penalite', on_delete=models.CASCADE, null=True, blank=True,
                                 related_name='notifications')

    # Canal de notification
    canal_notification = models.CharField(max_length=20, choices=[
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
        ('app', 'Application mobile'),
        ('email', 'Email'),
        ('appel', 'Appel téléphonique'),
    ], default='sms')

    # Informations de suivi
    est_lue = models.BooleanField(default=False)
    date_lecture = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payments_notificationpaiement'
        ordering = ['-date_programmee']

    def get_recipient_number(self):
        """Retourne le numéro de téléphone du destinataire"""
        if self.chauffeur:
            return self.chauffeur.phone
        elif self.partenaire:
            return self.partenaire.phone
        return None

    def __str__(self):
        return f"Notification {self.id} - {self.get_type_notification_display()}"


class Swap(models.Model):
    id = models.BigAutoField(primary_key=True)
    battery_moto_user_association_id = models.BigIntegerField()
    battery_in_id = models.BigIntegerField()
    battery_out_id = models.BigIntegerField()
    swap_price = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    swap_date = models.DateTimeField()
    nom = models.CharField(max_length=255, null=True)
    prenom = models.CharField(max_length=255, null=True)
    phone = models.CharField(max_length=20, null=True)
    created_at = models.DateTimeField(null=True)
    updated_at = models.DateTimeField(null=True)
    battery_out_soc = models.CharField(max_length=255, null=True)
    battery_in_soc = models.CharField(max_length=255, null=True)
    agent_user_id = models.BigIntegerField()
    id_agence = models.BigIntegerField()

    class Meta:
        db_table = 'swaps'
        managed = False  # important : Django ne gère pas cette table

    def __str__(self):
        return f"Swap {self.id} - {self.swap_date} - {self.swap_price} FCFA"


class ReglePenalite(models.Model):
    """Modèle pour configurer les règles de pénalités"""
    TYPE_CONTRAT_CHOICES = [
        ('combine', 'Moto + Batterie'),
        ('batterie_seule', 'Batterie uniquement'),
    ]

    nom_regle = models.CharField(max_length=100)
    type_contrat = models.CharField(max_length=20, choices=TYPE_CONTRAT_CHOICES)

    # Définition des seuils horaires et montants
    heure_debut_leger = models.TimeField(help_text="Heure de début pour les pénalités légères (ex: 12:01)")
    heure_debut_grave = models.TimeField(help_text="Heure de début pour les pénalités graves (ex: 14:01)")

    montant_penalite_leger = models.DecimalField(max_digits=10, decimal_places=2,
                                                 help_text="Montant de la pénalité légère")
    montant_penalite_grave = models.DecimalField(max_digits=10, decimal_places=2,
                                                 help_text="Montant de la pénalité grave")
    montant_penalite_jour_manque = models.DecimalField(max_digits=10, decimal_places=2,
                                                       help_text="Montant de la pénalité pour jour manqué",
                                                       default=Decimal('5000.00'))

    est_active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments_regle_penalite'

    def __str__(self):
        return f"Règle de pénalité: {self.nom_regle} ({self.get_type_contrat_display()})"

    @classmethod
    def get_penalite_applicable(cls, type_contrat, heure_paiement=None, jours_retard=0):
        """
        Détermine le montant de pénalité applicable selon le type de contrat, l'heure et/ou jours de retard

        Args:
            type_contrat: 'combine' ou 'batterie_seule'
            heure_paiement: objet time représentant l'heure du paiement (facultatif)
            jours_retard: nombre de jours de retard (facultatif)

        Returns:
            Tuple (montant, motif)
        """
        # Tenter de récupérer la règle active pour ce type de contrat
        try:
            regle = cls.objects.filter(type_contrat=type_contrat, est_active=True).first()

            if not regle:
                # Valeurs par défaut si aucune règle n'est configurée
                if jours_retard > 0:
                    return Decimal('5000.00'), 'retard_paiement'

                if type_contrat == 'combine':
                    if heure_paiement and heure_paiement >= time(13, 1):
                        return Decimal('5000.00'), 'retard_grave'
                else:  # batterie_seule
                    if heure_paiement and heure_paiement >= time(13, 1):
                        return Decimal('2500.00'), 'retard_grave'

                return Decimal('0.00'), None

            # Gérer d'abord les jours de retard
            if jours_retard > 0:
                return regle.montant_penalite_jour_manque, 'retard_paiement'

            # Utiliser les valeurs de la règle configurée pour le même jour
            if heure_paiement and heure_paiement >= regle.heure_debut_grave:
                return regle.montant_penalite_grave, 'retard_grave'
            elif heure_paiement and heure_paiement >= regle.heure_debut_leger:
                return regle.montant_penalite_leger, 'retard_paiement'

            return Decimal('0.00'), None

        except Exception:
            # En cas d'erreur, utiliser les valeurs par défaut
            if jours_retard > 0:
                return Decimal('5000.00'), 'retard_paiement'

            if type_contrat == 'combine':
                if heure_paiement and heure_paiement >= time(13, 1):
                    return Decimal('5000.00'), 'retard_grave'
            else:  # batterie_seule
                if heure_paiement and heure_paiement >= time(13, 1):
                    return Decimal('2500.00'), 'retard_grave'
            return Decimal('0.00'), None


