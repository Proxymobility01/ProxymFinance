# dashboard/views.py

from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal
import json

# Imports des modèles
from authentication.models import Employe, Agence
from contrats.models import (
    ValidatedUser, ContratChauffeur, ContratPartenaire,
    ContratBatterie, CongesChauffeur, Partenaire
)
from payments.models import Paiement, Penalite, Swap
from stations.models import StationCharge, RentabilityAnalysis


class DashboardView(View):
    """
    Vue pour le tableau de bord principal.
    """
    template_name = 'dashboard/index.html'

    def get(self, request):
        # Vérifier si l'utilisateur est connecté
        if 'user_id' not in request.session:
            return redirect('authentication:login')

        # Récupérer les informations de l'utilisateur connecté
        user_id = request.session.get('user_id')
        user_name = request.session.get('user_name')
        user_type = request.session.get('user_type')
        user_role = request.session.get('user_role', '')

        # Rediriger vers le dashboard spécialisé selon le rôle
        if user_role == 'Gestionnaire de Station':
            return redirect('dashboard:station')
        elif user_role == 'Gestionnaire des Opérations':
            return redirect('dashboard:operations')
        elif user_role == 'Responsable des Leases':
            return redirect('dashboard:leases')
        elif user_role == 'Manager Financier':
            return redirect('dashboard:admin')

        # Dashboard général par défaut
        context = self._get_general_dashboard_data(request)
        return render(request, self.template_name, context)

    def _get_general_dashboard_data(self, request):
        """Données pour le dashboard général"""
        today = date.today()

        # Statistiques générales
        total_contrats = ContratChauffeur.objects.count() + ContratPartenaire.objects.count()
        contrats_actifs = ContratChauffeur.objects.filter(statut='actif').count() + ContratPartenaire.objects.filter(
            statut='actif').count()

        # Paiements du jour
        paiements_jour = Paiement.objects.filter(date_paiement=today)
        montant_jour = paiements_jour.aggregate(total=Sum('montant_total'))['total'] or 0

        # Pénalités actives
        penalites_actives = Penalite.objects.filter(statut='en_attente').count()

        return {
            'user_name': request.session.get('user_name'),
            'user_type': request.session.get('user_type'),
            'user_role': request.session.get('user_role'),
            'page_title': 'Tableau de bord général',
            'total_contrats': total_contrats,
            'contrats_actifs': contrats_actifs,
            'montant_jour': montant_jour,
            'penalites_actives': penalites_actives,
        }


class StationDashboardView(View):
    """
    Dashboard pour les Gestionnaires de Station
    """
    template_name = 'dashboard/station.html'

    def get(self, request):
        if not self._check_role(request, 'Gestionnaire de Station'):
            return redirect('authentication:login')

        context = self._get_station_dashboard_data(request)
        return render(request, self.template_name, context)

    def _check_role(self, request, required_role):
        """Vérifier si l'utilisateur a le rôle requis"""
        if 'user_id' not in request.session:
            return False

        user_role = request.session.get('user_role', '')
        if user_role != required_role:
            messages.error(request, f"Accès réservé aux {required_role}s.")
            return False

        return True

    def _get_station_dashboard_data(self, request):
        """Données spécifiques au dashboard station"""
        today = date.today()
        start_month = today.replace(day=1)
        start_week = today - timedelta(days=today.weekday())

        # Statistiques des swaps aujourd'hui
        swaps_today = Swap.objects.filter(swap_date__date=today)
        revenus_jour = swaps_today.aggregate(total=Sum('swap_price'))['total'] or 0
        nb_swaps_jour = swaps_today.count()

        # Statistiques de la semaine
        swaps_semaine = Swap.objects.filter(swap_date__date__gte=start_week)
        revenus_semaine = swaps_semaine.aggregate(total=Sum('swap_price'))['total'] or 0
        nb_swaps_semaine = swaps_semaine.count()

        # Statistiques du mois
        swaps_mois = Swap.objects.filter(swap_date__date__gte=start_month)
        revenus_mois = swaps_mois.aggregate(total=Sum('swap_price'))['total'] or 0
        nb_swaps_mois = swaps_mois.count()

        # Charges du mois
        charges_mois = StationCharge.objects.filter(
            date_charge__gte=start_month
        ).aggregate(total=Sum('montant'))['total'] or 0

        # Top 5 stations par revenus du mois
        top_stations = Agence.objects.annotate(
            revenus_mois=Sum('swaps__swap_price',
                             filter=Q(swaps__swap_date__date__gte=start_month))
        ).order_by('-revenus_mois')[:5]

        # Évolution des revenus sur 7 jours
        evolution_7j = []
        for i in range(7):
            jour = today - timedelta(days=6 - i)
            revenus = Swap.objects.filter(
                swap_date__date=jour
            ).aggregate(total=Sum('swap_price'))['total'] or 0

            evolution_7j.append({
                'date': jour.strftime('%d/%m'),
                'revenus': float(revenus)
            })

        # Répartition des swaps par station (aujourd'hui)
        swaps_par_station = Swap.objects.filter(
            swap_date__date=today
        ).values('id_agence').annotate(
            count=Count('id'),
            revenus=Sum('swap_price')
        ).order_by('-count')[:10]

        return {
            'user_name': request.session.get('user_name'),
            'user_role': request.session.get('user_role'),
            'page_title': 'Dashboard Station',

            # Métriques principales
            'revenus_jour': revenus_jour,
            'nb_swaps_jour': nb_swaps_jour,
            'revenus_semaine': revenus_semaine,
            'nb_swaps_semaine': nb_swaps_semaine,
            'revenus_mois': revenus_mois,
            'nb_swaps_mois': nb_swaps_mois,
            'charges_mois': charges_mois,
            'profit_mois': revenus_mois - charges_mois,

            # Moyennes
            'moyenne_swap': revenus_jour / nb_swaps_jour if nb_swaps_jour > 0 else 0,
            'moyenne_jour_mois': revenus_mois / today.day if today.day > 0 else 0,

            # Listes et graphiques
            'top_stations': top_stations,
            'evolution_7j_json': json.dumps(evolution_7j),
            'swaps_par_station': swaps_par_station,

            # Alertes
            'stations_sans_activite': self._get_stations_inactives(),
        }

    def _get_stations_inactives(self):
        """Stations sans activité depuis 24h"""
        yesterday = date.today() - timedelta(days=1)
        stations_actives = Swap.objects.filter(
            swap_date__date__gte=yesterday
        ).values_list('id_agence', flat=True).distinct()

        return Agence.objects.exclude(id__in=stations_actives)


class OperationsDashboardView(View):
    """
    Dashboard pour les Gestionnaires des Opérations
    """
    template_name = 'dashboard/operations.html'

    def get(self, request):
        if not self._check_role(request, 'Gestionnaire des Opérations'):
            return redirect('authentication:login')

        context = self._get_operations_dashboard_data(request)
        return render(request, self.template_name, context)

    def _check_role(self, request, required_role):
        if 'user_id' not in request.session:
            return False

        user_role = request.session.get('user_role', '')
        if user_role != required_role:
            messages.error(request, f"Accès réservé aux {required_role}s.")
            return False

        return True

    def _get_operations_dashboard_data(self, request):
        """Données spécifiques au dashboard opérations"""
        today = date.today()
        start_month = today.replace(day=1)

        # Statistiques des paiements
        paiements_jour = Paiement.objects.filter(date_paiement=today)
        montant_paiements_jour = paiements_jour.aggregate(total=Sum('montant_total'))['total'] or 0
        nb_paiements_jour = paiements_jour.count()

        paiements_mois = Paiement.objects.filter(date_paiement__gte=start_month)
        montant_paiements_mois = paiements_mois.aggregate(total=Sum('montant_total'))['total'] or 0

        # Statistiques des pénalités
        penalites_actives = Penalite.objects.filter(statut='en_attente')
        nb_penalites_actives = penalites_actives.count()
        montant_penalites_actives = penalites_actives.aggregate(total=Sum('montant'))['total'] or 0

        penalites_mois = Penalite.objects.filter(
            date_creation__date__gte=start_month
        )
        nb_penalites_mois = penalites_mois.count()

        # Taux de recouvrement
        paiements_penalites_mois = Paiement.objects.filter(
            date_paiement__gte=start_month,
            est_penalite=True
        ).aggregate(total=Sum('montant_total'))['total'] or 0

        taux_recouvrement = (
                    paiements_penalites_mois / montant_penalites_actives * 100) if montant_penalites_actives > 0 else 0

        # Contrats en retard
        contrats_retard = self._get_contrats_en_retard()

        # Top clients par paiements
        top_payeurs = self._get_top_payeurs_mois(start_month)

        # Évolution des paiements sur 30 jours
        evolution_paiements = []
        for i in range(30):
            jour = today - timedelta(days=29 - i)
            montant = Paiement.objects.filter(
                date_paiement=jour
            ).aggregate(total=Sum('montant_total'))['total'] or 0

            evolution_paiements.append({
                'date': jour.strftime('%d/%m'),
                'montant': float(montant)
            })

        # Répartition par méthode de paiement
        methodes_paiement = paiements_mois.values('methode_paiement').annotate(
            count=Count('id'),
            montant=Sum('montant_total')
        ).order_by('-montant')

        return {
            'user_name': request.session.get('user_name'),
            'user_role': request.session.get('user_role'),
            'page_title': 'Dashboard Opérations',

            # Métriques paiements
            'montant_paiements_jour': montant_paiements_jour,
            'nb_paiements_jour': nb_paiements_jour,
            'montant_paiements_mois': montant_paiements_mois,
            'moyenne_paiement': montant_paiements_jour / nb_paiements_jour if nb_paiements_jour > 0 else 0,

            # Métriques pénalités
            'nb_penalites_actives': nb_penalites_actives,
            'montant_penalites_actives': montant_penalites_actives,
            'nb_penalites_mois': nb_penalites_mois,
            'taux_recouvrement': round(taux_recouvrement, 2),

            # Listes et analyses
            'contrats_retard': contrats_retard,
            'top_payeurs': top_payeurs,
            'evolution_paiements_json': json.dumps(evolution_paiements),
            'methodes_paiement': methodes_paiement,

            # Alertes
            'paiements_en_retard': len(contrats_retard),
            'penalites_importantes': penalites_actives.filter(montant__gte=10000).count(),
        }

    def _get_contrats_en_retard(self):
        """Contrats avec paiements en retard"""
        today = date.today()
        retards = []

        # Vérifier les contrats chauffeur
        for contrat in ContratChauffeur.objects.filter(statut='actif'):
            dernier_paiement = Paiement.objects.filter(
                contrat_chauffeur=contrat
            ).order_by('-date_paiement').first()

            if dernier_paiement:
                jours_retard = (today - dernier_paiement.date_paiement).days
                if jours_retard > 2:  # Plus de 2 jours de retard
                    retards.append({
                        'type': 'chauffeur',
                        'contrat': contrat,
                        'client': contrat.association.validated_user,
                        'jours_retard': jours_retard,
                        'montant_du': contrat.montant_par_paiement
                    })

        return retards[:10]  # Limiter à 10 résultats

    def _get_top_payeurs_mois(self, start_month):
        """Top payeurs du mois"""
        # Agrégation par client (chauffeur)
        top_chauffeurs = Paiement.objects.filter(
            date_paiement__gte=start_month,
            contrat_chauffeur__isnull=False
        ).values(
            'contrat_chauffeur__association__validated_user__nom',
            'contrat_chauffeur__association__validated_user__prenom'
        ).annotate(
            total_paye=Sum('montant_total'),
            nb_paiements=Count('id')
        ).order_by('-total_paye')[:5]

        return top_chauffeurs


class LeasesDashboardView(View):
    """
    Dashboard pour les Responsables des Leases
    """
    template_name = 'dashboard/leases.html'

    def get(self, request):
        if not self._check_role(request, 'Responsable des Leases'):
            return redirect('authentication:login')

        context = self._get_leases_dashboard_data(request)
        return render(request, self.template_name, context)

    def _check_role(self, request, required_role):
        if 'user_id' not in request.session:
            return False

        user_role = request.session.get('user_role', '')
        if user_role != required_role:
            messages.error(request, f"Accès réservé aux {required_role}s.")
            return False

        return True

    def _get_leases_dashboard_data(self, request):
        """Données spécifiques au dashboard leases"""
        today = date.today()
        start_month = today.replace(day=1)

        # Statistiques des contrats
        total_contrats_chauffeur = ContratChauffeur.objects.count()
        total_contrats_partenaire = ContratPartenaire.objects.count()
        total_contrats_batterie = ContratBatterie.objects.count()

        contrats_actifs_chauffeur = ContratChauffeur.objects.filter(statut='actif').count()
        contrats_actifs_partenaire = ContratPartenaire.objects.filter(statut='actif').count()
        contrats_actifs_batterie = ContratBatterie.objects.filter(statut='actif').count()

        # Nouveaux contrats ce mois
        nouveaux_contrats_mois = ContratChauffeur.objects.filter(
            date_signature__gte=start_month
        ).count() + ContratPartenaire.objects.filter(
            date_signature__gte=start_month
        ).count()

        # Contrats arrivant à échéance (30 prochains jours)
        fin_proche = today + timedelta(days=30)
        contrats_echeance = ContratChauffeur.objects.filter(
            date_fin__lte=fin_proche,
            date_fin__gte=today,
            statut='actif'
        ).count() + ContratPartenaire.objects.filter(
            date_fin__lte=fin_proche,
            date_fin__gte=today,
            statut='actif'
        ).count()

        # Revenus contractuels
        revenus_previsionnels = self._calculate_revenus_previsionnels()
        revenus_realises_mois = Paiement.objects.filter(
            date_paiement__gte=start_month,
            est_penalite=False
        ).aggregate(total=Sum('montant_total'))['total'] or 0

        # Taux de réalisation
        taux_realisation = (revenus_realises_mois / revenus_previsionnels * 100) if revenus_previsionnels > 0 else 0

        # Évolution des nouveaux contrats
        evolution_contrats = []
        for i in range(12):
            mois = today.replace(day=1) - timedelta(days=30 * i)
            nb_contrats = ContratChauffeur.objects.filter(
                date_signature__year=mois.year,
                date_signature__month=mois.month
            ).count() + ContratPartenaire.objects.filter(
                date_signature__year=mois.year,
                date_signature__month=mois.month
            ).count()

            evolution_contrats.append({
                'mois': mois.strftime('%m/%Y'),
                'nb_contrats': nb_contrats
            })

        evolution_contrats.reverse()

        # Top partenaires par nombre de contrats
        top_partenaires = Partenaire.objects.annotate(
            nb_contrats=Count('contrats')
        ).order_by('-nb_contrats')[:5]

        # Congés en cours et à venir
        conges_cours = CongesChauffeur.objects.filter(
            date_debut__lte=today,
            date_fin__gte=today,
            statut__in=['approuvé', 'en_cours']
        ).count()

        conges_a_venir = CongesChauffeur.objects.filter(
            date_debut__gt=today,
            date_debut__lte=today + timedelta(days=7),
            statut='approuvé'
        ).count()

        return {
            'user_name': request.session.get('user_name'),
            'user_role': request.session.get('user_role'),
            'page_title': 'Dashboard Leases',

            # Statistiques générales
            'total_contrats_chauffeur': total_contrats_chauffeur,
            'total_contrats_partenaire': total_contrats_partenaire,
            'total_contrats_batterie': total_contrats_batterie,
            'contrats_actifs_total': contrats_actifs_chauffeur + contrats_actifs_partenaire,
            'nouveaux_contrats_mois': nouveaux_contrats_mois,
            'contrats_echeance': contrats_echeance,

            # Revenus et performance
            'revenus_previsionnels': revenus_previsionnels,
            'revenus_realises_mois': revenus_realises_mois,
            'taux_realisation': round(taux_realisation, 2),

            # Analyses
            'evolution_contrats_json': json.dumps(evolution_contrats),
            'top_partenaires': top_partenaires,

            # Congés
            'conges_cours': conges_cours,
            'conges_a_venir': conges_a_venir,

            # Répartition
            'repartition_contrats': {
                'chauffeur': contrats_actifs_chauffeur,
                'partenaire': contrats_actifs_partenaire,
                'batterie': contrats_actifs_batterie
            }
        }

    def _calculate_revenus_previsionnels(self):
        """Calcul des revenus prévisionnels du mois"""
        today = date.today()
        start_month = today.replace(day=1)

        # Jours ouvrables du mois (lundi à samedi)
        jours_ouvrables = 0
        current_date = start_month

        while current_date.month == today.month:
            if current_date.weekday() < 6:  # Lundi (0) à Samedi (5)
                jours_ouvrables += 1
            current_date += timedelta(days=1)

        # Revenus des contrats journaliers
        contrats_journaliers = ContratChauffeur.objects.filter(
            statut='actif',
            frequence_paiement='journalier'
        ).aggregate(total=Sum('montant_par_paiement'))['total'] or 0

        contrats_journaliers += ContratPartenaire.objects.filter(
            statut='actif',
            frequence_paiement='journalier'
        ).aggregate(total=Sum('montant_par_paiement'))['total'] or 0

        return contrats_journaliers * jours_ouvrables


class AdminDashboardView(View):
    """
    Dashboard pour les Managers Financiers
    """
    template_name = 'dashboard/admin.html'

    def get(self, request):
        if not self._check_role(request, 'Manager Financier'):
            return redirect('authentication:login')

        context = self._get_admin_dashboard_data(request)
        return render(request, self.template_name, context)

    def _check_role(self, request, required_role):
        if 'user_id' not in request.session:
            return False

        user_role = request.session.get('user_role', '')
        if user_role != required_role:
            messages.error(request, f"Accès réservé aux {required_role}s.")
            return False

        return True

    def _get_admin_dashboard_data(self, request):
        """Données pour le dashboard administratif global"""
        today = date.today()
        start_month = today.replace(day=1)
        start_quarter = self._get_quarter_start(today)
        start_year = today.replace(month=1, day=1)

        # KPIs financiers globaux
        # Revenus
        revenus_jour = self._get_revenus_periode(today, today)
        revenus_mois = self._get_revenus_periode(start_month, today)
        revenus_trimestre = self._get_revenus_periode(start_quarter, today)
        revenus_annee = self._get_revenus_periode(start_year, today)

        # Charges
        charges_mois = StationCharge.objects.filter(
            date_charge__gte=start_month
        ).aggregate(total=Sum('montant'))['total'] or 0

        charges_trimestre = StationCharge.objects.filter(
            date_charge__gte=start_quarter
        ).aggregate(total=Sum('montant'))['total'] or 0

        # Profits
        profit_mois = revenus_mois - charges_mois
        profit_trimestre = revenus_trimestre - charges_trimestre
        marge_mois = (profit_mois / revenus_mois * 100) if revenus_mois > 0 else 0

        # Croissance par rapport au mois précédent
        mois_precedent_debut = (start_month - timedelta(days=1)).replace(day=1)
        mois_precedent_fin = start_month - timedelta(days=1)
        revenus_mois_precedent = self._get_revenus_periode(mois_precedent_debut, mois_precedent_fin)

        croissance_mois = ((
                                       revenus_mois - revenus_mois_precedent) / revenus_mois_precedent * 100) if revenus_mois_precedent > 0 else 0

        # Métriques opérationnelles
        total_transactions = Paiement.objects.filter(date_paiement__gte=start_month).count()
        total_swaps = Swap.objects.filter(swap_date__date__gte=start_month).count()
        stations_actives = Agence.objects.filter(
            swaps__swap_date__date__gte=start_month
        ).distinct().count()

        # Évolution mensuelle des revenus (12 derniers mois)
        evolution_mensuelle = []
        for i in range(12):
            mois = start_month - timedelta(days=30 * i)
            mois_debut = mois.replace(day=1)

            if mois.month == 12:
                mois_fin = mois.replace(year=mois.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                mois_fin = mois.replace(month=mois.month + 1, day=1) - timedelta(days=1)

            revenus = self._get_revenus_periode(mois_debut, mois_fin)

            evolution_mensuelle.append({
                'mois': mois.strftime('%m/%Y'),
                'revenus': float(revenus)
            })

        evolution_mensuelle.reverse()

        # Top métriques par station
        top_stations_revenus = Agence.objects.annotate(
            revenus_mois=Sum('swaps__swap_price',
                             filter=Q(swaps__swap_date__date__gte=start_month))
        ).order_by('-revenus_mois')[:5]

        # Analyse des pénalités
        penalites_mois = Penalite.objects.filter(
            date_creation__date__gte=start_month
        )

        total_penalites = penalites_mois.aggregate(total=Sum('montant'))['total'] or 0
        penalites_payees = penalites_mois.filter(statut='payee').aggregate(total=Sum('montant'))['total'] or 0
        taux_recouvrement_penalites = (penalites_payees / total_penalites * 100) if total_penalites > 0 else 0

        # Alertes et indicateurs
        alertes = self._get_alertes_admin()

        return {
            'user_name': request.session.get('user_name'),
            'user_role': request.session.get('user_role'),
            'page_title': 'Dashboard Financier',

            # KPIs principaux
            'revenus_jour': revenus_jour,
            'revenus_mois': revenus_mois,
            'revenus_trimestre': revenus_trimestre,
            'revenus_annee': revenus_annee,
            'charges_mois': charges_mois,
            'profit_mois': profit_mois,
            'marge_mois': round(marge_mois, 2),
            'croissance_mois': round(croissance_mois, 2),

            # Métriques opérationnelles
            'total_transactions': total_transactions,
            'total_swaps': total_swaps,
            'stations_actives': stations_actives,
            'ticket_moyen': revenus_mois / total_swaps if total_swaps > 0 else 0,

            # Analyses
            'evolution_mensuelle_json': json.dumps(evolution_mensuelle),
            'top_stations_revenus': top_stations_revenus,

            # Pénalités
            'total_penalites': total_penalites,
            'penalites_payees': penalites_payees,
            'taux_recouvrement_penalites': round(taux_recouvrement_penalites, 2),

            # Alertes
            'alertes': alertes,
            'nb_alertes': len(alertes),
        }

    def _get_quarter_start(self, date):
        """Obtenir le début du trimestre"""
        quarter = (date.month - 1) // 3 + 1
        return date.replace(month=(quarter - 1) * 3 + 1, day=1)

    def _get_revenus_periode(self, date_debut, date_fin):
        """Calculer les revenus sur une période"""
        # Revenus des swaps
        revenus_swaps = Swap.objects.filter(
            swap_date__date__gte=date_debut,
            swap_date__date__lte=date_fin
        ).aggregate(total=Sum('swap_price'))['total'] or 0

        # Revenus des paiements de contrats
        revenus_contrats = Paiement.objects.filter(
            date_paiement__gte=date_debut,
            date_paiement__lte=date_fin,
            est_penalite=False
        ).aggregate(total=Sum('montant_total'))['total'] or 0

        return revenus_swaps + revenus_contrats

    def _get_alertes_admin(self):
        """Générer les alertes pour le dashboard admin"""
        alertes = []
        today = date.today()

        # Alerte stations inactives
        stations_inactives = Agence.objects.exclude(
            swaps__swap_date__date__gte=today - timedelta(days=2)
        ).count()

        if stations_inactives > 0:
            alertes.append({
                'type': 'warning',
                'titre': 'Stations inactives',
                'message': f'{stations_inactives} station(s) sans activité depuis 48h',
                'action_url': '/stations/',
                'priorite': 'moyenne'
            })

        # Alerte pénalités importantes
        penalites_importantes = Penalite.objects.filter(
            statut='en_attente',
            montant__gte=20000
        ).count()

        if penalites_importantes > 0:
            alertes.append({
                'type': 'danger',
                'titre': 'Pénalités importantes',
                'message': f'{penalites_importantes} pénalité(s) de plus de 20 000 FCFA en attente',
                'action_url': '/payments/penalites/',
                'priorite': 'haute'
            })

        # Alerte contrats arrivant à échéance
        contrats_echeance = ContratChauffeur.objects.filter(
            date_fin__lte=today + timedelta(days=7),
            date_fin__gte=today,
            statut='actif'
        ).count()

        if contrats_echeance > 0:
            alertes.append({
                'type': 'info',
                'titre': 'Contrats en fin de période',
                'message': f'{contrats_echeance} contrat(s) arrivent à échéance cette semaine',
                'action_url': '/contrats/',
                'priorite': 'basse'
            })

        # Alerte baisse de revenus
        start_month = today.replace(day=1)
        revenus_mois = self._get_revenus_periode(start_month, today)

        # Revenus mois précédent
        mois_precedent_debut = (start_month - timedelta(days=1)).replace(day=1)
        mois_precedent_fin = start_month - timedelta(days=1)
        revenus_mois_precedent = self._get_revenus_periode(mois_precedent_debut, mois_precedent_fin)

        if revenus_mois_precedent > 0:
            baisse_revenus = ((revenus_mois_precedent - revenus_mois) / revenus_mois_precedent * 100)
            if baisse_revenus > 10:  # Baisse de plus de 10%
                alertes.append({
                    'type': 'warning',
                    'titre': 'Baisse de revenus',
                    'message': f'Revenus en baisse de {baisse_revenus:.1f}% par rapport au mois précédent',
                    'action_url': '/dashboard/admin/',
                    'priorite': 'moyenne'
                })

        return sorted(alertes, key=lambda x: {'haute': 3, 'moyenne': 2, 'basse': 1}[x['priorite']], reverse=True)