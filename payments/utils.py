# À ajouter dans payments/utils.py

from django.utils import timezone
from datetime import date, time, timedelta
from decimal import Decimal
from django.db.models import Q

from contrats.models import ContratChauffeur, ContratPartenaire, ContratBatterie, CongesChauffeur
from .models import Paiement, Penalite, ReglePenalite


def creer_penalites_manquees_automatiquement(jours_max=30):
    """
    Crée automatiquement toutes les pénalités manquées pour les jours précédents
    jusqu'à jours_max jours en arrière
    """
    aujourd_hui = date.today()
    penalites_creees = 0

    # Pour chaque jour depuis jours_max jours
    for i in range(1, jours_max + 1):
        date_a_verifier = aujourd_hui - timedelta(days=i)

        # Contrats chauffeur
        contrats_chauffeur = ContratChauffeur.objects.filter(
            statut='actif',
            date_debut__lte=date_a_verifier
        )

        for contrat in contrats_chauffeur:
            # Vérifier si c'était un jour de paiement
            if _est_jour_de_paiement(contrat, date_a_verifier):
                # Vérifier s'il était en congé
                try:
                    est_en_conge = CongesChauffeur.objects.filter(
                        contrat=contrat,
                        date_debut__lte=date_a_verifier,
                        date_fin__gte=date_a_verifier,
                        statut__in=['approuvé', 'planifié', 'en_cours']
                    ).exists()
                except:
                    est_en_conge = False

                if not est_en_conge:
                    # Vérifier si le paiement a été effectué
                    paiement_existe = Paiement.objects.filter(
                        contrat_chauffeur=contrat,
                        date_paiement=date_a_verifier,
                        est_penalite=False
                    ).exists()

                    # Vérifier si une pénalité existe déjà
                    penalite_existe = Penalite.objects.filter(
                        contrat_chauffeur=contrat,
                        date_paiement_manque=date_a_verifier
                    ).exists()

                    # Si pas de paiement et pas de pénalité, créer la pénalité
                    if not paiement_existe and not penalite_existe:
                        try:
                            # Déterminer le type de pénalité
                            type_penalite = 'combine' if ContratBatterie.objects.filter(
                                chauffeur=contrat.chauffeur,
                                statut='actif'
                            ).exists() else 'batterie_seule'

                            # Calculer le montant selon le nombre de jours de retard
                            jours_retard = (aujourd_hui - date_a_verifier).days
                            if jours_retard <= 1:
                                montant_penalite = Decimal('2000.00') if type_penalite == 'combine' else Decimal(
                                    '500.00')
                                motif = 'retard_leger'
                            elif jours_retard <= 3:
                                montant_penalite = Decimal('3000.00') if type_penalite == 'combine' else Decimal(
                                    '1000.00')
                                motif = 'retard_grave'
                            else:
                                montant_penalite = Decimal('5000.00') if type_penalite == 'combine' else Decimal(
                                    '2000.00')
                                motif = 'retard_paiement'

                            Penalite.objects.create(
                                contrat_chauffeur=contrat,
                                contrat_reference=contrat.reference,
                                type_penalite=type_penalite,
                                montant=montant_penalite,
                                motif=motif,
                                description=f"Pénalité automatique pour paiement manqué du {date_a_verifier.strftime('%d/%m/%Y')} - {jours_retard} jours de retard",
                                statut='en_attente',
                                date_paiement_manque=date_a_verifier,
                                cree_par=None  # Créé automatiquement
                            )
                            penalites_creees += 1

                        except Exception as e:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"Erreur création pénalité chauffeur {contrat.id} pour {date_a_verifier}: {e}")

        # Contrats partenaire
        contrats_partenaire = ContratPartenaire.objects.filter(
            statut='actif',
            date_debut__lte=date_a_verifier
        )

        for contrat in contrats_partenaire:
            # Vérifier si c'était un jour de paiement
            if _est_jour_de_paiement(contrat, date_a_verifier):
                # Vérifier si le paiement a été effectué
                paiement_existe = Paiement.objects.filter(
                    contrat_partenaire=contrat,
                    date_paiement=date_a_verifier,
                    est_penalite=False
                ).exists()

                # Vérifier si une pénalité existe déjà
                penalite_existe = Penalite.objects.filter(
                    contrat_partenaire=contrat,
                    date_paiement_manque=date_a_verifier
                ).exists()

                # Si pas de paiement et pas de pénalité, créer la pénalité
                if not paiement_existe and not penalite_existe:
                    try:
                        # Déterminer le type de pénalité
                        type_penalite = 'combine' if ContratBatterie.objects.filter(
                            partenaire=contrat.partenaire,
                            statut='actif'
                        ).exists() else 'batterie_seule'

                        # Calculer le montant selon le nombre de jours de retard
                        jours_retard = (aujourd_hui - date_a_verifier).days
                        if jours_retard <= 1:
                            montant_penalite = Decimal('2000.00') if type_penalite == 'combine' else Decimal('500.00')
                            motif = 'retard_leger'
                        elif jours_retard <= 3:
                            montant_penalite = Decimal('3000.00') if type_penalite == 'combine' else Decimal('1000.00')
                            motif = 'retard_grave'
                        else:
                            montant_penalite = Decimal('5000.00') if type_penalite == 'combine' else Decimal('2000.00')
                            motif = 'retard_paiement'

                        Penalite.objects.create(
                            contrat_partenaire=contrat,
                            contrat_reference=contrat.reference,
                            type_penalite=type_penalite,
                            montant=montant_penalite,
                            motif=motif,
                            description=f"Pénalité automatique pour paiement manqué du {date_a_verifier.strftime('%d/%m/%Y')} - {jours_retard} jours de retard",
                            statut='en_attente',
                            date_paiement_manque=date_a_verifier,
                            cree_par=None  # Créé automatiquement
                        )
                        penalites_creees += 1

                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Erreur création pénalité partenaire {contrat.id} pour {date_a_verifier}: {e}")

        # Contrats batterie standalone
        contrats_batterie = ContratBatterie.objects.filter(
            statut='actif',
            date_debut__lte=date_a_verifier
        )

        for contrat in contrats_batterie:
            # Vérifier si c'est un contrat batterie standalone
            is_standalone = True

            if contrat.chauffeur:
                if ContratChauffeur.objects.filter(chauffeur=contrat.chauffeur, statut='actif').exists():
                    is_standalone = False

            if contrat.partenaire:
                if ContratPartenaire.objects.filter(partenaire=contrat.partenaire, statut='actif').exists():
                    is_standalone = False

            if is_standalone and _est_jour_de_paiement(contrat, date_a_verifier):
                # Vérifier si le paiement a été effectué
                paiement_existe = Paiement.objects.filter(
                    contrat_batterie=contrat,
                    date_paiement=date_a_verifier,
                    est_penalite=False
                ).exists()

                # Vérifier si une pénalité existe déjà
                penalite_existe = Penalite.objects.filter(
                    contrat_batterie=contrat,
                    date_paiement_manque=date_a_verifier
                ).exists()

                # Si pas de paiement et pas de pénalité, créer la pénalité
                if not paiement_existe and not penalite_existe:
                    try:
                        # Calculer le montant selon le nombre de jours de retard
                        jours_retard = (aujourd_hui - date_a_verifier).days
                        if jours_retard <= 1:
                            montant_penalite = Decimal('500.00')
                            motif = 'retard_leger'
                        elif jours_retard <= 3:
                            montant_penalite = Decimal('1000.00')
                            motif = 'retard_grave'
                        else:
                            montant_penalite = Decimal('2000.00')
                            motif = 'retard_paiement'

                        Penalite.objects.create(
                            contrat_batterie=contrat,
                            contrat_reference=contrat.reference,
                            type_penalite='batterie_seule',
                            montant=montant_penalite,
                            motif=motif,
                            description=f"Pénalité automatique pour paiement manqué du {date_a_verifier.strftime('%d/%m/%Y')} - {jours_retard} jours de retard",
                            statut='en_attente',
                            date_paiement_manque=date_a_verifier,
                            cree_par=None  # Créé automatiquement
                        )
                        penalites_creees += 1

                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Erreur création pénalité batterie {contrat.id} pour {date_a_verifier}: {e}")

    return penalites_creees


def verifier_et_appliquer_penalites_si_necessaire():
    """
    Fonction appelée depuis centre_paiements pour vérifier et appliquer les pénalités
    """
    return creer_penalites_manquees_automatiquement(jours_max=30)


def _est_jour_de_paiement(contrat, date_ref):
    """
    Détermine si un contrat a un paiement prévu pour la date de référence
    selon sa fréquence de paiement
    """
    # Date de début du contrat
    date_debut = contrat.date_debut

    # Nombre de jours depuis le début du contrat
    jours_depuis_debut = (date_ref - date_debut).days

    # Si date_ref est antérieure à la date de début, pas de paiement
    if jours_depuis_debut < 0:
        return False

    # Si la date est après la date de fin du contrat, pas de paiement
    if hasattr(contrat, 'date_fin') and contrat.date_fin and date_ref > contrat.date_fin:
        return False

    # Vérifier selon la fréquence
    if contrat.frequence_paiement == 'journalier':
        # Paiement tous les jours sauf dimanche (jour 6)
        return date_ref.weekday() < 6

    elif contrat.frequence_paiement == 'hebdomadaire':
        # Paiement le même jour de la semaine que la date de début
        return date_ref.weekday() == date_debut.weekday()

    elif contrat.frequence_paiement == 'mensuel':
        # Paiement le même jour du mois que la date de début
        # Gestion des mois avec moins de jours
        if date_ref.day == date_debut.day:
            return True

        # Si on est le dernier jour du mois et que le jour de début est supérieur au nombre de jours de ce mois
        import calendar
        _, dernier_jour = calendar.monthrange(date_ref.year, date_ref.month)
        if date_ref.day == dernier_jour and date_debut.day > dernier_jour:
            return True

        return False

    elif contrat.frequence_paiement == 'trimestriel':
        # Paiement tous les 3 mois le même jour du mois que la date de début
        mois_depuis_debut = (date_ref.year - date_debut.year) * 12 + date_ref.month - date_debut.month

        if mois_depuis_debut % 3 == 0:
            # Même logique que pour le paiement mensuel
            if date_ref.day == date_debut.day:
                return True

            import calendar
            _, dernier_jour = calendar.monthrange(date_ref.year, date_ref.month)
            if date_ref.day == dernier_jour and date_debut.day > dernier_jour:
                return True

        return False

    return False

