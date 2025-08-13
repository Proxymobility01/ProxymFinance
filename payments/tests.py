from django.test import TestCase
from datetime import date, timedelta
from contrats.models import ContratChauffeur, AssociationUserMoto, ValidatedUser, MotosValides, CongesChauffeur

class ContratDateFinTestCase(TestCase):
    def setUp(self):
        self.user = ValidatedUser.objects.create(nom="Test", prenom="User", email="test@proxym.cm", phone="123456789", domicile="Yaoundé", user_unique_id="ABC123")
        self.moto = MotosValides.objects.create(vin="VIN123", model="MotoX", gps_imei="IMEI")
        self.association = AssociationUserMoto.objects.create(validated_user=self.user, moto_valide=self.moto)

        self.contrat = ContratChauffeur.objects.create(
            association=self.association,
            reference="REF-001",
            montant_total=10000,
            montant_paye=0,
            montant_engage=1000,
            montant_par_paiement=1000,
            date_signature=date.today(),
            date_enregistrement=date.today(),
            date_debut=date.today(),
            duree_semaines=4,
            duree_jours=28,
            date_fin=date.today() + timedelta(days=28),
            statut='actif',
        )

    def test_prolongation_date_fin(self):
        # Ajout d'un congé de 3 jours
        jours_conge = 3
        self.contrat.prolonger_duree(jours_conge)
        self.contrat.refresh_from_db()
        date_attendue = self.contrat.date_debut + timedelta(days=28 + jours_conge)
        self.assertEqual(self.contrat.date_fin, date_attendue)


from payments.models import Paiement

class ContratClotureTestCase(TestCase):
    def setUp(self):
        # Reprends le setUp précédent (user, moto, association, contrat)
        self.user = ValidatedUser.objects.create(nom="Test", prenom="User", email="test@proxym.cm", phone="123456789", domicile="Yaoundé", user_unique_id="ABC123")
        self.moto = MotosValides.objects.create(vin="VIN123", model="MotoX", gps_imei="IMEI")
        self.association = AssociationUserMoto.objects.create(validated_user=self.user, moto_valide=self.moto)
        self.contrat = ContratChauffeur.objects.create(
            association=self.association,
            reference="REF-002",
            montant_total=5000,
            montant_paye=0,
            montant_engage=1000,
            montant_par_paiement=1000,
            date_signature=date.today(),
            date_enregistrement=date.today(),
            date_debut=date.today(),
            duree_semaines=2,
            duree_jours=14,
            date_fin=date.today() + timedelta(days=14),
            statut='actif',
        )

    def test_cloture_sans_penalite(self):
        # Paie la totalité du contrat
        Paiement.objects.create(
            reference="PAY-001",
            montant_moto=5000,
            montant_batterie=0,
            montant_total=5000,
            date_paiement=date.today(),
            methode_paiement="espece",
            contrat_chauffeur=self.contrat,
            type_contrat="chauffeur_batterie",
            est_penalite=False
        )
        self.contrat.refresh_from_db()
        self.assertEqual(self.contrat.statut, "terminé")




from payments.models import Penalite

class ContratPenaliteTestCase(TestCase):
    def setUp(self):
        self.user = ValidatedUser.objects.create(nom="Test", prenom="User", email="test@proxym.cm", phone="123456789", domicile="Yaoundé", user_unique_id="ABC123")
        self.moto = MotosValides.objects.create(vin="VIN123", model="MotoX", gps_imei="IMEI")
        self.association = AssociationUserMoto.objects.create(validated_user=self.user, moto_valide=self.moto)
        self.contrat = ContratChauffeur.objects.create(
            association=self.association,
            reference="REF-003",
            montant_total=3000,
            montant_paye=0,
            montant_engage=1000,
            montant_par_paiement=1000,
            date_signature=date.today(),
            date_enregistrement=date.today(),
            date_debut=date.today(),
            duree_semaines=1,
            duree_jours=7,
            date_fin=date.today() + timedelta(days=7),
            statut='actif',
        )
        # Créer une pénalité EN ATTENTE
        self.penalite = Penalite.objects.create(
            contrat_chauffeur=self.contrat,
            montant=1000,
            type_penalite="combine",
            motif="retard_paiement",
            description="Retard paiement",
            statut="en_attente"
        )

    def test_cloture_bloquee_par_penalite(self):
        # Paie la totalité du contrat
        Paiement.objects.create(
            reference="PAY-002",
            montant_moto=3000,
            montant_batterie=0,
            montant_total=3000,
            date_paiement=date.today(),
            methode_paiement="espece",
            contrat_chauffeur=self.contrat,
            type_contrat="chauffeur_batterie",
            est_penalite=False
        )
        self.contrat.refresh_from_db()
        # Le statut doit rester actif, car la pénalité n'est pas réglée
        self.assertEqual(self.contrat.statut, "actif")

    def test_cloture_apres_reglement_penalite(self):
        # On règle la pénalité
        self.penalite.statut = "payee"
        self.penalite.save()
        # Paie la totalité du contrat
        Paiement.objects.create(
            reference="PAY-003",
            montant_moto=3000,
            montant_batterie=0,
            montant_total=3000,
            date_paiement=date.today(),
            methode_paiement="espece",
            contrat_chauffeur=self.contrat,
            type_contrat="chauffeur_batterie",
            est_penalite=False
        )
        self.contrat.refresh_from_db()
        # Le statut doit passer à terminé
        self.assertEqual(self.contrat.statut, "terminé")
