# À ajouter dans payments/utils.py

from django.utils import timezone
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from django.db.models import Q
from contrats.models import ContratChauffeur, ContratPartenaire, ContratBatterie, CongesChauffeur
from .models import Paiement, Penalite, ReglePenalite
from django.db import transaction



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

    return creer_penalites_manquees_automatiquement(jours_max=30)
    """
    """
    ➜ Version adaptée : ne traite QUE la date du jour et UNIQUEMENT après 12:01.
    Idempotent. Ne crée pas de rétroactifs.
    """
    return appliquer_penalites_du_jour()


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


# --- Pénalités du jour (après 12:01), idempotent ---

def _has_payment_today(contrat, today):
    """Paiement (hors pénalité) déjà effectué aujourd'hui ?"""
    if isinstance(contrat, ContratChauffeur):
        return Paiement.objects.filter(
            contrat_chauffeur=contrat, date_paiement=today, est_penalite=False
        ).exists()
    if isinstance(contrat, ContratPartenaire):
        return Paiement.objects.filter(
            contrat_partenaire=contrat, date_paiement=today, est_penalite=False
        ).exists()
    # ContratBatterie
    return Paiement.objects.filter(
        contrat_batterie=contrat, date_paiement=today, est_penalite=False
    ).exists()


def _penalty_exists_for_today(contrat, today):
    """Évite les doublons : une pénalité existe déjà pour aujourd'hui ?"""
    if isinstance(contrat, ContratChauffeur):
        return Penalite.objects.filter(
            contrat_chauffeur=contrat, date_paiement_manque=today
        ).exists()
    if isinstance(contrat, ContratPartenaire):
        return Penalite.objects.filter(
            contrat_partenaire=contrat, date_paiement_manque=today
        ).exists()
    # ContratBatterie
    return Penalite.objects.filter(
        contrat_batterie=contrat, date_paiement_manque=today
    ).exists()


def _create_penalty(contrat, type_penalite, montant, motif, today, cree_par=None, description=None):
    """Crée une pénalité pour le contrat, datée d'aujourd'hui."""
    description = description or f"Pénalité automatique pour retard du {today.strftime('%d/%m/%Y')}"
    if isinstance(contrat, ContratChauffeur):
        return Penalite.objects.create(
            contrat_chauffeur=contrat,
            contrat_reference=contrat.reference,
            type_penalite=type_penalite,
            montant=montant,
            motif=motif,
            description=description,
            statut='en_attente',
            date_paiement_manque=today,
            cree_par=cree_par
        )
    if isinstance(contrat, ContratPartenaire):
        return Penalite.objects.create(
            contrat_partenaire=contrat,
            contrat_reference=contrat.reference,
            type_penalite=type_penalite,
            montant=montant,
            motif=motif,
            description=description,
            statut='en_attente',
            date_paiement_manque=today,
            cree_par=cree_par
        )
    # ContratBatterie
    return Penalite.objects.create(
        contrat_batterie=contrat,
        contrat_reference=contrat.reference,
        type_penalite=type_penalite,
        montant=montant,
        motif=motif,
        description=description,
        statut='en_attente',
        date_paiement_manque=today,
        cree_par=cree_par
    )


def _is_battery_standalone(contrat_bat: ContratBatterie) -> bool:
    """Un contrat batterie 'standalone' = pas couvert par un contrat chauffeur/partenaire actif."""
    if contrat_bat.chauffeur and ContratChauffeur.objects.filter(
        association__validated_user=contrat_bat.chauffeur, statut='actif'
    ).exists():
        return False
    if contrat_bat.partenaire and ContratPartenaire.objects.filter(
        partenaire=contrat_bat.partenaire, statut='actif'
    ).exists():
        return False
    return True


def appliquer_penalites_du_jour(run_dt=None, user=None) -> int:
    """
    Applique les pénalités UNIQUEMENT pour la date du jour, et UNIQUEMENT après 12:01 (Africa/Douala).
    Idempotent : ne recrée pas si paiement déjà fait ou pénalité déjà existante pour aujourd'hui.
    Retourne le nombre de pénalités créées.
    """
    tz = timezone.get_current_timezone()
    now = timezone.localtime(run_dt, tz) if run_dt else timezone.localtime()
    today = now.date()

    # 12:01 locale Cameroun (TIME_ZONE = 'Africa/Douala')
    cutoff = timezone.make_aware(datetime.combine(today, time(12, 1)), tz)
    if now < cutoff:
        return 0

    created = 0

    # 1) Chauffeurs
    # 1) Chauffeurs
    for contrat in ContratChauffeur.objects.filter(statut='actif', date_debut__lte=today):
        if not _est_jour_de_paiement(contrat, today):
            continue

        # Congé => pas de pénalité
        try:
            est_en_conge = CongesChauffeur.objects.filter(
                contrat=contrat,
                date_debut__lte=today,
                date_fin__gte=today,
                statut__in=['approuvé', 'planifié', 'en_cours']
            ).exists()
        except Exception:
            est_en_conge = False
        if est_en_conge:
            continue

        if _has_payment_today(contrat, today) or _penalty_exists_for_today(contrat, today):
            continue

        # ✅ Récupération correcte du "chauffeur"
        chauffeur_user = getattr(contrat.association, 'validated_user', None)

        # ✅ Vérifier s’il a un contrat batterie actif
        has_battery = False
        if chauffeur_user:
            has_battery = ContratBatterie.objects.filter(
                chauffeur=chauffeur_user,
                statut='actif'
            ).exists()

        type_penalite = 'combine' if has_battery else 'batterie_seule'

        montant, motif = ReglePenalite.get_penalite_applicable(
            type_penalite,
            heure_paiement=now.time(),
            jours_retard=0
        )

        if montant and montant > 0 and motif:
            with transaction.atomic():
                if _has_payment_today(contrat, today) or _penalty_exists_for_today(contrat, today):
                    continue
                _create_penalty(contrat, type_penalite, montant, motif, today, cree_par=user)
                created += 1

    # 2) Partenaires
    for contrat in ContratPartenaire.objects.filter(statut='actif', date_debut__lte=today):
        if not _est_jour_de_paiement(contrat, today):
            continue
        if _has_payment_today(contrat, today) or _penalty_exists_for_today(contrat, today):
            continue

        type_penalite = 'combine' if ContratBatterie.objects.filter(partenaire=contrat.partenaire, statut='actif').exists() else 'batterie_seule'
        montant, motif = ReglePenalite.get_penalite_applicable(type_penalite, heure_paiement=now.time(), jours_retard=0)
        if montant and montant > 0 and motif:
            with transaction.atomic():
                if _has_payment_today(contrat, today) or _penalty_exists_for_today(contrat, today):
                    continue
                _create_penalty(contrat, type_penalite, montant, motif, today, cree_par=user)
                created += 1

    # 3) Batteries standalone
    for contrat in ContratBatterie.objects.filter(statut='actif', date_debut__lte=today):
        if not _is_battery_standalone(contrat):
            continue
        if not _est_jour_de_paiement(contrat, today):
            continue
        if _has_payment_today(contrat, today) or _penalty_exists_for_today(contrat, today):
            continue

        montant, motif = ReglePenalite.get_penalite_applicable('batterie_seule', heure_paiement=now.time(), jours_retard=0)
        if montant and montant > 0 and motif:
            with transaction.atomic():
                if _has_payment_today(contrat, today) or _penalty_exists_for_today(contrat, today):
                    continue
                _create_penalty(contrat, 'batterie_seule', montant, motif, today, cree_par=user)
                created += 1

    return created




