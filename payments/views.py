from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count, Q, F, Case, Value, DecimalField

from django.http import JsonResponse, HttpResponse
from datetime import datetime, timedelta, date, time
from django.urls import reverse
from django.core.paginator import Paginator
from decimal import Decimal
from .models import PaiementPenalite

import uuid
import json
import csv


from contrats.models import ValidatedUser, Partenaire, ContratChauffeur, ContratPartenaire, ContratBatterie
from .models import Paiement, Penalite, NotificationPaiement, ReglePenalite, Swap
from .forms import (
    PaiementForm, PaiementRapideForm, PenaliteForm, GestionPenaliteForm,
    GestionPenalitesMultiplesForm, ReglePenaliteForm, RechercheAvanceeForm
)

from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from datetime import date, datetime, time
from decimal import Decimal
# Ajouter ces imports en haut du fichier si pas déjà présents
from django.db import transaction
from .models import Paiement, Penalite, ReglePenalite
from .utils import _est_jour_de_paiement
from django.db.models import Count, Q
# + à importer en haut du fichier
from django.utils.dateparse import parse_date
from datetime import time
from django.utils import timezone


def centre_paiements(request):
    """Centre de paiements unifié avec application automatique des pénalités"""
    dt_now = timezone.localtime()
    # -- AJOUT: lire la date choisie dans l'URL
    selected_date_str = request.GET.get('date')
    selected_date = parse_date(selected_date_str) if selected_date_str else None

    aujourd_hui = (selected_date or dt_now.date())
    is_today = (aujourd_hui == timezone.localdate())

    # si on consulte une date passée/future, on fige l'heure du jour à 23:59:59
    heure_actuelle = dt_now.time() if is_today else time(23, 59, 59)
    heure_limite = time(13, 0)

    # ⚠️ (option sûr) : ne déclencher l’auto-création de pénalités QUE pour aujourd’hui
    if is_today:
        try:
            created = run_penalties_if_due()
            if created:
                messages.info(request, f"{created} pénalité(s) automatique(s) appliquée(s).")
        except Exception:
            pass

        try:
            from .utils import verifier_et_appliquer_penalites_si_necessaire
            penalites_creees = verifier_et_appliquer_penalites_si_necessaire()
            if penalites_creees > 0:
                messages.info(request,
                              f"{penalites_creees} pénalité(s) automatique(s) ont été appliquées pour les paiements manqués.")
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Erreur lors de l'application automatique des pénalités: {e}")

    # Récupérer tous les contrats actifs
    contrats_chauffeur = ContratChauffeur.objects.filter(statut='actif')
    contrats_partenaire = ContratPartenaire.objects.filter(statut='actif')
    contrats_batterie = ContratBatterie.objects.filter(statut='actif')


    # Récupérer les paiements de la journée
    paiements_aujourd_hui = Paiement.objects.filter(date_paiement=aujourd_hui)

    # Récupérer les pénalités actives
    penalites_actives = Penalite.objects.filter(statut='en_attente')

    # Calculer les paiements attendus aujourd'hui selon la fréquence
    paiements_attendus = []

    # Variable pour compter les pénalités créées automatiquement
    penalites_auto_creees = 0

    # Pour les contrats chauffeur
    for contrat in contrats_chauffeur:
        if _est_jour_de_paiement(contrat, aujourd_hui):
            montant = contrat.montant_par_paiement

            # Vérifier s'il y a un contrat batterie associé
            contrat_batterie = None
            contrat_batterie = None
            try:
                chauffeur_vu = contrat.association.validated_user  # <-- clé correcte
                contrat_batterie = ContratBatterie.objects.filter(
                    chauffeur=chauffeur_vu,
                    statut='actif'
                ).first()
            except:
                contrat_batterie = None


            montant_batterie = Decimal('0.00')
            if contrat_batterie and _est_jour_de_paiement(contrat_batterie, aujourd_hui):
                montant_batterie = contrat_batterie.montant_par_paiement

            # Vérifier si le paiement a déjà été effectué aujourd'hui
            deja_paye = paiements_aujourd_hui.filter(
                contrat_chauffeur=contrat, est_penalite=False
            ).exists()

            if not deja_paye:
                # Vérifier s'il y a des pénalités en attente
                penalites = penalites_actives.filter(contrat_chauffeur=contrat)
                montant_penalites = penalites.aggregate(total=Sum('montant'))['total'] or 0


                # Déterminer si c'est un retard et le niveau de pénalité applicable
                penalite_applicable = Decimal('0.00')
                motif_penalite = None

                # Vérifier s'il y a une pénalité pour aujourd'hui
                penalite_du_jour = penalites.filter(date_paiement_manque=aujourd_hui).first()

                if heure_actuelle >= time(12, 1) and not penalite_du_jour:
                    type_contrat = 'combine' if contrat_batterie else 'batterie_seule'
                    penalite_applicable, motif_penalite = ReglePenalite.get_penalite_applicable(
                        type_contrat, heure_actuelle
                    )

                    # CRÉER AUTOMATIQUEMENT LA PÉNALITÉ EN BASE SI ELLE N'EXISTE PAS
                    if penalite_applicable > 0:
                        try:
                            # Vérifier si le chauffeur est en congé
                            try:
                                est_en_conge = CongesChauffeur.objects.filter(
                                    contrat=contrat,
                                    date_debut__lte=aujourd_hui,
                                    date_fin__gte=aujourd_hui,
                                    statut__in=['approuvé', 'planifié', 'en_cours']
                                ).exists()
                            except:
                                est_en_conge = False

                            if not est_en_conge:
                                # Créer la pénalité
                                Penalite.objects.create(
                                    contrat_chauffeur=contrat,
                                    contrat_reference=contrat.reference,
                                    type_penalite=type_contrat,
                                    montant=penalite_applicable,
                                    motif=motif_penalite,
                                    description=f"Pénalité automatique pour retard du {aujourd_hui.strftime('%d/%m/%Y')}",
                                    statut='en_attente',
                                    date_paiement_manque=aujourd_hui,
                                    cree_par=request.user if request.user.is_authenticated else None
                                )
                                penalites_auto_creees += 1

                                # Mettre à jour la liste des pénalités actives
                                penalites_actives = Penalite.objects.filter(statut='en_attente')
                                penalites = penalites_actives.filter(contrat_chauffeur=contrat)
                                montant_penalites = penalites.aggregate(total=Sum('montant'))['total'] or 0
                        except Exception as e:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"Erreur création pénalité chauffeur {contrat.id}: {e}")

                # Vérifier si le chauffeur est en congé
                try:
                    est_en_conge = CongesChauffeur.objects.filter(
                        contrat=contrat,
                        date_debut__lte=aujourd_hui,
                        date_fin__gte=aujourd_hui,
                        statut__in=['approuvé', 'planifié', 'en_cours']
                    ).exists()
                except:
                    est_en_conge = False

                paiements_attendus.append({
                    'contrat_id': contrat.id,
                    'contrat_type': 'chauffeur',
                    'contrat_batterie_id': contrat_batterie.id if contrat_batterie else None,
                    'reference': contrat.reference,
                    'client_nom': f"{contrat.association.validated_user.prenom} {contrat.association.validated_user.nom}",
                    'client_id': contrat.association.validated_user.id,
                    'client_telephone': contrat.association.validated_user.phone,
                    'montant': montant,
                    'montant_batterie': montant_batterie,
                    'montant_total': montant + montant_batterie,
                    'frequence': contrat.get_frequence_paiement_display(),
                    'penalites_count': penalites.count(),
                    'penalites_montant': montant_penalites,
                    'heure_limite': heure_limite,
                    'retard': heure_actuelle >= time(12, 1),
                    'retard_grave': heure_actuelle >= time(14, 1),
                    'penalite_applicable': penalite_applicable,
                    'motif_penalite': motif_penalite,
                    'type_penalite': 'combine' if contrat_batterie else 'batterie_seule',
                    'photo_client': contrat.association.validated_user.photo_url if hasattr(contrat.association.validated_user, 'photo_url') else None,
                    'est_en_conge': est_en_conge,
                })

    # Faire de même pour les contrats partenaire
    for contrat in contrats_partenaire:
        if _est_jour_de_paiement(contrat, aujourd_hui):
            montant = contrat.montant_par_paiement

            # Vérifier s'il y a un contrat batterie associé
            contrats_batterie = []
            try:
                # Vérifier si le partenaire a des contrats batterie actifs
                contrats_batterie = ContratBatterie.objects.filter(
                    partenaire=contrat.partenaire,
                    statut='actif'
                )
            except:
                contrats_batterie = []

            montant_batterie = Decimal('0.00')
            contrat_batterie_id = None
            for cb in contrats_batterie:
                if _est_jour_de_paiement(cb, aujourd_hui):
                    montant_batterie += cb.montant_par_paiement
                    # On garde le premier ID pour la référence
                    if not contrat_batterie_id:
                        contrat_batterie_id = cb.id

            # Vérifier si le paiement a déjà été effectué aujourd'hui
            deja_paye = paiements_aujourd_hui.filter(
                contrat_partenaire=contrat, est_penalite=False
            ).exists()

            if not deja_paye:
                # Vérifier s'il y a des pénalités en attente
                penalites = penalites_actives.filter(contrat_partenaire=contrat)
                montant_penalites = penalites.aggregate(total=Sum('montant'))['total'] or 0

                # Déterminer si c'est un retard et le niveau de pénalité applicable
                penalite_applicable = Decimal('0.00')
                motif_penalite = None


                # Vérifier s'il y a une pénalité pour aujourd'hui
                penalite_du_jour = penalites.filter(date_paiement_manque=aujourd_hui).first()

                if heure_actuelle >= time(12, 1) and not penalite_du_jour:
                    type_contrat = 'combine' if contrats_batterie.exists() else 'batterie_seule'
                    penalite_applicable, motif_penalite = ReglePenalite.get_penalite_applicable(
                        type_contrat, heure_actuelle
                    )

                    # CRÉER AUTOMATIQUEMENT LA PÉNALITÉ EN BASE SI ELLE N'EXISTE PAS
                    if penalite_applicable > 0:
                        try:
                            # Créer la pénalité
                            Penalite.objects.create(
                                contrat_partenaire=contrat,
                                contrat_reference=contrat.reference,
                                type_penalite=type_contrat,
                                montant=penalite_applicable,
                                motif=motif_penalite,
                                description=f"Pénalité automatique pour retard du {aujourd_hui.strftime('%d/%m/%Y')}",
                                statut='en_attente',
                                date_paiement_manque=aujourd_hui,
                                cree_par=request.user if request.user.is_authenticated else None
                            )
                            penalites_auto_creees += 1

                            # Mettre à jour la liste des pénalités actives
                            penalites_actives = Penalite.objects.filter(statut='en_attente')
                            penalites = penalites_actives.filter(contrat_partenaire=contrat)
                            montant_penalites = penalites.aggregate(total=Sum('montant'))['total'] or 0
                        except Exception as e:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"Erreur création pénalité partenaire {contrat.id}: {e}")

                paiements_attendus.append({
                    'contrat_id': contrat.id,
                    'contrat_type': 'partenaire',
                    'contrat_batterie_id': contrat_batterie_id,
                    'reference': contrat.reference,
                    'client_nom': f"{contrat.partenaire.prenom} {contrat.partenaire.nom}",
                    'client_id': contrat.partenaire.id,
                    'client_telephone': contrat.partenaire.phone,
                    'montant': montant,
                    'montant_batterie': montant_batterie,
                    'montant_total': montant + montant_batterie,
                    'frequence': contrat.get_frequence_paiement_display(),
                    'penalites_count': penalites.count(),
                    'penalites_montant': montant_penalites,
                    'heure_limite': heure_limite,
                    'retard': heure_actuelle >= time(12, 1),
                    'retard_grave': heure_actuelle >= time(14, 1),
                    'penalite_applicable': penalite_applicable,
                    'motif_penalite': motif_penalite,
                    'type_penalite': 'combine' if contrats_batterie.exists() else 'batterie_seule',
                    'photo_client': contrat.partenaire.photo_url if hasattr(contrat.partenaire, 'photo_url') else None,
                })

    # Pour les contrats batterie standalone (pas liés à un contrat moto)
    for contrat in contrats_batterie:
        # Vérifier si c'est un contrat batterie "standalone" (pas lié à un contrat chauffeur/partenaire)
        is_standalone = True

        if contrat.chauffeur :
            # Vérifier si le chauffeur a un contrat actif
            if ContratChauffeur.objects.filter(
                    association__validated_user=contrat.chauffeur,
                    statut='actif'
            ).exists():
                is_standalone = False

        if contrat.partenaire:
            # Vérifier si le partenaire a un contrat actif
            if ContratPartenaire.objects.filter(partenaire=contrat.partenaire, statut='actif').exists():
                is_standalone = False

        # Ne traiter que les contrats batterie standalone
        if is_standalone and _est_jour_de_paiement(contrat, aujourd_hui):
            montant = contrat.montant_par_paiement

            # Déterminer le client (chauffeur ou partenaire)
            client_nom = ""
            client_id = None
            client_telephone = ""
            photo_client = None

            if contrat.chauffeur:
                client_nom = f"{contrat.chauffeur.prenom} {contrat.chauffeur.nom}"
                client_id = contrat.chauffeur.id
                client_telephone = contrat.chauffeur.phone
                photo_client = contrat.chauffeur.photo_url if hasattr(contrat.chauffeur, 'photo_url') else None
            elif contrat.partenaire:
                client_nom = f"{contrat.partenaire.prenom} {contrat.partenaire.nom}"
                client_id = contrat.partenaire.id
                client_telephone = contrat.partenaire.phone
                photo_client = contrat.partenaire.photo_url if hasattr(contrat.partenaire, 'photo_url') else None

            # Vérifier si le paiement a déjà été effectué aujourd'hui
            deja_paye = paiements_aujourd_hui.filter(
                contrat_batterie=contrat, est_penalite=False
            ).exists()

            if not deja_paye:
                # Vérifier s'il y a des pénalités en attente
                penalites = penalites_actives.filter(contrat_batterie=contrat)
                montant_penalites = penalites.aggregate(total=Sum('montant'))['total'] or 0

                # Déterminer si c'est un retard et le niveau de pénalité applicable
                penalite_applicable = Decimal('0.00')
                motif_penalite = None


                # Vérifier s'il y a une pénalité pour aujourd'hui
                penalite_du_jour = penalites.filter(date_paiement_manque=aujourd_hui).first()

                if heure_actuelle >= time(12, 1) and not penalite_du_jour:
                    penalite_applicable, motif_penalite = ReglePenalite.get_penalite_applicable(
                        'batterie_seule', heure_actuelle
                    )

                    # CRÉER AUTOMATIQUEMENT LA PÉNALITÉ EN BASE SI ELLE N'EXISTE PAS
                    if penalite_applicable > 0:
                        try:
                            # Créer la pénalité
                            Penalite.objects.create(
                                contrat_batterie=contrat,
                                contrat_reference=contrat.reference,
                                type_penalite='batterie_seule',
                                montant=penalite_applicable,
                                motif=motif_penalite,
                                description=f"Pénalité automatique pour retard du {aujourd_hui.strftime('%d/%m/%Y')}",
                                statut='en_attente',
                                date_paiement_manque=aujourd_hui,
                                cree_par=request.user if request.user.is_authenticated else None
                            )
                            penalites_auto_creees += 1

                            # Mettre à jour la liste des pénalités actives
                            penalites_actives = Penalite.objects.filter(statut='en_attente')
                            penalites = penalites_actives.filter(contrat_batterie=contrat)
                            montant_penalites = penalites.aggregate(total=Sum('montant'))['total'] or 0
                        except Exception as e:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"Erreur création pénalité batterie {contrat.id}: {e}")

                paiements_attendus.append({
                    'contrat_id': contrat.id,
                    'contrat_type': 'batterie',
                    'contrat_batterie_id': contrat.id,
                    'reference': contrat.reference,
                    'client_nom': client_nom,
                    'client_id': client_id,
                    'client_telephone': client_telephone,
                    'montant': Decimal('0.00'),  # Pas de montant moto
                    'montant_batterie': montant,
                    'montant_total': montant,
                    'frequence': contrat.get_frequence_paiement_display(),
                    'penalites_count': penalites.count(),
                    'penalites_montant': montant_penalites,
                    'heure_limite': heure_limite,
                    'retard': heure_actuelle >= time(12, 1),
                    'retard_grave': heure_actuelle >= time(14, 1),
                    'penalite_applicable': penalite_applicable,
                    'motif_penalite': motif_penalite,
                    'type_penalite': 'batterie_seule',
                    'photo_client': photo_client,
                })

    # Afficher un message si des pénalités ont été créées automatiquement
    if penalites_auto_creees > 0:
        messages.success(
            request,
            f"{penalites_auto_creees} pénalité(s) ont été créées automatiquement et enregistrées en base de données."
        )

    # Trier les paiements attendus par priorité
    paiements_attendus.sort(key=lambda x: (
        not x['retard_grave'],  # Les retards graves en premier
        not x['retard'],  # Puis les retards normaux
        -x['penalites_count'],  # Puis par nombre de pénalités (décroissant)
        x['client_nom']  # Enfin par ordre alphabétique
    ))

    # Statistiques
    stats = {
        'nb_paiements_attendus': len(paiements_attendus),
        'montant_total_attendu': sum(p['montant_total'] for p in paiements_attendus),
        'nb_penalites_actives': penalites_actives.count(),
        'montant_total_penalites': penalites_actives.aggregate(total=Sum('montant'))['total'] or 0,
        'nb_paiements_effectues': paiements_aujourd_hui.count(),
        'montant_total_paye': paiements_aujourd_hui.aggregate(total=Sum('montant_total'))['total'] or 0,
        'taux_realisation': (
                    paiements_aujourd_hui.count() / len(paiements_attendus) * 100) if paiements_attendus else 0,
    }

    # Récupérer les paiements effectués aujourd'hui pour l'onglet "Déjà traités"
    paiements_effectues = []
    for paiement in paiements_aujourd_hui.order_by('-date_enregistrement'):
        client_info = paiement.get_client_info()

        paiements_effectues.append({
            'id': paiement.id,
            'reference': paiement.reference,
            'montant': paiement.montant_moto,
            'montant_batterie': paiement.montant_batterie,
            'heure': paiement.date_enregistrement.strftime('%H:%M'),
            'methode': paiement.get_methode_paiement_display(),
            'client_nom': client_info.get('nom', 'Inconnu'),
            'client_type': client_info.get('type', 'Inconnu'),
            'contrat_type': paiement.get_type_contrat_display(),
            'est_penalite': paiement.est_penalite,
            'inclut_penalites': paiement.inclut_penalites,
        })

    # Récupérer les paiements en retard (jours précédents non payés)
    paiements_retard = []
    date_hier = aujourd_hui - timedelta(days=1)



    # Fonction pour vérifier les paiements manqués
    def _verifier_paiements_manques(contrat, date_limite, type_contrat):
        jours_manques = []
        date_courante = date_limite

        # Remonter jusqu'à 30 jours en arrière maximum
        for _ in range(30):
            date_courante = date_courante - timedelta(days=1)

            # Arrêter si on atteint la date de début du contrat
            if date_courante < contrat.date_debut:
                break

            # Vérifier si c'était un jour de paiement
            if _est_jour_de_paiement(contrat, date_courante):
                # Vérifier si le paiement a été effectué
                if type_contrat == 'chauffeur':
                    paiement_existe = Paiement.objects.filter(
                        contrat_chauffeur=contrat,
                        date_paiement=date_courante,
                        est_penalite=False
                    ).exists()
                elif type_contrat == 'partenaire':
                    paiement_existe = Paiement.objects.filter(
                        contrat_partenaire=contrat,
                        date_paiement=date_courante,
                        est_penalite=False
                    ).exists()
                elif type_contrat == 'batterie':
                    paiement_existe = Paiement.objects.filter(
                        contrat_batterie=contrat,
                        date_paiement=date_courante,
                        est_penalite=False
                    ).exists()
                else:
                    paiement_existe = False

                if not paiement_existe:
                    jours_manques.append(date_courante)

                    # Créer automatiquement la pénalité pour les jours manqués si elle n'existe pas
                    try:
                        if type_contrat == 'chauffeur':
                            penalite_existe = Penalite.objects.filter(
                                contrat_chauffeur=contrat,
                                date_paiement_manque=date_courante
                            ).exists()

                            # if not penalite_existe:
                            #     # Déterminer le type de pénalité
                            #     chauffeur_vu = contrat.association.validated_user
                            #     type_penalite = 'combine' if ContratBatterie.objects.filter(
                            #         chauffeur=chauffeur_vu, statut='actif'
                            #     ).exists() else 'batterie_seule'
                            #
                            #     jours_retard = (aujourd_hui - date_courante).days
                            #     montant_penalite = Decimal('5000.00') if jours_retard > 3 else Decimal(
                            #         '2000.00') if type_penalite == 'combine' else Decimal('1000.00')
                            #
                            #     Penalite.objects.create(
                            #         contrat_chauffeur=contrat,
                            #         contrat_reference=contrat.reference,
                            #         type_penalite=type_penalite,
                            #         montant=montant_penalite,
                            #         motif='retard_paiement',
                            #         description=f"Pénalité pour paiement manqué du {date_courante.strftime('%d/%m/%Y')} - {jours_retard} jours de retard",
                            #         statut='en_attente',
                            #         date_paiement_manque=date_courante,
                            #         cree_par=request.user if request.user.is_authenticated else None
                            #     )

                        elif type_contrat == 'partenaire':
                            penalite_existe = Penalite.objects.filter(
                                contrat_partenaire=contrat,
                                date_paiement_manque=date_courante
                            ).exists()

                            # if not penalite_existe:
                            #     # Déterminer le type de pénalité
                            #     type_penalite = 'combine' if ContratBatterie.objects.filter(
                            #         partenaire=contrat.partenaire, statut='actif').exists() else 'batterie_seule'
                            #     jours_retard = (aujourd_hui - date_courante).days
                            #     montant_penalite = Decimal('5000.00') if jours_retard > 3 else Decimal(
                            #         '2000.00') if type_penalite == 'combine' else Decimal('1000.00')
                            #
                            #     Penalite.objects.create(
                            #         contrat_partenaire=contrat,
                            #         contrat_reference=contrat.reference,
                            #         type_penalite=type_penalite,
                            #         montant=montant_penalite,
                            #         motif='retard_paiement',
                            #         description=f"Pénalité pour paiement manqué du {date_courante.strftime('%d/%m/%Y')} - {jours_retard} jours de retard",
                            #         statut='en_attente',
                            #         date_paiement_manque=date_courante,
                            #         cree_par=request.user if request.user.is_authenticated else None
                            #     )

                        elif type_contrat == 'batterie':
                            penalite_existe = Penalite.objects.filter(
                                contrat_batterie=contrat,
                                date_paiement_manque=date_courante
                            ).exists()

                            # if not penalite_existe:
                            #     jours_retard = (aujourd_hui - date_courante).days
                            #     montant_penalite = Decimal('1000.00') if jours_retard > 3 else Decimal('500.00')
                            #
                            #     Penalite.objects.create(
                            #         contrat_batterie=contrat,
                            #         contrat_reference=contrat.reference,
                            #         type_penalite='batterie_seule',
                            #         montant=montant_penalite,
                            #         motif='retard_paiement',
                            #         description=f"Pénalité pour paiement manqué du {date_courante.strftime('%d/%m/%Y')} - {jours_retard} jours de retard",
                            #         statut='en_attente',
                            #         date_paiement_manque=date_courante,
                            #         cree_par=request.user if request.user.is_authenticated else None
                            #     )
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Erreur création pénalité rétroactive: {e}")

                    # Limiter à 5 jours manqués maximum pour l'affichage
                    if len(jours_manques) >= 5:
                        break

        return jours_manques

    # Vérifier les contrats chauffeur
    for contrat in contrats_chauffeur:
        jours_manques = _verifier_paiements_manques(contrat, aujourd_hui, 'chauffeur')

        if jours_manques:
            # Vérifier s'il y a un contrat batterie associé
            contrat_batterie = None
            try:
                contrat_batterie = ContratBatterie.objects.filter(
                    chauffeur=contrat.chauffeur,
                    statut='actif'
                ).first()
            except:
                contrat_batterie = None

            for jour_manque in jours_manques:
                paiements_retard.append({
                    'contrat_id': contrat.id,
                    'contrat_type': 'chauffeur',
                    'contrat_batterie_id': contrat_batterie.id if contrat_batterie else None,
                    'reference': contrat.reference,
                    'client_nom': f"{contrat.association.validated_user.prenom} {contrat.association.validated_user.nom}",
                    'client_id': contrat.association.validated_user.id,
                    'montant': contrat.montant_par_paiement,
                    'montant_batterie': contrat_batterie.montant_par_paiement if contrat_batterie and _est_jour_de_paiement(
                        contrat_batterie, jour_manque) else Decimal('0.00'),
                    'date_manquee': jour_manque,
                    'jours_retard': (aujourd_hui - jour_manque).days,
                    'type_penalite': 'combine' if contrat_batterie else 'batterie_seule',
                })

    # Faire de même pour les contrats partenaire
    for contrat in contrats_partenaire:
        jours_manques = _verifier_paiements_manques(contrat, aujourd_hui, 'partenaire')

        if jours_manques:
            # Vérifier s'il y a un contrat batterie associé
            contrats_batterie_partenaire = []
            try:
                contrats_batterie_partenaire = ContratBatterie.objects.filter(
                    partenaire=contrat.partenaire,
                    statut='actif'
                )
            except:
                contrats_batterie_partenaire = []

            for jour_manque in jours_manques:
                montant_batterie_jour = Decimal('0.00')
                contrat_batterie_id = None

                for cb in contrats_batterie_partenaire:
                    if _est_jour_de_paiement(cb, jour_manque):
                        montant_batterie_jour += cb.montant_par_paiement
                        if not contrat_batterie_id:
                            contrat_batterie_id = cb.id

                paiements_retard.append({
                    'contrat_id': contrat.id,
                    'contrat_type': 'partenaire',
                    'contrat_batterie_id': contrat_batterie_id,
                    'reference': contrat.reference,
                    'client_nom': f"{contrat.partenaire.prenom} {contrat.partenaire.nom}",
                    'client_id': contrat.partenaire.id,
                    'montant': contrat.montant_par_paiement,
                    'montant_batterie': montant_batterie_jour,
                    'date_manquee': jour_manque,
                    'jours_retard': (aujourd_hui - jour_manque).days,
                    'type_penalite': 'combine' if contrats_batterie_partenaire.exists() else 'batterie_seule',
                })

    # Faire de même pour les contrats batterie standalone
    for contrat in contrats_batterie:
        # Vérifier si c'est un contrat batterie "standalone"
        is_standalone = True

        if contrat.chauffeur:
            if ContratChauffeur.objects.filter(
                    association__validated_user=contrat.chauffeur,
                    statut='actif'
            ).exists():
                is_standalone = False

        if contrat.partenaire:
            if ContratPartenaire.objects.filter(partenaire=contrat.partenaire, statut='actif').exists():
                is_standalone = False

        if is_standalone:
            jours_manques = _verifier_paiements_manques(contrat, aujourd_hui, 'batterie')

            if jours_manques:
                # Déterminer le client (chauffeur ou partenaire)
                client_nom = ""
                client_id = None

                if contrat.chauffeur:
                    client_nom = f"{contrat.chauffeur.prenom} {contrat.chauffeur.nom}"
                    client_id = contrat.chauffeur.id
                elif contrat.partenaire:
                    client_nom = f"{contrat.partenaire.prenom} {contrat.partenaire.nom}"
                    client_id = contrat.partenaire.id

                for jour_manque in jours_manques:
                    paiements_retard.append({
                        'contrat_id': contrat.id,
                        'contrat_type': 'batterie',
                        'contrat_batterie_id': contrat.id,
                        'reference': contrat.reference,
                        'client_nom': client_nom,
                        'client_id': client_id,
                        'montant': Decimal('0.00'),  # Pas de montant moto
                        'montant_batterie': contrat.montant_par_paiement,
                        'date_manquee': jour_manque,
                        'jours_retard': (aujourd_hui - jour_manque).days,
                        'type_penalite': 'batterie_seule',
                    })

    # Trier les paiements en retard par date (plus ancien en premier)
    paiements_retard.sort(key=lambda x: x['jours_retard'], reverse=True)

    all_paiements = []
    for p in paiements_attendus:
        p['display_status'] = 'a_traiter'
        all_paiements.append(p)
    for p in paiements_effectues:
        p['display_status'] = 'deja_traites'
        all_paiements.append(p)
    for p in paiements_retard:
        p['display_status'] = 'retards'
        all_paiements.append(p)



    from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

    page = request.GET.get('page', 1)
    paginator = Paginator(all_paiements, 20)  # 20 paiements par page

    try:
        paiements_page = paginator.page(page)
    except PageNotAnInteger:
        paiements_page = paginator.page(1)
    except EmptyPage:
        paiements_page = paginator.page(paginator.num_pages)

    context = {
        'titre': 'Centre de Paiements',
        'paiements': paiements_page,
        'stats': stats,
        'aujourd_hui': aujourd_hui,        # déjà présent chez vous
        'heure_actuelle': heure_actuelle,  # déjà présent chez vous
        'onglet_actif': request.GET.get('onglet', 'a_traiter'),
        'vue_calendrier': request.GET.get('vue', 'liste') == 'calendrier',
        'is_today': is_today,              # + utile pour l’affichage si besoin
    }
    return render(request, 'payments/centre.html', context)



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

    # Vérifier si le chauffeur est en congé à cette date
    est_en_conge = False
    if hasattr(contrat, 'chauffeur'):
        est_en_conge = CongesChauffeur.objects.filter(
            contrat=contrat,
            date_debut__lte=date_ref,
            date_fin__gte=date_ref,
            statut__in=['approuvé', 'planifié', 'en_cours']
        ).exists()

        # Si en congé, pas de paiement attendu
    if est_en_conge:
        return False

    # Vérifier si la personne est en congé à cette date
    if hasattr(contrat, 'conges') and contrat.conges.filter(
            date_debut__lte=date_ref,
            date_fin__gte=date_ref,
            statut__in=['planifie', 'en_cours']
    ).exists():
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


def paiement_rapide(request, contrat_type, contrat_id):
    contrat = None
    contrat_batterie = None
    contrat_batterie_id = request.GET.get('contrat_batterie_id')
    aujourd_hui = date.today()
    est_en_conge = False

    if contrat_type == 'chauffeur':
        contrat = get_object_or_404(ContratChauffeur, id=contrat_id)
        client = contrat.association.validated_user
        contrat_batterie = get_object_or_404(ContratBatterie,
                                             id=contrat_batterie_id) if contrat_batterie_id else ContratBatterie.objects.filter(
            chauffeur=client, statut='actif').first()

        # Vérifier si le chauffeur est en congé
        est_en_conge = CongesChauffeur.objects.filter(
            contrat=contrat,
            date_debut__lte=aujourd_hui,
            date_fin__gte=aujourd_hui,
            statut__in=['approuvé', 'planifié', 'en_cours']
        ).exists()

    elif contrat_type == 'partenaire':
        contrat = get_object_or_404(ContratPartenaire, id=contrat_id)
        client = contrat.partenaire
        contrat_batterie = get_object_or_404(ContratBatterie,
                                             id=contrat_batterie_id) if contrat_batterie_id else ContratBatterie.objects.filter(
            partenaire=client, statut='actif').first()

    elif contrat_type == 'batterie':
        contrat_batterie = get_object_or_404(ContratBatterie, id=contrat_id)
        contrat = contrat_batterie
        client = contrat_batterie.chauffeur if contrat_batterie.chauffeur else contrat_batterie.partenaire

        # Vérifier si le chauffeur est en congé
        if contrat_batterie.chauffeur:
            est_en_conge = CongesChauffeur.objects.filter(
                contrat__chauffeur=contrat_batterie.chauffeur,
                date_debut__lte=aujourd_hui,
                date_fin__gte=aujourd_hui,
                statut__in=['approuvé', 'planifié', 'en_cours']
            ).exists()

    else:
        messages.error(request, "Type de contrat invalide.")
        return redirect('payments:centre_paiements')

    # Récupérer les pénalités existantes (non payées)
    penalites_existantes = Penalite.objects.filter(
        **{f'contrat_{contrat_type}': contrat},
        statut='en_attente'
    )

    # Rechercher la pénalité du jour s'il y en a une
    penalite_du_jour = penalites_existantes.filter(
        date_paiement_manque=aujourd_hui
    ).first()

    montant_attendu = contrat.montant_engage if contrat_type != 'batterie' else Decimal('0.00')
    montant_batterie_attendu = contrat_batterie.montant_engage_batterie if contrat_batterie else Decimal('0.00')

    initial_data = {
        'montant': montant_attendu,
        'montant_batterie': montant_batterie_attendu,
    }

    if request.method == 'POST':
        form = PaiementRapideForm(request.POST, penalite_jour=penalite_du_jour)
        if form.is_valid():
            data = form.cleaned_data
            now = timezone.now()
            user = request.user if request.user.is_authenticated else None

            # Enregistrer le paiement principal
            paiement_principal = Paiement(
                montant_moto=data['montant'],
                montant_batterie=data.get('montant_batterie', 0) or 0,  # <-- AJOUT ICI
                montant_total=data['montant'] + data.get('montant_batterie', 0),
                date_paiement=aujourd_hui,
                heure_paiement=now.time(),
                methode_paiement=data['methode_paiement'],
                reference_transaction=data['reference_transaction'],
                notes=data['notes'],
                est_penalite=False,
                type_contrat=contrat_type,
                contrat_batterie=contrat_batterie,
                enregistre_par=user,
                reference=f"PMT-{uuid.uuid4().hex[:8].upper()}"
            )

            # Associer au bon contrat
            setattr(paiement_principal, f'contrat_{contrat_type}', contrat)
            paiement_principal.save()



            if penalite_du_jour and data['pardonner_penalite_jour']:
                # Pardonner la pénalité
                penalite_du_jour.statut = 'annulee'
                penalite_du_jour.raison_annulation = data['justification_pardon']
                penalite_du_jour.pardonnee_par = user
                penalite_du_jour.date_pardon = now
                penalite_du_jour.save()

                messages.success(request, f"Pénalité du jour pardonnée avec succès.")

            messages.success(request, f"Paiement enregistré avec succès pour {client.prenom} {client.nom}.")
            return redirect('payments:centre_paiements')
    else:
        form = PaiementRapideForm(initial=initial_data, penalite_jour=penalite_du_jour)

    # Historique des paiements
    historique_paiements = Paiement.objects.filter(
        Q(**{f'contrat_{contrat_type}': contrat}) |
        Q(contrat_batterie=contrat_batterie) if contrat_batterie else Q(**{f'contrat_{contrat_type}': contrat})
    ).order_by('-date_paiement')[:10]

    context = {
        'titre': f'Paiement rapide - {client.prenom} {client.nom}',
        'form': form,
        'contrat': contrat,
        'contrat_batterie': contrat_batterie,
        'client': client,
        'contrat_type': contrat_type,
        'contrat_id': contrat_id,
        'penalites_existantes': penalites_existantes,
        'penalite_du_jour': penalite_du_jour,
        'historique_paiements': historique_paiements,
        'est_en_conge': est_en_conge,
    }

    return render(request, 'payments/paiement_rapide.html', context)


def liste_paiements(request):

    """Liste des paiements avec filtres améliorés"""
    # Récupérer les filtres
    date_debut = request.GET.get('date_debut', '')
    date_fin = request.GET.get('date_fin', '')
    type_contrat = request.GET.get('type_contrat', '')
    methode = request.GET.get('methode', '')
    est_penalite = request.GET.get('penalites') == '1'
    q = request.GET.get('q', '')
    trier_par = request.GET.get('trier_par', '-date_enregistrement')

    # Filtrer les paiements
    paiements = Paiement.objects.all()

    if date_debut:
        try:
            date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date()
            paiements = paiements.filter(date_paiement__gte=date_debut_obj)
        except ValueError:
            pass

    if date_fin:
        try:
            date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
            paiements = paiements.filter(date_paiement__lte=date_fin_obj)
        except ValueError:
            pass

    if type_contrat:
        paiements = paiements.filter(type_contrat=type_contrat)

    if methode:
        paiements = paiements.filter(methode_paiement=methode)

    if est_penalite:
        paiements = paiements.filter(est_penalite=True)

    if q:
        # Recherche par référence, client, ou contrat
        paiements = paiements.filter(
            Q(reference__icontains=q) |
            Q(contrat_chauffeur__association__validated_user__nom__icontains=q) |
            Q(contrat_chauffeur__association__validated_user__prenom__icontains=q) |
            Q(contrat_chauffeur__association__validated_user__phone__icontains=q) |

            Q(contrat_partenaire__partenaire__nom__icontains=q) |
            Q(contrat_partenaire__partenaire__prenom__icontains=q) |
            Q(contrat_batterie__reference__icontains=q) |
            Q(contrat_chauffeur__reference__icontains=q) |
            Q(contrat_partenaire__reference__icontains=q)
        )

    # Tri
    if trier_par:
        # Cas spéciaux pour le tri par client
        if trier_par == 'client':
            # Créer un tri complexe par nom de client
            paiements = paiements.annotate(
                client_nom=Case(
                    When(contrat_chauffeur__isnull=False, then=Concat('contrat_chauffeur__chauffeur__nom', Value(' '),
                                                                      'contrat_chauffeur__chauffeur__prenom')),
                    When(contrat_partenaire__isnull=False,
                         then=Concat('contrat_partenaire__partenaire__nom', Value(' '),
                                     'contrat_partenaire__partenaire__prenom')),
                    When(contrat_batterie__chauffeur__isnull=False,
                         then=Concat('contrat_batterie__chauffeur__nom', Value(' '),
                                     'contrat_batterie__chauffeur__prenom')),
                    When(contrat_batterie__partenaire__isnull=False,
                         then=Concat('contrat_batterie__partenaire__nom', Value(' '),
                                     'contrat_batterie__partenaire__prenom')),
                    default=Value(''),
                    output_field=CharField()
                )
            ).order_by('client_nom')
        elif trier_par == '-client':
            paiements = paiements.annotate(
                client_nom=Case(
                    When(contrat_chauffeur__isnull=False, then=Concat('contrat_chauffeur__chauffeur__nom', Value(' '),
                                                                      'contrat_chauffeur__chauffeur__prenom')),
                    When(contrat_partenaire__isnull=False,
                         then=Concat('contrat_partenaire__partenaire__nom', Value(' '),
                                     'contrat_partenaire__partenaire__prenom')),
                    When(contrat_batterie__chauffeur__isnull=False,
                         then=Concat('contrat_batterie__chauffeur__nom', Value(' '),
                                     'contrat_batterie__chauffeur__prenom')),
                    When(contrat_batterie__partenaire__isnull=False,
                         then=Concat('contrat_batterie__partenaire__nom', Value(' '),
                                     'contrat_batterie__partenaire__prenom')),
                    default=Value(''),
                    output_field=CharField()
                )
            ).order_by('-client_nom')
        else:
            paiements = paiements.order_by(trier_par)

    # Données pour les statistiques
    total_montant = paiements.aggregate(total=Sum('montant_total'))['total'] or 0

    # Vérifier si export CSV est demandé
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="paiements.csv"'

        writer = csv.writer(response)
        # Écrire l'en-tête du CSV
        writer.writerow(['Date', 'Référence', 'Client', 'Contrat', 'Montant', 'Méthode', 'Type', 'Enregistré par'])

        # Écrire toutes les lignes (sans pagination)
        for paiement in paiements:
            client_nom = "-"
            contrat_ref = "-"

            if paiement.contrat_chauffeur:
                client_nom = f"{paiement.contrat_chauffeur.association.validated_user.prenom} {paiement.contrat_chauffeur.association.validated_user.nom}"
                contrat_ref = paiement.contrat_chauffeur.reference
            elif paiement.contrat_partenaire:
                client_nom = f"{paiement.contrat_partenaire.partenaire.prenom} {paiement.contrat_partenaire.partenaire.nom}"
                contrat_ref = paiement.contrat_partenaire.reference
            elif paiement.contrat_batterie and paiement.contrat_batterie.chauffeur:
                client_nom = f"{paiement.contrat_batterie.chauffeur.prenom} {paiement.contrat_batterie.chauffeur.nom}"
                contrat_ref = paiement.contrat_batterie.reference
            elif paiement.contrat_batterie and paiement.contrat_batterie.partenaire:
                client_nom = f"{paiement.contrat_batterie.partenaire.prenom} {paiement.contrat_batterie.partenaire.nom}"
                contrat_ref = paiement.contrat_batterie.reference

            type_display = "Pénalité" if paiement.est_penalite else paiement.get_type_contrat_display()
            enregistre_par = f"{paiement.enregistre_par.prenom} {paiement.enregistre_par.nom}" if paiement.enregistre_par else "-"

            writer.writerow([
                paiement.date_paiement.strftime('%d/%m/%Y'),
                paiement.reference,
                client_nom,
                contrat_ref,
                f"{paiement.montant_total:,.0f}",  # ← CORRECTION ICI
                paiement.get_methode_paiement_display(),
                type_display,
                enregistre_par
            ])

        return response

    # Pagination (seulement si on n'exporte pas)
    paginator = Paginator(paiements, 20)  # 20 paiements par page
    page_number = request.GET.get('page')
    paiements_page = paginator.get_page(page_number)

    context = {
        'filtres': {
            'date_debut': date_debut,
            'date_fin': date_fin,
            'type_contrat': type_contrat,
            'methode': methode,
            'penalites': est_penalite,
            'q': q,
            'trier_par': trier_par,
        },
        'paiements': paiements_page,
        'total_montant': total_montant,
        'methode_choices': Paiement.METHODE_CHOICES,
    }

    return render(request, 'payments/historique.html', context)


def gestion_penalites(request):
    """Centre de gestion des pénalités avec filtres avancés"""
    # Récupération des filtres depuis les paramètres GET
    statut = request.GET.get('statut', '')
    type_penalite = request.GET.get('type_penalite', '')
    motif = request.GET.get('motif', '')
    date_debut = request.GET.get('date_debut', '')
    date_fin = request.GET.get('date_fin', '')
    q = request.GET.get('q', '')

    # Base de requête
    penalites = Penalite.objects.all()

    # Application des filtres
    if statut:
        penalites = penalites.filter(statut=statut)

    if type_penalite:
        penalites = penalites.filter(type_penalite=type_penalite)

    if motif:
        penalites = penalites.filter(motif=motif)

    if date_debut:
        try:
            date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date()
            penalites = penalites.filter(date_creation__date__gte=date_debut_obj)
        except ValueError:
            pass

    if date_fin:
        try:
            date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
            penalites = penalites.filter(date_creation__date__lte=date_fin_obj)
        except ValueError:
            pass

    if q:
        # Recherche par client, description, ou référence de contrat
        penalites = penalites.filter(
            Q(contrat_chauffeur__chauffeur__nom__icontains=q) |
            Q(contrat_chauffeur__chauffeur__prenom__icontains=q) |
            Q(contrat_chauffeur__chauffeur__phone__icontains=q) |
            Q(contrat_partenaire__partenaire__nom__icontains=q) |
            Q(contrat_partenaire__partenaire__prenom__icontains=q) |
            Q(contrat_partenaire__partenaire__phone__icontains=q) |
            Q(contrat_batterie__chauffeur__nom__icontains=q) |
            Q(contrat_batterie__chauffeur__prenom__icontains=q) |
            Q(contrat_batterie__partenaire__nom__icontains=q) |
            Q(contrat_batterie__partenaire__prenom__icontains=q) |
            Q(contrat_reference__icontains=q) |
            Q(description__icontains=q)
        )

    # Tri par date de création (plus récentes en premier)
    penalites = penalites.order_by('-date_creation')

    # Pagination
    paginator = Paginator(penalites, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Statistiques
    total_penalites = penalites.count()
    montant_total = penalites.aggregate(total=Sum('montant'))['total'] or 0

    # Préparer les choix pour les filtres
    statut_choices = Penalite.STATUT_CHOICES
    motif_choices = Penalite.MOTIF_CHOICES
    type_penalite_choices = Penalite.TYPE_CONTRAT_CHOICES

    # Créer le dictionnaire des filtres pour le template
    filtres = {
        'statut': statut,
        'type_penalite': type_penalite,
        'motif': motif,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'q': q,
    }

    context = {
        'titre': 'Centre de Gestion des Pénalités',
        'penalites': page_obj,
        'total_penalites': total_penalites,
        'montant_total': montant_total,
        'filtres': filtres,  # ✅ Utiliser 'filtres' au lieu de variables séparées
        'statut_choices': statut_choices,
        'motif_choices': motif_choices,
        'type_penalite_choices': type_penalite_choices,
    }

    return render(request, 'payments/penalites/centre.html', context)


def creer_penalite(request, contrat_type, contrat_id):
    """Créer une nouvelle pénalité avec interface améliorée"""
    # Récupérer le contrat
    contrat = None
    client = None
    type_penalite = 'batterie_seule'

    if contrat_type == 'chauffeur':
        contrat = get_object_or_404(ContratChauffeur, id=contrat_id)
        client = contrat.chauffeur

        # Vérifier si le chauffeur a un contrat batterie actif
        if ContratBatterie.objects.filter(chauffeur=client, statut='actif').exists():
            type_penalite = 'combine'

    elif contrat_type == 'partenaire':
        contrat = get_object_or_404(ContratPartenaire, id=contrat_id)
        client = contrat.partenaire

        # Vérifier si le partenaire a un contrat batterie actif
        if ContratBatterie.objects.filter(partenaire=client, statut='actif').exists():
            type_penalite = 'combine'

    elif contrat_type == 'batterie':
        contrat = get_object_or_404(ContratBatterie, id=contrat_id)
        if contrat.chauffeur:
            client = contrat.chauffeur
        else:
            client = contrat.partenaire
        type_penalite = 'batterie_seule'

    else:
        messages.error(request, "Type de contrat invalide pour une pénalité.")
        return redirect('payments:centre_paiements')

    if request.method == 'POST':
        form = PenaliteForm(request.POST)

        if form.is_valid():
            penalite = form.save(commit=False)

            # Associer au contrat approprié
            if contrat_type == 'chauffeur':
                penalite.contrat_chauffeur = contrat
                penalite.contrat_reference = contrat.reference
            elif contrat_type == 'partenaire':
                penalite.contrat_partenaire = contrat
                penalite.contrat_reference = contrat.reference
            elif contrat_type == 'batterie':
                penalite.contrat_batterie = contrat
                penalite.contrat_reference = contrat.reference

            penalite.cree_par = request.user
            penalite.date_paiement_manque = date.today()
            penalite.save()

            messages.success(request, f"Pénalité créée avec succès pour {client.prenom} {client.nom}.")

            # Créer une notification si demandé
            if 'envoyer_notification' in request.POST:
                notification = NotificationPaiement()
                notification.type_notification = 'penalite'
                notification.message = f"Une pénalité de {penalite.montant} FCFA a été appliquée à votre compte. Motif: {penalite.get_motif_display()}"
                notification.date_programmee = timezone.now()
                notification.canal_notification = 'sms'

                # Associer au bon client et contrat
                if isinstance(client, Chauffeur):
                    notification.chauffeur = client
                    if contrat_type == 'chauffeur':
                        notification.contrat_chauffeur = contrat
                    elif contrat_type == 'batterie':
                        notification.contrat_batterie = contrat
                else:
                    notification.partenaire = client
                    if contrat_type == 'partenaire':
                        notification.contrat_partenaire = contrat
                    elif contrat_type == 'batterie':
                        notification.contrat_batterie = contrat

                notification.save()

                messages.info(request, "Une notification a été envoyée au client.")

            # Si la création vient de la page de détails du contrat, y retourner
            if 'from_detail' in request.GET:
                if contrat_type == 'chauffeur':
                    return redirect('contrats:details_contrat_chauffeur', contrat_id=contrat_id)
                elif contrat_type == 'partenaire':
                    return redirect('contrats:details_contrat_partenaire', contrat_id=contrat_id)
                elif contrat_type == 'batterie':
                    return redirect('contrats:details_contrat_batterie', contrat_id=contrat_id)

            return redirect('payments:gestion_penalites')
    else:
        # Récupérer le montant recommandé selon le type de pénalité
        montant_recommande = Decimal('2000.00')
        if type_penalite == 'combine':
            montant_recommande = Decimal('5000.00')

        form = PenaliteForm(initial={
            'type_penalite': type_penalite,
            'montant': montant_recommande
        })

    # Récupérer l'historique des pénalités pour ce client
    historique_penalites = []

    if contrat_type == 'chauffeur':
        historique_penalites = Penalite.objects.filter(
            contrat_chauffeur__chauffeur=client
        ).order_by('-date_creation')[:5]
    elif contrat_type == 'partenaire':
        historique_penalites = Penalite.objects.filter(
            contrat_partenaire__partenaire=client
        ).order_by('-date_creation')[:5]
    elif contrat_type == 'batterie':
        if contrat.chauffeur:
            historique_penalites = Penalite.objects.filter(
                Q(contrat_batterie__chauffeur=client) |
                Q(contrat_chauffeur__chauffeur=client)
            ).order_by('-date_creation')[:5]
        else:
            historique_penalites = Penalite.objects.filter(
                Q(contrat_batterie__partenaire=client) |
                Q(contrat_partenaire__partenaire=client)
            ).order_by('-date_creation')[:5]

    context = {
        'titre': f'Nouvelle pénalité - {client.prenom} {client.nom}',
        'form': form,
        'contrat': contrat,
        'client': client,
        'contrat_type': contrat_type,
        'type_penalite': type_penalite,
        'historique_penalites': historique_penalites,
    }

    return render(request, 'payments/penalites/nouveau.html', context)


def gerer_penalite(request, penalite_id):
    """Gérer une pénalité existante (payer, annuler, reporter, pardonner) avec interface améliorée"""
    penalite = get_object_or_404(Penalite, id=penalite_id)
    client = penalite.get_client()

    contrat = None
    contrat_type = None

    if penalite.contrat_chauffeur:
        contrat = penalite.contrat_chauffeur
        contrat_type = 'chauffeur'
    elif penalite.contrat_partenaire:
        contrat = penalite.contrat_partenaire
        contrat_type = 'partenaire'
    elif penalite.contrat_batterie:
        contrat = penalite.contrat_batterie
        contrat_type = 'batterie'

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'pardonner':
            raison_pardon = request.POST.get('raison_pardon')
            if not raison_pardon:
                messages.error(request, "Une raison est obligatoire pour pardonner une pénalité.")
                form = GestionPenaliteForm(initial={'montant_paiement': penalite.montant}, penalite=penalite)
            else:
                penalite.statut = 'annulee'
                penalite.raison_annulation = raison_pardon
                penalite.modifie_par = request.user if request.user.is_authenticated else None
                penalite.date_modification = timezone.now()
                if hasattr(penalite, 'pardonnee_par'):
                    penalite.pardonnee_par = request.user
                if hasattr(penalite, 'date_pardon'):
                    penalite.date_pardon = timezone.now()
                penalite.save()

                client_nom = f"{client.prenom} {client.nom}" if client else "Client inconnu"
                messages.success(request, f'Pénalité pardonnée pour {client_nom}')
                return redirect('payments:gestion_penalites')

        else:
            form = GestionPenaliteForm(request.POST, penalite=penalite)
            if form.is_valid():
                action = form.cleaned_data['action']
                raison = form.cleaned_data['raison']
                envoyer_notification = 'envoyer_notification' in request.POST

                if action == 'payer':
                    montant = form.cleaned_data['montant_paiement'] or penalite.montant
                    methode = form.cleaned_data['methode_paiement']

                    # Récupérer l'agence liée à l'utilisateur connecté
                    user_agence = getattr(request.user, 'user_agence', None)

                    PaiementPenalite.objects.create(
                        reference=f"PEN-{uuid.uuid4().hex[:8].upper()}",
                        penalite=penalite,
                        montant=montant,
                        date_paiement=date.today(),
                        methode_paiement=methode,
                        reference_transaction='',
                        enregistre_par=request.user,
                        user_agence=user_agence,
                    )

                    # 🔁 Recalculer le total payé
                    total_paye = penalite.paiements.aggregate(total=Sum('montant'))['total'] or 0
                    if total_paye >= penalite.montant:
                        penalite.statut = 'payee'

                    penalite.date_modification = timezone.now()
                    penalite.modifie_par = request.user
                    penalite.save()

                    messages.success(request, f"{montant} FCFA payés pour la pénalité de {client.prenom} {client.nom}.")

                    if envoyer_notification and client:
                        notification = NotificationPaiement()
                        notification.type_notification = 'penalite'
                        notification.message = f"Votre pénalité de {montant} FCFA a été réglée. Merci."
                        notification.date_programmee = timezone.now()
                        notification.canal_notification = 'sms'
                        if isinstance(client, ValidatedUser):
                            notification.chauffeur = client
                        else:
                            notification.partenaire = client
                        notification.penalite = penalite
                        notification.save()

                elif action == 'annuler':
                    penalite.statut = 'annulee'
                    penalite.date_modification = timezone.now()
                    penalite.modifie_par = request.user
                    penalite.raison_annulation = raison
                    penalite.save()

                    messages.success(request, f"Pénalité annulée pour {client.prenom} {client.nom}.")

                    if envoyer_notification and client:
                        notification = NotificationPaiement()
                        notification.type_notification = 'penalite'
                        notification.message = f"Votre pénalité de {penalite.montant} FCFA a été annulée. Raison: {raison}"
                        notification.date_programmee = timezone.now()
                        notification.canal_notification = 'sms'
                        if isinstance(client, ValidatedUser):
                            notification.chauffeur = client
                        else:
                            notification.partenaire = client
                        notification.penalite = penalite
                        notification.save()

                elif action == 'reporter':
                    date_report = form.cleaned_data['date_report']
                    if date_report:
                        penalite.statut = 'reportee'
                        penalite.date_modification = timezone.now()
                        penalite.modifie_par = request.user
                        penalite.raison_annulation = f"Reportée au {date_report.strftime('%d/%m/%Y')}. Raison: {raison}"
                        penalite.save()

                        messages.success(request,
                                         f"Pénalité reportée au {date_report.strftime('%d/%m/%Y')} pour {client.prenom} {client.nom}.")

                        if envoyer_notification and client:
                            notification = NotificationPaiement()
                            notification.type_notification = 'penalite'
                            notification.message = f"Votre pénalité de {penalite.montant} FCFA a été reportée au {date_report.strftime('%d/%m/%Y')}."
                            notification.date_programmee = timezone.now()
                            notification.canal_notification = 'sms'
                            if isinstance(client, ValidatedUser):
                                notification.chauffeur = client
                            else:
                                notification.partenaire = client
                            notification.penalite = penalite
                            notification.save()
                    else:
                        messages.error(request, "Une date de report est requise.")
                        return redirect('payments:gerer_penalite', penalite_id=penalite_id)

                return redirect('payments:gestion_penalites')

    else:
        form = GestionPenaliteForm(initial={'montant_paiement': penalite.montant}, penalite=penalite)

    # Historique des pénalités pour ce client
    historique_penalites = []
    if client:
        if isinstance(client, ValidatedUser):
            historique_penalites = Penalite.objects.filter(
                Q(contrat_chauffeur__association__validated_user=client) |
                Q(contrat_batterie__chauffeur=client)
            ).exclude(id=penalite.id).order_by('-date_creation')[:5]
        else:
            historique_penalites = Penalite.objects.filter(
                Q(contrat_partenaire__partenaire=client) |
                Q(contrat_batterie__partenaire=client)
            ).exclude(id=penalite.id).order_by('-date_creation')[:5]

    restant_a_payer = penalite.montant - penalite.montant_total_paye()

    context = {
        'titre': f'Gérer la pénalité - {client.prenom if client else ""} {client.nom if client else ""}',
        'form': form,
        'penalite': penalite,
        'client': client,
        'contrat': contrat,
        'contrat_type': contrat_type,
        'historique_penalites': historique_penalites,
        'restant_a_payer': restant_a_payer,
    }

    return render(request, 'payments/penalites/details.html', context)


# À ajouter dans payments/views.py

from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from .utils import creer_penalites_manquees_automatiquement


@require_POST
def corriger_penalites_manquees(request):
    """
    Vue pour corriger toutes les pénalités manquées des 30 derniers jours
    Crée en base de données toutes les pénalités qui auraient dû être appliquées
    """
    try:
        # Créer toutes les pénalités manquées des 30 derniers jours
        penalites_creees = creer_penalites_manquees_automatiquement(jours_max=30)

        if penalites_creees > 0:
            messages.success(
                request,
                f"✅ Correction terminée ! {penalites_creees} pénalité(s) manquées ont été créées et enregistrées en base de données."
            )
        else:
            messages.info(
                request,
                "ℹ️ Aucune pénalité manquée détectée. Toutes les pénalités sont déjà enregistrées en base."
            )

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur lors de la correction des pénalités manquées: {e}")

        messages.error(
            request,
            f"❌ Erreur lors de la correction des pénalités: {str(e)}"
        )

    # Rediriger vers la gestion des pénalités pour voir le résultat
    return redirect('payments:gestion_penalites')


# Ajout d'une fonction pour pardonner une pénalité
def pardonner_penalite(request, penalite_id):
    """Pardonner une pénalité spécifique"""
    if request.method == 'POST':
        penalite = get_object_or_404(Penalite, id=penalite_id)
        raison = request.POST.get('raison_pardon')

        if not raison:
            messages.error(request, "Une raison est obligatoire pour pardonner une pénalité.")
            return JsonResponse({'success': False, 'message': 'Raison obligatoire'})

        # Pardonner la pénalité
        penalite.statut = 'annulee'
        penalite.raison_annulation = raison
        penalite.pardonnee_par = request.user if request.user.is_authenticated else None
        penalite.date_pardon = timezone.now()
        penalite.save()

        client = penalite.get_client()
        client_nom = f"{client.prenom} {client.nom}" if client else "Client inconnu"

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Pénalité pardonnée pour {client_nom}'
            })
        else:
            messages.success(request, f'Pénalité pardonnée pour {client_nom}')
            return redirect('payments:gestion_penalites')

    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})


def tableau_bord_analytique(request):
    """Tableau de bord analytique global amélioré"""
    # Récupérer la période d'analyse
    periode = request.GET.get('periode', 'mois')  # Options: 'semaine', 'mois', 'trimestre', 'annee'
    aujourd_hui = date.today()

    # Déterminer les dates de début et fin selon la période
    if periode == 'semaine':
        date_debut = aujourd_hui - timedelta(days=aujourd_hui.weekday(), weeks=1)
        date_fin = date_debut + timedelta(days=6)
        periode_precedente_debut = date_debut - timedelta(weeks=1)
        periode_precedente_fin = date_debut - timedelta(days=1)
        format_date = '%d %b'
        titre_periode = f"Semaine du {date_debut.strftime('%d/%m')} au {date_fin.strftime('%d/%m/%Y')}"
    elif periode == 'mois':
        date_debut = aujourd_hui.replace(day=1)
        import calendar
        _, dernier_jour = calendar.monthrange(aujourd_hui.year, aujourd_hui.month)
        date_fin = aujourd_hui.replace(day=dernier_jour)

        # Mois précédent
        if aujourd_hui.month == 1:
            periode_precedente_debut = aujourd_hui.replace(year=aujourd_hui.year - 1, month=12, day=1)
            periode_precedente_fin = aujourd_hui.replace(year=aujourd_hui.year - 1, month=12, day=31)
        else:
            periode_precedente_debut = aujourd_hui.replace(month=aujourd_hui.month - 1, day=1)
            _, dernier_jour_prec = calendar.monthrange(aujourd_hui.year, aujourd_hui.month - 1)
            periode_precedente_fin = aujourd_hui.replace(month=aujourd_hui.month - 1, day=dernier_jour_prec)

        format_date = '%d %b'
        titre_periode = f"{date_debut.strftime('%B %Y')}"
    elif periode == 'trimestre':
        trimestre_actuel = (aujourd_hui.month - 1) // 3 + 1
        date_debut = date(aujourd_hui.year, (trimestre_actuel - 1) * 3 + 1, 1)

        if trimestre_actuel * 3 > 12:
            date_fin = date(aujourd_hui.year + 1, 1, 1) - timedelta(days=1)
        else:
            date_fin = date(aujourd_hui.year, trimestre_actuel * 3 + 1, 1) - timedelta(days=1)

        # Trimestre précédent
        if trimestre_actuel == 1:
            periode_precedente_debut = date(aujourd_hui.year - 1, 10, 1)
            periode_precedente_fin = date(aujourd_hui.year, 1, 1) - timedelta(days=1)
        else:
            periode_precedente_debut = date(aujourd_hui.year, (trimestre_actuel - 2) * 3 + 1, 1)
            periode_precedente_fin = date_debut - timedelta(days=1)

        format_date = '%b %Y'
        titre_periode = f"T{trimestre_actuel} {aujourd_hui.year}"
    else:  # annee
        date_debut = date(aujourd_hui.year, 1, 1)
        date_fin = date(aujourd_hui.year, 12, 31)
        periode_precedente_debut = date(aujourd_hui.year - 1, 1, 1)
        periode_precedente_fin = date(aujourd_hui.year - 1, 12, 31)
        format_date = '%b %Y'
        titre_periode = f"Année {aujourd_hui.year}"

    # Statistiques sur les contrats
    total_contrats_chauffeur = ContratChauffeur.objects.count()
    total_contrats_partenaire = ContratPartenaire.objects.count()
    total_contrats_batterie = ContratBatterie.objects.count()

    # Contrats par statut
    contrats_par_statut = {
        'chauffeur': {
            'actif': ContratChauffeur.objects.filter(statut='actif').count(),
            'termine': ContratChauffeur.objects.filter(statut='terminé').count(),
            'suspendu': ContratChauffeur.objects.filter(statut='suspendu').count(),
        },
        'partenaire': {
            'actif': ContratPartenaire.objects.filter(statut='actif').count(),
            'termine': ContratPartenaire.objects.filter(statut='terminé').count(),
            'suspendu': ContratPartenaire.objects.filter(statut='suspendu').count(),
        },
        'batterie': {
            'actif': ContratBatterie.objects.filter(statut='actif').count(),
            'termine': ContratBatterie.objects.filter(statut='terminé').count(),
            'suspendu': ContratBatterie.objects.filter(statut='suspendu').count(),
        }
    }

    # Paiements de la période courante
    paiements_periode = Paiement.objects.filter(
        date_paiement__gte=date_debut,
        date_paiement__lte=date_fin
    )
    montant_paiements_periode = paiements_periode.aggregate(total=Sum('montant_total'))['total'] or 0

    # Paiements de la période précédente
    paiements_periode_precedente = Paiement.objects.filter(
        date_paiement__gte=periode_precedente_debut,
        date_paiement__lte=periode_precedente_fin
    )
    montant_paiements_periode_precedente = paiements_periode_precedente.aggregate(total=Sum('montant_total'))[
                                               'total'] or 0

    # Variation en pourcentage
    if montant_paiements_periode_precedente > 0:
        variation_paiements = abs((
                                              montant_paiements_periode - montant_paiements_periode_precedente) / montant_paiements_periode_precedente) * 100
    else:
        variation_paiements = 100 if montant_paiements_periode > 0 else 0

    # Pénalités actives
    penalites_actives = Penalite.objects.filter(statut='en_attente')
    montant_penalites_actives = penalites_actives.aggregate(total=Sum('montant'))['total'] or 0

    # Pénalités de la période
    penalites_periode = Penalite.objects.filter(
        date_creation__date__gte=date_debut,
        date_creation__date__lte=date_fin
    )
    montant_penalites_periode = penalites_periode.aggregate(total=Sum('montant'))['total'] or 0

    # Paiements par type de contrat
    paiements_par_type = paiements_periode.values('type_contrat').annotate(
        montant=Sum('montant_total'),
        count=Count('id')
    ).order_by('type_contrat')

    # Répartition des méthodes de paiement
    paiements_par_methode = paiements_periode.values('methode_paiement').annotate(
        montant=Sum('montant_total'),
        count=Count('id')
    ).order_by('methode_paiement')

    # Convertir pour le graphique
    methodes_labels = [dict(Paiement.METHODE_CHOICES).get(p['methode_paiement'], p['methode_paiement']) for p in
                       paiements_par_methode]
    methodes_data = [float(p['montant']) for p in paiements_par_methode]
    methodes_counts = [p['count'] for p in paiements_par_methode]

    # Paiements par jour sur la période
    paiements_par_jour = {}

    delta = date_fin - date_debut
    for i in range(delta.days + 1):
        date_curr = date_debut + timedelta(days=i)
        paiements_jour = paiements_periode.filter(date_paiement=date_curr)
        montant_jour = paiements_jour.aggregate(total=Sum('montant_total'))['total'] or 0
        nb_paiements = paiements_jour.count()

        paiements_par_jour[date_curr.strftime('%Y-%m-%d')] = {
            'date_affichage': date_curr.strftime(format_date),
            'montant': float(montant_jour),
            'count': nb_paiements
        }

    # Trier par date
    paiements_par_jour_tries = [
        {'date': k, 'date_affichage': v['date_affichage'], 'montant': v['montant'], 'count': v['count']}
        for k, v in sorted(paiements_par_jour.items())
    ]

    # Top 5 des clients avec le plus de pénalités
    top_clients_penalites = []

    # Pour les chauffeurs

    chauffeurs_penalites = ValidatedUser.objects.annotate(
        nb_penalites=Count(
            'associations_user__association_user_motos__penalites',
            filter=Q(associations_user__association_user_motos__penalites__statut='en_attente')
        )
    ).filter(nb_penalites__gt=0).order_by('-nb_penalites')[:5]

    for chauffeur in chauffeurs_penalites:
        # Récupère tous les contrats chauffeur de ce user
        contrats = ContratChauffeur.objects.filter(
            association__validated_user=chauffeur
        )
        montant_total = Penalite.objects.filter(
            Q(contrat_chauffeur__in=contrats) | Q(contrat_batterie__chauffeur=chauffeur),
            statut='en_attente'
        ).aggregate(total=Sum('montant'))['total'] or 0

        top_clients_penalites.append({
            'type': 'Chauffeur',
            'nom': f"{chauffeur.prenom} {chauffeur.nom}",
            'id': chauffeur.id,
            'nb_penalites': chauffeur.nb_penalites,
            'montant_total': montant_total
        })

    # Pour les partenaires
    partenaires_penalites = Partenaire.objects.annotate(
        nb_penalites=Count('contrats__penalites', filter=Q(contrats__penalites__statut='en_attente'))
    ).filter(nb_penalites__gt=0).order_by('-nb_penalites')[:5]

    for partenaire in partenaires_penalites:
        montant_total = Penalite.objects.filter(
            Q(contrat_partenaire__partenaire=partenaire) | Q(contrat_batterie__partenaire=partenaire),
            statut='en_attente'
        ).aggregate(total=Sum('montant'))['total'] or 0

        top_clients_penalites.append({
            'type': 'Partenaire',
            'nom': f"{partenaire.prenom} {partenaire.nom}",
            'id': partenaire.id,
            'nb_penalites': partenaire.nb_penalites,
            'montant_total': montant_total
        })

    # Trier le top par nombre de pénalités
    top_clients_penalites.sort(key=lambda x: x['nb_penalites'], reverse=True)
    top_clients_penalites = top_clients_penalites[:5]  # Limiter à 5 résultats

    # Statistiques sur les swaps
    swaps_periode = Swap.objects.filter(
        swap_date__date__gte=date_debut,
        swap_date__date__lte=date_fin
    )

    nb_swaps = swaps_periode.count()
    montant_swaps = swaps_periode.aggregate(total=Sum('swap_price'))['total'] or 0

    # Moyenne de swaps par jour
    nb_jours = (date_fin - date_debut).days + 1
    moyenne_swaps_jour = nb_swaps / nb_jours if nb_jours > 0 else 0

    # Prévisions pour le mois suivant (basées sur tendances)
    # ... (code pour calcul des prévisions)

    context = {
        'titre': 'Tableau de Bord Analytique',
        'titre_periode': titre_periode,
        'periode': periode,
        'total_contrats_chauffeur': total_contrats_chauffeur,
        'total_contrats_partenaire': total_contrats_partenaire,
        'total_contrats_batterie': total_contrats_batterie,
        'contrats_par_statut': contrats_par_statut,
        'montant_paiements_periode': montant_paiements_periode,
        'montant_paiements_periode_precedente': montant_paiements_periode_precedente,
        'variation_paiements': variation_paiements,
        'penalites_actives': penalites_actives.count(),
        'montant_penalites_actives': montant_penalites_actives,
        'montant_penalites_periode': montant_penalites_periode,
        'paiements_par_jour': json.dumps(paiements_par_jour_tries),
        'methodes_labels': json.dumps(methodes_labels),
        'methodes_data': json.dumps(methodes_data),
        'methodes_counts': json.dumps(methodes_counts),
        'top_clients_penalites': top_clients_penalites,
        'nb_swaps': nb_swaps,
        'montant_swaps': montant_swaps,
        'moyenne_swaps_jour': moyenne_swaps_jour,
    }

    return render(request, 'payments/analytique.html', context)


def liste_swaps(request):
    """Gestion des swaps (échanges de batteries)"""
    # Filtres GET
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    station = request.GET.get('station')
    q = request.GET.get('q')

    # Date du jour si non spécifiée
    if not date_debut:
        date_debut = date.today().strftime('%Y-%m-%d')

    swaps = Swap.objects.all()

    # Filtrage par date
    if date_debut:
        try:
            date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date()
            swaps = swaps.filter(swap_date__date__gte=date_debut_obj)
        except ValueError:
            pass

    if date_fin:
        try:
            date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
            swaps = swaps.filter(swap_date__date__lte=date_fin_obj)
        except ValueError:
            pass

    # Filtrage par station
    if station:
        swaps = swaps.filter(id_agence=station)

    # Recherche
    if q:
        swaps = swaps.filter(
            Q(nom__icontains=q) |
            Q(prenom__icontains=q) |
            Q(phone__icontains=q)
        )

    # Statistiques
    total_swaps = swaps.count()
    montant_total = swaps.aggregate(total=Sum('swap_price'))['total'] or 0

    # Par station
    if date_debut and date_fin:
        swaps_par_station = swaps.values('id_agence').annotate(
            count=Count('id'),
            montant=Sum('swap_price')
        ).order_by('-count')
        stations_labels = [str(s['id_agence']) for s in swaps_par_station]
        stations_data = [float(s['montant']) or 0 for s in swaps_par_station]
        stations_counts = [s['count'] for s in swaps_par_station]
    else:
        swaps_par_station = []
        stations_labels = []
        stations_data = []
        stations_counts = []

    # Moyenne par jour
    try:
        if date_debut and date_fin:
            date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date()
            date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
            nb_jours = (date_fin_obj - date_debut_obj).days + 1
        else:
            date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date()
            date_fin_obj = date_debut_obj
            nb_jours = 1
        moyenne_swaps_jour = total_swaps / nb_jours if nb_jours > 0 else total_swaps
    except:
        moyenne_swaps_jour = 0

    # Pagination
    paginator = Paginator(swaps.order_by('-swap_date'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Données enrichies
    swaps_enrichis = []
    for swap in page_obj:
        swaps_enrichis.append({
            'id': swap.id,
            'swap_date': swap.swap_date,
            'station_id': swap.id_agence,
            'client_nom': f"{swap.prenom or ''} {swap.nom or ''}",
            'phone': swap.phone,
            'montant': swap.swap_price,
            'batterie_entree': swap.battery_in_id,
            'batterie_sortie': swap.battery_out_id,
            'niveau_charge_entree': swap.battery_in_soc,
            'niveau_charge_sortie': swap.battery_out_soc,
        })

    # Liste des stations (uniquement les ID ici)
    stations = Swap.objects.values('id_agence').distinct().order_by('id_agence')

    context = {
        'titre': 'Transactions de Swap',
        'swaps': swaps_enrichis,
        'page_obj': page_obj,
        'total_swaps': total_swaps,
        'montant_total': montant_total,
        'moyenne_swaps_jour': moyenne_swaps_jour,
        'stations': stations,
        'filtres': {
            'date_debut': date_debut,
            'date_fin': date_fin,
            'station': station,
            'q': q,
        },
        'stations_labels': json.dumps(stations_labels),
        'stations_data': json.dumps(stations_data),
        'stations_counts': json.dumps(stations_counts),
        'statut_choices': [],  # À remplir si tu ajoutes un champ statut
    }

    return render(request, 'payments/swaps/liste.html', context)


def configuration_penalites(request):
    """Page de configuration des règles de pénalités"""
    regles = ReglePenalite.objects.all()

    if request.method == 'POST':
        form = ReglePenaliteForm(request.POST)
        if form.is_valid():
            # Création ou mise à jour d'une règle
            regle = form.save()

            # Si cette règle est activée, désactiver les autres du même type
            if regle.est_active:
                ReglePenalite.objects.filter(
                    type_contrat=regle.type_contrat
                ).exclude(id=regle.id).update(est_active=False)

            messages.success(request, f"Règle de pénalité '{regle.nom_regle}' enregistrée avec succès.")
            return redirect('payments:configuration_penalites')
    else:
        form = ReglePenaliteForm()

    context = {
        'titre': 'Configuration des Règles de Pénalités',
        'regles': regles,
        'form': form,
    }

    return render(request, 'payments/configuration/penalites.html', context)


def modifier_regle_penalite(request, regle_id):
    """Modifier une règle de pénalité existante"""
    regle = get_object_or_404(ReglePenalite, id=regle_id)

    if request.method == 'POST':
        form = ReglePenaliteForm(request.POST, instance=regle)
        if form.is_valid():
            # Mise à jour de la règle
            regle = form.save()

            # Si cette règle est activée, désactiver les autres du même type
            if regle.est_active:
                ReglePenalite.objects.filter(
                    type_contrat=regle.type_contrat
                ).exclude(id=regle.id).update(est_active=False)

            messages.success(request, f"Règle de pénalité '{regle.nom_regle}' mise à jour avec succès.")
            return redirect('payments:configuration_penalites')
    else:
        form = ReglePenaliteForm(instance=regle)

    context = {
        'titre': f'Modifier la règle de pénalité - {regle.nom_regle}',
        'form': form,
        'regle': regle,
    }

    return render(request, 'payments/configuration/modifier_regle.html', context)


def supprimer_regle_penalite(request, regle_id):
    """Supprimer une règle de pénalité"""
    regle = get_object_or_404(ReglePenalite, id=regle_id)

    if request.method == 'POST':
        nom_regle = regle.nom_regle
        regle.delete()
        messages.success(request, f"Règle de pénalité '{nom_regle}' supprimée avec succès.")
        return redirect('payments:configuration_penalites')

    context = {
        'titre': f'Supprimer la règle de pénalité - {regle.nom_regle}',
        'regle': regle,
    }

    return render(request, 'payments/configuration/supprimer_regle.html', context)


def basculer_etat_regle(request, regle_id):
    """Activer/désactiver une règle de pénalité via AJAX"""
    if request.method == 'POST' and request.is_ajax():
        regle = get_object_or_404(ReglePenalite, id=regle_id)

        # Inverser l'état actif/inactif
        regle.est_active = not regle.est_active
        regle.save()

        # Si activée, désactiver les autres règles du même type
        if regle.est_active:
            ReglePenalite.objects.filter(
                type_contrat=regle.type_contrat
            ).exclude(id=regle.id).update(est_active=False)

        return JsonResponse({
            'success': True,
            'est_active': regle.est_active,
            'message': f"Règle '{regle.nom_regle}' {'activée' if regle.est_active else 'désactivée'} avec succès."
        })

    return JsonResponse({'success': False, 'message': "Méthode non autorisée"}, status=405)


@require_POST
def traiter_penalites_groupees(request):
    """Traiter plusieurs pénalités en une seule action"""
    penalites_ids = request.POST.get('penalites_ids', '')
    action = request.POST.get('action', '')
    raison = request.POST.get('raison', '')
    methode_paiement = request.POST.get('methode_paiement', 'espece')
    date_report = request.POST.get('date_report', '')
    envoyer_notification = 'envoyer_notification' in request.POST

    if not penalites_ids or not action:
        messages.error(request, "Paramètres manquants pour l'action groupée.")
        return redirect('payments:gestion_penalites')

    # Convertir les IDs en liste d'entiers
    try:
        ids_list = [int(id.strip()) for id in penalites_ids.split(',') if id.strip()]
    except ValueError:
        messages.error(request, "IDs de pénalités invalides.")
        return redirect('payments:gestion_penalites')

    # Récupérer les pénalités concernées
    penalites = Penalite.objects.filter(id__in=ids_list, statut='en_attente')

    if not penalites.exists():
        messages.error(request, "Aucune pénalité en attente trouvée avec ces IDs.")
        return redirect('payments:gestion_penalites')

    nb_traitees = 0
    user = request.user if request.user.is_authenticated else None

    try:
        with transaction.atomic():
            for penalite in penalites:
                if action == 'payer':
                    # Créer un paiement pour la pénalité
                    paiement = Paiement.objects.create(
                        montant=penalite.montant,
                        date_paiement=date.today(),
                        heure_paiement=timezone.now().time(),
                        methode_paiement=methode_paiement,
                        reference_transaction='',
                        notes=f"Paiement groupé de pénalité: {raison}" if raison else "Paiement groupé de pénalité",
                        est_penalite=True,
                        enregistre_par=user,
                        reference=f"PEN-{uuid.uuid4().hex[:8].upper()}",
                        # Associer au bon type de contrat
                        contrat_chauffeur=penalite.contrat_chauffeur,
                        contrat_partenaire=penalite.contrat_partenaire,
                        contrat_batterie=penalite.contrat_batterie,
                        type_contrat=penalite.type_penalite if penalite.type_penalite == 'batterie' else (
                            'chauffeur' if penalite.contrat_chauffeur else 'partenaire'
                        )
                    )

                    # Marquer la pénalité comme payée
                    penalite.statut = 'payee'
                    penalite.paiement = paiement
                    penalite.date_modification = timezone.now()
                    penalite.modifie_par = user
                    penalite.raison_annulation = raison
                    penalite.save()

                elif action == 'annuler':
                    # Annuler la pénalité
                    penalite.statut = 'annulee'
                    penalite.date_modification = timezone.now()
                    penalite.modifie_par = user
                    penalite.raison_annulation = raison
                    penalite.save()

                elif action == 'reporter':
                    # Reporter la pénalité
                    if date_report:
                        try:
                            date_report_obj = datetime.strptime(date_report, '%Y-%m-%d').date()
                            penalite.statut = 'reportee'
                            penalite.date_modification = timezone.now()
                            penalite.modifie_par = user
                            penalite.raison_annulation = f"Reportée au {date_report_obj.strftime('%d/%m/%Y')}. {raison}" if raison else f"Reportée au {date_report_obj.strftime('%d/%m/%Y')}"
                            penalite.save()
                        except ValueError:
                            continue  # Ignorer cette pénalité si la date est invalide
                    else:
                        continue  # Ignorer si pas de date de report

                nb_traitees += 1

                # Envoyer une notification si demandé
                if envoyer_notification:
                    try:
                        client = penalite.get_client()
                        if client:
                            message_map = {
                                'payer': f"Votre pénalité de {penalite.montant} FCFA a été réglée.",
                                'annuler': f"Votre pénalité de {penalite.montant} FCFA a été annulée." + (
                                    f" Raison: {raison}" if raison else ""),
                                'reporter': f"Votre pénalité de {penalite.montant} FCFA a été reportée." + (
                                    f" {raison}" if raison else "")
                            }

                            notification = NotificationPaiement.objects.create(
                                type_notification='penalite',
                                message=message_map.get(action, ''),
                                date_programmee=timezone.now(),
                                canal_notification='sms',
                                chauffeur=client if hasattr(client, 'contrats_chauffeur') else None,
                                partenaire=client if hasattr(client, 'contrats_partenaire') else None,
                                penalite=penalite,
                                contrat_chauffeur=penalite.contrat_chauffeur,
                                contrat_partenaire=penalite.contrat_partenaire,
                                contrat_batterie=penalite.contrat_batterie
                            )
                    except Exception as e:
                        # Ne pas faire échouer l'action si la notification échoue
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Erreur envoi notification pénalité {penalite.id}: {e}")

        # Message de succès
        action_text = {
            'payer': 'marquées comme payées',
            'annuler': 'annulées',
            'reporter': 'reportées'
        }

        messages.success(
            request,
            f"✅ {nb_traitees} pénalité(s) ont été {action_text.get(action, 'traitées')} avec succès."
        )

        if envoyer_notification:
            messages.info(
                request,
                f"📱 Des notifications ont été envoyées aux clients concernés."
            )

    except Exception as e:
        messages.error(
            request,
            f"❌ Erreur lors du traitement groupé: {str(e)}"
        )
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur traitement groupé pénalités: {e}")

    return redirect('payments:gestion_penalites')


def export_paiements(request):
    """Exporter les paiements en CSV"""
    # Récupérer les filtres depuis la session ou les paramètres GET
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    type_contrat = request.GET.get('type_contrat')
    methode = request.GET.get('methode')
    est_penalite = request.GET.get('penalites') == '1'
    q = request.GET.get('q')

    # Filtrer les paiements
    paiements = Paiement.objects.all()

    if date_debut:
        try:
            date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date()
            paiements = paiements.filter(date_paiement__gte=date_debut_obj)
        except ValueError:
            pass

    if date_fin:
        try:
            date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
            paiements = paiements.filter(date_paiement__lte=date_fin_obj)
        except ValueError:
            pass

    if type_contrat:
        paiements = paiements.filter(type_contrat=type_contrat)

    if methode:
        paiements = paiements.filter(methode_paiement=methode)

    if est_penalite:
        paiements = paiements.filter(est_penalite=True)

    if q:
        # Recherche par référence, client, ou contrat
        paiements = paiements.filter(
            Q(reference__icontains=q) |
            Q(contrat_chauffeur__chauffeur__nom__icontains=q) |
            Q(contrat_chauffeur__chauffeur__prenom__icontains=q) |
            Q(contrat_partenaire__partenaire__nom__icontains=q) |
            Q(contrat_partenaire__partenaire__prenom__icontains=q) |
            Q(contrat_batterie__reference__icontains=q) |
            Q(contrat_chauffeur__reference__icontains=q) |
            Q(contrat_partenaire__reference__icontains=q)
        )

    # Créer la réponse CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="paiements_{date.today().strftime("%Y%m%d")}.csv"'

    # Créer le writer CSV avec en-têtes
    writer = csv.writer(response)
    writer.writerow([
        'Référence', 'Montant', 'Date de paiement', 'Heure', 'Méthode',
        'Type de contrat', 'Client', 'Est pénalité', 'Référence transaction', 'Notes'
    ])

    # Ajouter les données
    for paiement in paiements:
        client_info = paiement.get_client_info()

        writer.writerow([
            paiement.reference,
            paiement.montant,
            paiement.date_paiement.strftime('%d/%m/%Y'),
            paiement.heure_paiement.strftime('%H:%M') if paiement.heure_paiement else '',
            paiement.get_methode_paiement_display(),
            paiement.get_type_contrat_display(),
            client_info.get('nom', 'Inconnu'),
            'Oui' if paiement.est_penalite else 'Non',
            paiement.reference_transaction or '',
            paiement.notes or ''
        ])

    return response


def export_penalites(request):
    """Exporter les pénalités en CSV"""
    # Récupérer les filtres
    statut = request.GET.get('statut')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    q = request.GET.get('q')

    # Filtrer les pénalités
    penalites = Penalite.objects.all()

    if statut:
        penalites = penalites.filter(statut=statut)

    if date_debut:
        try:
            date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date()
            penalites = penalites.filter(date_creation__date__gte=date_debut_obj)
        except ValueError:
            pass

    if date_fin:
        try:
            date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
            penalites = penalites.filter(date_creation__date__lte=date_fin_obj)
        except ValueError:
            pass

    if q:
        # Recherche par client, description, etc.
        penalites = penalites.filter(
            Q(contrat_chauffeur__chauffeur__nom__icontains=q) |
            Q(contrat_chauffeur__chauffeur__prenom__icontains=q) |
            Q(contrat_partenaire__partenaire__nom__icontains=q) |
            Q(contrat_partenaire__partenaire__prenom__icontains=q) |
            Q(description__icontains=q)
        )

    # Créer la réponse CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="penalites_{date.today().strftime("%Y%m%d")}.csv"'

    # Créer le writer CSV avec en-têtes
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Client', 'Type client', 'Montant', 'Date création', 'Motif',
        'Type pénalité', 'Statut', 'Contrat', 'Date paiement', 'Description', 'Raison annulation'
    ])

    # Ajouter les données
    for penalite in penalites:
        client = penalite.get_client()
        client_nom = f"{client.prenom} {client.nom}" if client else "Inconnu"
        client_type = "Chauffeur" if isinstance(client, Chauffeur) else "Partenaire" if isinstance(client,
                                                                                                   Partenaire) else "Inconnu"

        writer.writerow([
            penalite.id,
            client_nom,
            client_type,
            penalite.montant,
            penalite.date_creation.strftime('%d/%m/%Y %H:%M'),
            penalite.get_motif_display(),
            penalite.get_type_penalite_display(),
            penalite.get_statut_display(),
            penalite.get_contract_reference(),
            penalite.date_paiement_manque.strftime('%d/%m/%Y') if penalite.date_paiement_manque else '',
            penalite.description or '',
            penalite.raison_annulation or ''
        ])

    return response


def gerer_notifications(request):
    """Gérer les notifications envoyées aux clients"""
    # Filtres
    statut = request.GET.get('statut')
    type_notification = request.GET.get('type')
    canal = request.GET.get('canal')
    q = request.GET.get('q')

    # Base de requête
    notifications = NotificationPaiement.objects.all().order_by('-date_programmee')

    if statut:
        notifications = notifications.filter(statut=statut)

    if type_notification:
        notifications = notifications.filter(type_notification=type_notification)

    if canal:
        notifications = notifications.filter(canal_notification=canal)

    if q:
        # Recherche par client ou message
        notifications = notifications.filter(
            Q(chauffeur__nom__icontains=q) |
            Q(chauffeur__prenom__icontains=q) |
            Q(partenaire__nom__icontains=q) |
            Q(partenaire__prenom__icontains=q) |
            Q(message__icontains=q)
        )

    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Enrichir les données
    notifications_enrichies = []
    for notif in page_obj:
        client_nom = ""
        client_type = ""

        if notif.chauffeur:
            client_nom = f"{notif.chauffeur.prenom} {notif.chauffeur.nom}"
            client_type = "Chauffeur"
        elif notif.partenaire:
            client_nom = f"{notif.partenaire.prenom} {notif.partenaire.nom}"
            client_type = "Partenaire"

        contrat_reference = ""
        if notif.contrat_chauffeur:
            contrat_reference = notif.contrat_chauffeur.reference
        elif notif.contrat_partenaire:
            contrat_reference = notif.contrat_partenaire.reference
        elif notif.contrat_batterie:
            contrat_reference = notif.contrat_batterie.reference

        notifications_enrichies.append({
            'id': notif.id,
            'client_nom': client_nom,
            'client_type': client_type,
            'type': notif.get_type_notification_display(),
            'message': notif.message,
            'date_programmee': notif.date_programmee,
            'statut': notif.get_statut_display(),
            'canal': notif.get_canal_notification_display(),
            'contrat_reference': contrat_reference,
            'date_envoi': notif.date_envoi,
            'est_lue': notif.est_lue,
            'date_lecture': notif.date_lecture
        })

    context = {
        'titre': 'Gestion des Notifications',
        'notifications': notifications_enrichies,
        'page_obj': page_obj,
        'filtres': {
            'statut': statut,
            'type': type_notification,
            'canal': canal,
            'q': q
        },
        'statut_choices': NotificationPaiement.STATUT_CHOICES,
        'type_choices': NotificationPaiement.TYPE_CHOICES,
        'canal_choices': [
            ('sms', 'SMS'),
            ('whatsapp', 'WhatsApp'),
            ('app', 'Application mobile'),
            ('email', 'Email'),
            ('appel', 'Appel téléphonique'),
        ]
    }

    return render(request, 'payments/notifications/liste.html', context)


def creer_notification(request):
    """Créer une nouvelle notification pour les clients"""
    if request.method == 'POST':
        # Récupérer les données du formulaire
        type_notification = request.POST.get('type_notification')
        message = request.POST.get('message')
        canal_notification = request.POST.get('canal_notification', 'sms')

        client_type = request.POST.get('client_type')
        clients_ids = request.POST.getlist('clients_ids', [])

        if type_notification and message and client_type and clients_ids:
            nb_notifs = 0

            # Créer une notification pour chaque client sélectionné
            for client_id in clients_ids:
                notification = NotificationPaiement()
                notification.type_notification = type_notification
                notification.message = message
                notification.date_programmee = timezone.now()
                notification.canal_notification = canal_notification

                # Associer au bon type de client
                if client_type == 'chauffeur':
                    try:
                        chauffeur = Chauffeur.objects.get(id=int(client_id))
                        notification.chauffeur = chauffeur

                        # Récupérer le contrat actif si existant
                        contrat = ContratChauffeur.objects.filter(
                            chauffeur=chauffeur,
                            statut='actif'
                        ).first()

                        if contrat:
                            notification.contrat_chauffeur = contrat

                        notification.save()
                        nb_notifs += 1
                    except Chauffeur.DoesNotExist:
                        continue

                elif client_type == 'partenaire':
                    try:
                        partenaire = Partenaire.objects.get(id=int(client_id))
                        notification.partenaire = partenaire

                        # Récupérer le contrat actif si existant
                        contrat = ContratPartenaire.objects.filter(
                            partenaire=partenaire,
                            statut='actif'
                        ).first()

                        if contrat:
                            notification.contrat_partenaire = contrat

                        notification.save()
                        nb_notifs += 1
                    except Partenaire.DoesNotExist:
                        continue

            messages.success(request, f"{nb_notifs} notifications créées avec succès.")
            return redirect('payments:gerer_notifications')
        else:
            messages.error(request, "Veuillez remplir tous les champs requis.")

    # Récupérer des listes de clients pour le formulaire
    chauffeurs = Chauffeur.objects.all().order_by('nom', 'prenom')
    partenaires = Partenaire.objects.all().order_by('nom', 'prenom')

    # Filtrer pour ne montrer que les clients avec contrats actifs
    chauffeurs_actifs = chauffeurs.filter(contrats_chauffeur__statut='actif').distinct()
    partenaires_actifs = partenaires.filter(contrats_partenaire__statut='actif').distinct()

    context = {
        'titre': 'Créer une Notification',
        'chauffeurs': chauffeurs_actifs,
        'partenaires': partenaires_actifs,
        'type_choices': NotificationPaiement.TYPE_CHOICES,
        'canal_choices': [
            ('sms', 'SMS'),
            ('whatsapp', 'WhatsApp'),
            ('app', 'Application mobile'),
            ('email', 'Email'),
            ('appel', 'Appel téléphonique'),
        ]
    }

    return render(request, 'payments/notifications/creer.html', context)


def programmation_notifications(request):
    """Configurer la programmation automatique des notifications"""
    # Logique pour configurer la programmation
    # ...

    context = {
        'titre': 'Programmation des Notifications',
        # Autres données de contexte
    }

    return render(request, 'payments/notifications/programmation.html', context)


def details_paiement(request, paiement_id):
    """Afficher les détails d'un paiement"""
    paiement = get_object_or_404(Paiement, id=paiement_id)

    # Récupérer les informations client
    client_info = paiement.get_client_info()

    # Récupérer les pénalités liées à ce paiement
    penalites = Penalite.objects.filter(paiement=paiement)

    # Récupérer la transaction swap si applicable
    swap = None
    try:
        swap = paiement.swap_transaction
    except:
        pass

    context = {
        'titre': f'Détails du paiement {paiement.reference}',
        'paiement': paiement,
        'client_info': client_info,
        'penalites': penalites,
        'swap': swap,
    }

    return render(request, 'payments/details_paiement.html', context)


def recherche_avancee(request):
    """Recherche avancée avec filtres multiples"""
    # Initialiser le formulaire de recherche
    form = RechercheAvanceeForm(request.GET)

    resultats = []
    a_recherche = False

    if form.is_valid() and any(form.cleaned_data.values()):
        a_recherche = True
        # Filtres de base
        q = form.cleaned_data.get('q')
        type_contrat = form.cleaned_data.get('type_contrat')
        statut = form.cleaned_data.get('statut')
        frequence = form.cleaned_data.get('frequence')
        date_debut = form.cleaned_data.get('date_debut')
        date_fin = form.cleaned_data.get('date_fin')
        statut_paiement = form.cleaned_data.get('statut_paiement')

        # Construire la requête pour chaque type de contrat
        if not type_contrat or type_contrat == 'chauffeur':
            contrats_chauffeur = ContratChauffeur.objects.all()

            if statut:
                contrats_chauffeur = contrats_chauffeur.filter(statut=statut)

            if frequence:
                contrats_chauffeur = contrats_chauffeur.filter(frequence_paiement=frequence)

            if date_debut:
                contrats_chauffeur = contrats_chauffeur.filter(date_debut__gte=date_debut)

            if date_fin:
                contrats_chauffeur = contrats_chauffeur.filter(date_fin__lte=date_fin)

            if q:
                contrats_chauffeur = contrats_chauffeur.filter(
                    Q(reference__icontains=q) |
                    Q(chauffeur__nom__icontains=q) |
                    Q(chauffeur__prenom__icontains=q) |
                    Q(chauffeur__telephone__icontains=q) |
                    Q(chauffeur__numero_cni__icontains=q)
                )

            # Filtrer par statut de paiement
            if statut_paiement:
                if statut_paiement == 'a_jour':
                    # Filtrer les contrats à jour
                    contrats_chauffeur = contrats_chauffeur.filter(
                        Q(montant_restant=0) |
                        Q(derniere_date_paiement__gte=date.today() - timedelta(days=1))
                    )
                elif statut_paiement == 'retard':
                    # Filtrer les contrats en retard
                    contrats_chauffeur = contrats_chauffeur.filter(
                        montant_restant__gt=0,
                        derniere_date_paiement__lt=date.today() - timedelta(days=1)
                    )
                elif statut_paiement == 'penalites':
                    # Filtrer les contrats avec pénalités actives
                    contrats_chauffeur = contrats_chauffeur.filter(
                        penalites__statut='en_attente'
                    ).distinct()

            # Ajouter les résultats
            for contrat in contrats_chauffeur:
                resultats.append({
                    'type': 'chauffeur',
                    'id': contrat.id,
                    'reference': contrat.reference,
                    'client_nom': f"{contrat.chauffeur.prenom} {contrat.chauffeur.nom}",
                    'client_telephone': contrat.chauffeur.telephone,
                    'statut': contrat.get_statut_display(),
                    'date_debut': contrat.date_debut,
                    'date_fin': contrat.date_fin,
                    'montant_total': contrat.montant_total,
                    'montant_restant': contrat.montant_restant,
                    'frequence': contrat.get_frequence_paiement_display(),
                    'lien': reverse('contrats:details_contrat_chauffeur', args=[contrat.id]),
                    'paiement_rapide': reverse('payments:paiement_rapide', args=['chauffeur', contrat.id]),
                })

        # Répéter pour les contrats partenaire
        if not type_contrat or type_contrat == 'partenaire':
            # ... (logique similaire à celle des contrats chauffeur)
            pass

        # Répéter pour les contrats batterie
        if not type_contrat or type_contrat == 'batterie':
            # ... (logique similaire à celle des contrats chauffeur)
            pass

    context = {
        'titre': 'Recherche Avancée',
        'form': form,
        'resultats': resultats,
        'a_recherche': a_recherche,
        'count': len(resultats),
    }

    return render(request, 'payments/recherche_avancee.html', context)


from django.views.decorators.http import require_POST

from django.views.decorators.http import require_POST
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from datetime import date, time, timedelta
from decimal import Decimal

from contrats.models import Partenaire, ContratChauffeur, ContratPartenaire, ContratBatterie
from .models import Paiement, Penalite, ReglePenalite


from datetime import time
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction

@require_POST
def appliquer_penalites_view(request):
    """Applique les pénalités uniquement pour AUJOURD’HUI (pas de rétroactif)."""
    aujourd_hui = timezone.localdate()
    heure_actuelle = timezone.localtime().time()
    user = request.user if request.user.is_authenticated else None

    HEURE_PENALITE = time(13, 1)  # ajuste si besoin (ex: 12:01 ou 14:01)
    penalites_creees = 0

    if heure_actuelle < HEURE_PENALITE:
        messages.info(request, "Trop tôt pour appliquer les pénalités aujourd’hui.")
        return redirect('payments:gestion_penalites')

    with transaction.atomic():
        # 1) Contrats CHAUFFEUR
        for contrat in ContratChauffeur.objects.filter(statut='actif').select_related('association__validated_user'):
            if not _est_jour_de_paiement(contrat, aujourd_hui):
                continue

            # Paiement déjà fait aujourd’hui (hors pénalité) ?
            if Paiement.objects.filter(
                contrat_chauffeur=contrat,
                date_paiement=aujourd_hui,
                est_penalite=False
            ).exists():
                continue

            # En congé aujourd’hui ?
            est_en_conge = CongesChauffeur.objects.filter(
                contrat=contrat,
                date_debut__lte=aujourd_hui,
                date_fin__gte=aujourd_hui,
                statut__in=['approuvé', 'planifié', 'en_cours']
            ).exists()
            if est_en_conge:
                continue

            # Type de pénalité (combine si une batterie active est liée au chauffeur)
            has_battery = ContratBatterie.objects.filter(
                chauffeur=contrat.association.validated_user,
                statut='actif'
            ).exists()
            type_penalite = 'combine' if has_battery else 'batterie_seule'

            montant, motif = ReglePenalite.get_penalite_applicable(type_penalite, heure_actuelle)
            if montant <= 0:
                continue

            _, created = Penalite.objects.get_or_create(
                contrat_chauffeur=contrat,
                date_paiement_manque=aujourd_hui,
                defaults={
                    'contrat_reference': contrat.reference,
                    'type_penalite': type_penalite,
                    'montant': montant,
                    'motif': motif,
                    'description': f"Pénalité automatique pour retard du {aujourd_hui.strftime('%d/%m/%Y')}",
                    'statut': 'en_attente',
                    'cree_par': user,
                }
            )
            if created:
                penalites_creees += 1

        # 2) Contrats PARTENAIRE
        for contrat in ContratPartenaire.objects.filter(statut='actif').select_related('partenaire'):
            if not _est_jour_de_paiement(contrat, aujourd_hui):
                continue

            if Paiement.objects.filter(
                contrat_partenaire=contrat,
                date_paiement=aujourd_hui,
                est_penalite=False
            ).exists():
                continue

            has_battery = ContratBatterie.objects.filter(
                partenaire=contrat.partenaire,
                statut='actif'
            ).exists()
            type_penalite = 'combine' if has_battery else 'batterie_seule'

            montant, motif = ReglePenalite.get_penalite_applicable(type_penalite, heure_actuelle)
            if montant <= 0:
                continue

            _, created = Penalite.objects.get_or_create(
                contrat_partenaire=contrat,
                date_paiement_manque=aujourd_hui,
                defaults={
                    'contrat_reference': contrat.reference,
                    'type_penalite': type_penalite,
                    'montant': montant,
                    'motif': motif,
                    'description': f"Pénalité automatique pour retard du {aujourd_hui.strftime('%d/%m/%Y')}",
                    'statut': 'en_attente',
                    'cree_par': user,
                }
            )
            if created:
                penalites_creees += 1

        # 3) Contrats BATTERIE STANDALONE
        for contrat in ContratBatterie.objects.filter(statut='actif').select_related('chauffeur', 'partenaire'):
            # standalone = pas de contrat chauffeur/partenaire actif pour cet acteur
            is_standalone = True
            if contrat.chauffeur and ContratChauffeur.objects.filter(
                association__validated_user=contrat.chauffeur, statut='actif'
            ).exists():
                is_standalone = False
            if contrat.partenaire and ContratPartenaire.objects.filter(
                partenaire=contrat.partenaire, statut='actif'
            ).exists():
                is_standalone = False
            if not is_standalone:
                continue

            if not _est_jour_de_paiement(contrat, aujourd_hui):
                continue

            if Paiement.objects.filter(
                contrat_batterie=contrat,
                date_paiement=aujourd_hui,
                est_penalite=False
            ).exists():
                continue

            montant, motif = ReglePenalite.get_penalite_applicable('batterie_seule', heure_actuelle)
            if montant <= 0:
                continue

            _, created = Penalite.objects.get_or_create(
                contrat_batterie=contrat,
                date_paiement_manque=aujourd_hui,
                defaults={
                    'contrat_reference': contrat.reference,
                    'type_penalite': 'batterie_seule',
                    'montant': montant,
                    'motif': motif,
                    'description': f"Pénalité automatique pour retard du {aujourd_hui.strftime('%d/%m/%Y')}",
                    'statut': 'en_attente',
                    'cree_par': user,
                }
            )
            if created:
                penalites_creees += 1

    messages.success(request, f"{penalites_creees} pénalité(s) créées pour aujourd’hui.")
    return redirect('payments:gestion_penalites')


# Fonction auxiliaire pour vérifier si une date est un jour de paiement pour un contrat
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

    # Vérifier si la personne est en congé à cette date
    if hasattr(contrat, 'conges') and contrat.conges.filter(
            date_debut__lte=date_ref,
            date_fin__gte=date_ref,
            statut__in=['planifie', 'en_cours']
    ).exists():
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


# payments/views.py

from django.shortcuts import render
from .models import Paiement
from django.db.models import Q


def recherche_avancee(request):
    paiements = Paiement.objects.all().order_by('-date_enregistrement')

    # Récupération des filtres de la requête GET
    type_contrat = request.GET.get('type_contrat')
    statut_paiement = request.GET.get('statut_paiement')
    methode_paiement = request.GET.get('methode_paiement')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    reference = request.GET.get('reference')

    # Application des filtres dynamiques
    if type_contrat:
        paiements = paiements.filter(type_contrat=type_contrat)
    if statut_paiement:
        paiements = paiements.filter(statut_paiement=statut_paiement)
    if methode_paiement:
        paiements = paiements.filter(methode_paiement=methode_paiement)
    if date_debut:
        paiements = paiements.filter(date_paiement__gte=date_debut)
    if date_fin:
        paiements = paiements.filter(date_paiement__lte=date_fin)
    if reference:
        paiements = paiements.filter(reference__icontains=reference)

    context = {
        'paiements': paiements,
        'type_contrat': type_contrat,
        'statut_paiement': statut_paiement,
        'methode_paiement': methode_paiement,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'reference': reference,
    }
    return render(request, 'payments/recherche_avancee.html', context)


from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from payments.models import Paiement


def details_paiement(request, paiement_id):
    paiement = get_object_or_404(Paiement, id=paiement_id)

    # Identifier le client concerné
    client = None
    contrat = None

    if paiement.contrat_chauffeur:
        client = paiement.contrat_chauffeur.chauffeur
        contrat = paiement.contrat_chauffeur
    elif paiement.contrat_partenaire:
        client = paiement.contrat_partenaire.partenaire
        contrat = paiement.contrat_partenaire
    elif paiement.contrat_batterie:
        contrat = paiement.contrat_batterie
        if contrat.chauffeur:
            client = contrat.chauffeur
        elif contrat.partenaire:
            client = contrat.partenaire

    context = {
        'titre': f"Détails du paiement {paiement.reference}",
        'paiement': paiement,
        'client': client,
        'contrat': contrat,
    }
    return render(request, 'payments/details_paiement.html', context)


# Dans payments/views.py

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from datetime import date
from contrats.models import CongesChauffeur


@require_GET
def verifier_conge_api(request):
    """API pour vérifier si un chauffeur est en congé à une date donnée"""
    chauffeur_id = request.GET.get('chauffeur_id')
    date_str = request.GET.get('date')

    if not chauffeur_id:
        return JsonResponse({'error': 'chauffeur_id est requis'}, status=400)

    try:
        chauffeur = Chauffeur.objects.get(id=chauffeur_id)
    except Chauffeur.DoesNotExist:
        return JsonResponse({'error': 'Chauffeur non trouvé'}, status=404)

    # Date à vérifier (aujourd'hui par défaut)
    date_verif = date.today()
    if date_str:
        try:
            date_verif = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Format de date invalide. Utilisez YYYY-MM-DD'}, status=400)

    # Vérifier les congés
    conges = CongesChauffeur.objects.filter(
        contrat__chauffeur=chauffeur,
        date_debut__lte=date_verif,
        date_fin__gte=date_verif,
        statut__in=['approuvé', 'planifié', 'en_cours']
    )

    est_en_conge = conges.exists()

    # Préparer la réponse
    response = {
        'chauffeur_id': chauffeur.id,
        'chauffeur_nom': f"{chauffeur.prenom} {chauffeur.nom}",
        'date': date_verif.strftime('%Y-%m-%d'),
        'est_en_conge': est_en_conge,
    }

    # Ajouter les détails du congé si disponible
    if est_en_conge:
        conge = conges.first()
        response['conge'] = {
            'id': conge.id,
            'date_debut': conge.date_debut.strftime('%Y-%m-%d'),
            'date_fin': conge.date_fin.strftime('%Y-%m-%d'),
            'nombre_jours': conge.nombre_jours,
            'statut': conge.get_statut_display(),
        }

    return JsonResponse(response)