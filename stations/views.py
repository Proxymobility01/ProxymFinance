## views.py - Version étendue avec analytiques

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models import ChargeCategory, StationCharge, RentabilityAnalysis, Swap
from .forms import (
    ChargeCategoryForm,
    StationChargeForm,
    RentabilityAnalysisForm,
    PeriodFilterForm,
    QuickAnalysisForm
)
from authentication.models import Agence
from django.contrib.auth.decorators import login_required


# ===== VUES EXISTANTES (inchangées) =====
@login_required
def charge_category_list(request):
    categories = ChargeCategory.objects.order_by('code')
    return render(request, 'stations/chargecategory_list.html', {'categories': categories})


@login_required
def charge_category_create(request):
    if request.method == 'POST':
        form = ChargeCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Catégorie de charge ajoutée avec succès.")
            return redirect('stations:charge_category_list')
    else:
        form = ChargeCategoryForm()
    return render(request, 'stations/chargecategory_form.html', {'form': form})


@login_required
def charge_category_update(request, pk):
    category = get_object_or_404(ChargeCategory, pk=pk)
    if request.method == 'POST':
        form = ChargeCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Catégorie de charge modifiée avec succès.")
            return redirect('stations:charge_category_list')
    else:
        form = ChargeCategoryForm(instance=category)
    return render(request, 'stations/chargecategory_form.html', {'form': form, 'category': category})


@login_required
def charge_category_delete(request, pk):
    category = get_object_or_404(ChargeCategory, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, "Catégorie de charge supprimée.")
        return redirect('stations:charge_category_list')
    return render(request, 'stations/chargecategory_confirm_delete.html', {'category': category})


@login_required
def station_charge_list(request, station_id=None):
    if station_id:
        station = get_object_or_404(Agence, pk=station_id)
        charges = StationCharge.objects.filter(station=station).order_by('-date_charge')
        total_montant = sum(charge.montant for charge in charges)
    else:
        station = None
        charges = StationCharge.objects.select_related('station', 'categorie').order_by('-date_charge')
        total_montant = sum(charge.montant for charge in charges)

    return render(request, 'stations/stationcharge_list.html', {
        'charges': charges,
        'station': station,
        'total_montant': total_montant
    })


@login_required
def station_charge_create(request):
    if request.method == 'POST':
        form = StationChargeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Charge enregistrée avec succès.")
            return redirect('stations:station_charge_list')
    else:
        form = StationChargeForm()
    return render(request, 'stations/stationcharge_form.html', {'form': form})


@login_required
def station_charge_update(request, pk):
    charge = get_object_or_404(StationCharge, pk=pk)
    if request.method == 'POST':
        form = StationChargeForm(request.POST, instance=charge)
        if form.is_valid():
            form.save()
            messages.success(request, "Charge modifiée avec succès.")
            return redirect('stations:station_charge_list')
    else:
        form = StationChargeForm(instance=charge)
    return render(request, 'stations/stationcharge_form.html', {'form': form, 'charge': charge})


@login_required
def station_charge_delete(request, pk):
    charge = get_object_or_404(StationCharge, pk=pk)
    if request.method == 'POST':
        charge.delete()
        messages.success(request, "Charge supprimée.")
        return redirect('stations:station_charge_list')
    return render(request, 'stations/stationcharge_confirm_delete.html', {'charge': charge})


# ===== NOUVELLES VUES POUR LA RENTABILITÉ =====

@login_required
def dashboard_rentability(request):
    """Vue principale du dashboard de rentabilité"""
    # Statistiques générales
    total_stations = Agence.objects.count()

    # Données pour le mois en cours
    today = timezone.now().date()
    start_month = today.replace(day=1)

    current_month_revenue = Swap.objects.filter(
        swap_date__date__gte=start_month,
        swap_price__isnull=False
    ).aggregate(total=Sum('swap_price'))['total'] or 0

    current_month_charges = StationCharge.objects.filter(
        date_charge__gte=start_month
    ).aggregate(total=Sum('montant'))['total'] or 0

    current_month_profit = current_month_revenue - current_month_charges
    current_month_swaps = Swap.objects.filter(swap_date__date__gte=start_month).count()

    # Top 5 stations par revenus du mois
    top_stations = Agence.objects.annotate(
        monthly_revenue=Sum('swaps__swap_price',
                            filter=Q(swaps__swap_date__date__gte=start_month))
    ).order_by('-monthly_revenue')[:5]

    context = {
        'total_stations': total_stations,
        'current_month_revenue': current_month_revenue,
        'current_month_charges': current_month_charges,
        'current_month_profit': current_month_profit,
        'current_month_swaps': current_month_swaps,
        'top_stations': top_stations,
        'current_month': start_month.strftime('%B %Y'),
    }

    return render(request, 'stations/dashboard_rentability.html', context)


@login_required
def station_detail(request, station_id):
    """Vue détaillée d'une station avec analytiques"""
    station = get_object_or_404(Agence, pk=station_id)

    # Formulaire de filtre par période
    filter_form = PeriodFilterForm(request.GET or None)

    # Dates par défaut (mois en cours)
    today = timezone.now().date()
    start_date = today.replace(day=1)
    end_date = today

    if filter_form.is_valid():
        date_range = filter_form.get_date_range()
        if date_range[0] and date_range[1]:
            start_date, end_date = date_range

    # Calculs pour la période sélectionnée
    swaps_period = Swap.objects.filter(
        agence=station,
        swap_date__date__gte=start_date,
        swap_date__date__lte=end_date
    )

    charges_period = StationCharge.objects.filter(
        station=station,
        date_charge__gte=start_date,
        date_charge__lte=end_date
    )

    # Métriques clés
    revenue = swaps_period.aggregate(total=Sum('swap_price'))['total'] or 0
    total_charges = charges_period.aggregate(total=Sum('montant'))['total'] or 0
    profit = revenue - total_charges
    swap_count = swaps_period.count()
    avg_swap_price = swaps_period.aggregate(avg=Avg('swap_price'))['avg'] or 0

    # Évolution quotidienne (derniers 30 jours)
    daily_data = []
    for i in range(30):
        date = today - timedelta(days=i)
        daily_revenue = Swap.objects.filter(
            agence=station,
            swap_date__date=date
        ).aggregate(total=Sum('swap_price'))['total'] or 0

        daily_charges = StationCharge.objects.filter(
            station=station,
            date_charge=date
        ).aggregate(total=Sum('montant'))['total'] or 0

        daily_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'revenue': float(daily_revenue),
            'charges': float(daily_charges),
            'profit': float(daily_revenue - daily_charges)
        })

    daily_data.reverse()  # Ordre chronologique

    # Répartition des charges par catégorie
    charges_by_category = charges_period.values('categorie__nom').annotate(
        total=Sum('montant')
    ).order_by('-total')

    # Dernières transactions
    recent_swaps = swaps_period.order_by('-swap_date')[:10]
    recent_charges = charges_period.order_by('-date_charge')[:10]

    context = {
        'station': station,
        'filter_form': filter_form,
        'start_date': start_date,
        'end_date': end_date,
        'revenue': revenue,
        'total_charges': total_charges,
        'profit': profit,
        'swap_count': swap_count,
        'avg_swap_price': avg_swap_price,
        'profit_margin': (profit / revenue * 100) if revenue > 0 else 0,
        'daily_data_json': json.dumps(daily_data),
        'charges_by_category': charges_by_category,
        'recent_swaps': recent_swaps,
        'recent_charges': recent_charges,
    }

    return render(request, 'stations/station_detail.html', context)


@login_required
def rentability_analysis_list(request):
    """Liste des analyses de rentabilité"""
    analyses = RentabilityAnalysis.objects.select_related('station').order_by('-created_at')

    # Filtre par station si spécifié
    station_id = request.GET.get('station')
    if station_id:
        analyses = analyses.filter(station_id=station_id)

    stations = Agence.objects.order_by('nom_agence')

    context = {
        'analyses': analyses,
        'stations': stations,
        'selected_station': station_id,
    }

    return render(request, 'stations/rentability_analysis_list.html', context)


@login_required
def rentability_analysis_create(request):
    """Créer une nouvelle analyse de rentabilité"""
    if request.method == 'POST':
        form = RentabilityAnalysisForm(request.POST)
        if form.is_valid():
            analysis = form.save()
            # Calculer automatiquement les métriques
            analysis.calculate_metrics()
            messages.success(request, "Analyse de rentabilité créée avec succès.")
            return redirect('stations:rentability_analysis_detail', pk=analysis.pk)
    else:
        form = RentabilityAnalysisForm()

    return render(request, 'stations/rentability_analysis_form.html', {'form': form})


@login_required
def rentability_analysis_detail(request, pk):
    """Détail d'une analyse de rentabilité"""
    analysis = get_object_or_404(RentabilityAnalysis, pk=pk)

    # Recalculer les métriques si demandé
    if request.GET.get('recalculate'):
        analysis.calculate_metrics()
        messages.success(request, "Métriques recalculées avec succès.")
        return redirect('stations:rentability_analysis_detail', pk=pk)

    # Données détaillées pour les graphiques
    # Évolution quotidienne pendant la période
    daily_evolution = []
    current_date = analysis.date_debut

    while current_date <= analysis.date_fin:
        daily_revenue = Swap.objects.filter(
            agence=analysis.station,
            swap_date__date=current_date
        ).aggregate(total=Sum('swap_price'))['total'] or 0

        daily_charges = StationCharge.objects.filter(
            station=analysis.station,
            date_charge=current_date
        ).aggregate(total=Sum('montant'))['total'] or 0

        daily_evolution.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'revenue': float(daily_revenue),
            'charges': float(daily_charges),
            'profit': float(daily_revenue - daily_charges)
        })

        current_date += timedelta(days=1)

    # Répartition des charges par catégorie
    charges_breakdown = StationCharge.objects.filter(
        station=analysis.station,
        date_charge__gte=analysis.date_debut,
        date_charge__lte=analysis.date_fin
    ).values('categorie__nom', 'categorie__code').annotate(
        total=Sum('montant'),
        count=Count('id')
    ).order_by('-total')

    # Statistiques hebdomadaires
    weekly_stats = []
    week_start = analysis.date_debut

    while week_start <= analysis.date_fin:
        week_end = min(week_start + timedelta(days=6), analysis.date_fin)

        week_revenue = Swap.objects.filter(
            agence=analysis.station,
            swap_date__date__gte=week_start,
            swap_date__date__lte=week_end
        ).aggregate(total=Sum('swap_price'))['total'] or 0

        week_charges = StationCharge.objects.filter(
            station=analysis.station,
            date_charge__gte=week_start,
            date_charge__lte=week_end
        ).aggregate(total=Sum('montant'))['total'] or 0

        week_swaps = Swap.objects.filter(
            agence=analysis.station,
            swap_date__date__gte=week_start,
            swap_date__date__lte=week_end
        ).count()

        weekly_stats.append({
            'week_start': week_start,
            'week_end': week_end,
            'revenue': week_revenue,
            'charges': week_charges,
            'profit': week_revenue - week_charges,
            'swaps': week_swaps,
        })

        week_start += timedelta(days=7)

    context = {
        'analysis': analysis,
        'daily_evolution_json': json.dumps(daily_evolution),
        'charges_breakdown': charges_breakdown,
        'weekly_stats': weekly_stats,
        'period_days': (analysis.date_fin - analysis.date_debut).days + 1,
        'avg_daily_revenue': analysis.revenus_total / ((analysis.date_fin - analysis.date_debut).days + 1),
        'avg_daily_charges': analysis.charges_total / ((analysis.date_fin - analysis.date_debut).days + 1),
    }

    return render(request, 'stations/rentability_analysis_detail.html', context)


@login_required
def rentability_analysis_update(request, pk):
    """Modifier une analyse de rentabilité"""
    analysis = get_object_or_404(RentabilityAnalysis, pk=pk)

    if request.method == 'POST':
        form = RentabilityAnalysisForm(request.POST, instance=analysis)
        if form.is_valid():
            analysis = form.save()
            # Recalculer les métriques
            analysis.calculate_metrics()
            messages.success(request, "Analyse de rentabilité modifiée avec succès.")
            return redirect('stations:rentability_analysis_detail', pk=analysis.pk)
    else:
        form = RentabilityAnalysisForm(instance=analysis)

    return render(request, 'stations/rentability_analysis_form.html', {
        'form': form,
        'analysis': analysis
    })


@login_required
def rentability_analysis_delete(request, pk):
    """Supprimer une analyse de rentabilité"""
    analysis = get_object_or_404(RentabilityAnalysis, pk=pk)

    if request.method == 'POST':
        analysis.delete()
        messages.success(request, "Analyse de rentabilité supprimée.")
        return redirect('stations:rentability_analysis_list')

    return render(request, 'stations/rentability_analysis_confirm_delete.html', {
        'analysis': analysis
    })


@login_required
def quick_analysis(request):
    """Analyse rapide de rentabilité"""
    if request.method == 'POST':
        form = QuickAnalysisForm(request.POST)
        if form.is_valid():
            station = form.cleaned_data['station']
            periode = form.cleaned_data['periode']

            # Calculer les dates selon la période
            today = timezone.now().date()

            if periode == 'last_7_days':
                start_date = today - timedelta(days=7)
                end_date = today
            elif periode == 'last_30_days':
                start_date = today - timedelta(days=30)
                end_date = today
            elif periode == 'current_month':
                start_date = today.replace(day=1)
                end_date = today
            elif periode == 'last_month':
                if today.month == 1:
                    start_date = today.replace(year=today.year - 1, month=12, day=1)
                    end_date = today.replace(day=1) - timedelta(days=1)
                else:
                    start_date = today.replace(month=today.month - 1, day=1)
                    end_date = today.replace(day=1) - timedelta(days=1)
            elif periode == 'current_quarter':
                quarter = (today.month - 1) // 3 + 1
                start_date = today.replace(month=(quarter - 1) * 3 + 1, day=1)
                end_date = today

            # Créer une analyse temporaire
            analysis = RentabilityAnalysis(
                station=station,
                nom_analyse=f"Analyse rapide - {station.nom_agence}",
                type_periode='custom',
                date_debut=start_date,
                date_fin=end_date
            )

            # Calculer les métriques
            metrics = analysis.calculate_metrics()

            return render(request, 'stations/quick_analysis_result.html', {
                'station': station,
                'periode': periode,
                'start_date': start_date,
                'end_date': end_date,
                'metrics': metrics,
                'analysis': analysis,
            })
    else:
        form = QuickAnalysisForm()

    return render(request, 'stations/quick_analysis.html', {'form': form})


@login_required
def stations_comparison(request):
    """Comparaison de rentabilité entre stations"""
    filter_form = PeriodFilterForm(request.GET or None)

    # Dates par défaut (mois en cours)
    today = timezone.now().date()
    start_date = today.replace(day=1)
    end_date = today

    if filter_form.is_valid():
        date_range = filter_form.get_date_range()
        if date_range[0] and date_range[1]:
            start_date, end_date = date_range

    # Calculer les métriques pour chaque station
    stations_data = []
    stations = Agence.objects.all().order_by('nom_agence')

    for station in stations:
        revenue = Swap.objects.filter(
            agence=station,
            swap_date__date__gte=start_date,
            swap_date__date__lte=end_date
        ).aggregate(total=Sum('swap_price'))['total'] or 0

        charges = StationCharge.objects.filter(
            station=station,
            date_charge__gte=start_date,
            date_charge__lte=end_date
        ).aggregate(total=Sum('montant'))['total'] or 0

        swaps_count = Swap.objects.filter(
            agence=station,
            swap_date__date__gte=start_date,
            swap_date__date__lte=end_date
        ).count()

        profit = revenue - charges
        margin = (profit / revenue * 100) if revenue > 0 else 0

        stations_data.append({
            'station': station,
            'revenue': revenue,
            'charges': charges,
            'profit': profit,
            'margin': margin,
            'swaps_count': swaps_count,
            'avg_per_swap': revenue / swaps_count if swaps_count > 0 else 0,
        })

    # Trier par profit décroissant
    stations_data.sort(key=lambda x: x['profit'], reverse=True)

    context = {
        'filter_form': filter_form,
        'start_date': start_date,
        'end_date': end_date,
        'stations_data': stations_data,
        'total_revenue': sum(s['revenue'] for s in stations_data),
        'total_charges': sum(s['charges'] for s in stations_data),
        'total_profit': sum(s['profit'] for s in stations_data),
        'total_swaps': sum(s['swaps_count'] for s in stations_data),
    }

    return render(request, 'stations/stations_comparison.html', context)


# ===== API ENDPOINTS POUR LES GRAPHIQUES =====

@login_required
def api_station_evolution(request, station_id):
    """API pour l'évolution d'une station (données JSON pour graphiques)"""
    station = get_object_or_404(Agence, pk=station_id)
    days = int(request.GET.get('days', 30))

    data = []
    today = timezone.now().date()

    for i in range(days):
        date = today - timedelta(days=i)

        daily_revenue = Swap.objects.filter(
            agence=station,
            swap_date__date=date
        ).aggregate(total=Sum('swap_price'))['total'] or 0

        daily_charges = StationCharge.objects.filter(
            station=station,
            date_charge=date
        ).aggregate(total=Sum('montant'))['total'] or 0

        daily_swaps = Swap.objects.filter(
            agence=station,
            swap_date__date=date
        ).count()

        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'revenue': float(daily_revenue),
            'charges': float(daily_charges),
            'profit': float(daily_revenue - daily_charges),
            'swaps': daily_swaps,
        })

    data.reverse()  # Ordre chronologique
    return JsonResponse({'data': data})


@login_required
def api_global_stats(request):
    """API pour les statistiques globales"""
    # Période configurable
    days = int(request.GET.get('days', 30))
    today = timezone.now().date()
    start_date = today - timedelta(days=days)

    total_revenue = Swap.objects.filter(
        swap_date__date__gte=start_date
    ).aggregate(total=Sum('swap_price'))['total'] or 0

    total_charges = StationCharge.objects.filter(
        date_charge__gte=start_date
    ).aggregate(total=Sum('montant'))['total'] or 0

    total_swaps = Swap.objects.filter(
        swap_date__date__gte=start_date
    ).count()

    active_stations = Agence.objects.filter(
        swaps__swap_date__date__gte=start_date
    ).distinct().count()

    return JsonResponse({
        'total_revenue': float(total_revenue),
        'total_charges': float(total_charges),
        'total_profit': float(total_revenue - total_charges),
        'total_swaps': total_swaps,
        'active_stations': active_stations,
        'avg_revenue_per_swap': float(total_revenue / total_swaps) if total_swaps > 0 else 0,
        'profit_margin': float((total_revenue - total_charges) / total_revenue * 100) if total_revenue > 0 else 0,
    })


@login_required
def api_categories(request):
    """API pour récupérer la liste des catégories (pour le refresh des selects)"""
    categories = ChargeCategory.objects.order_by('code').values('id', 'code', 'nom')
    return JsonResponse({
        'categories': list(categories)
    })

@login_required
def station_list(request):
    """Liste des stations avec filtres et statistiques"""

    # Récupération des filtres
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')

    # Base queryset
    stations = Agence.objects.all().order_by('nom_agence')

    # Application des filtres
    if search_query:
        stations = stations.filter(
            Q(nom_agence__icontains=search_query) |
            Q(ville__icontains=search_query) |
            Q(quartier__icontains=search_query)
        )

    # Calcul des métriques pour chaque station (30 derniers jours)
    today = timezone.now().date()
    start_date = today - timedelta(days=30)

    stations_data = []
    for station in stations:
        # Revenus des 30 derniers jours
        recent_revenue = Swap.objects.filter(
            agence=station,
            swap_date__date__gte=start_date,
            swap_price__isnull=False
        ).aggregate(total=Sum('swap_price'))['total'] or 0

        # Charges des 30 derniers jours
        recent_charges = StationCharge.objects.filter(
            station=station,
            date_charge__gte=start_date
        ).aggregate(total=Sum('montant'))['total'] or 0

        # Nombre de swaps des 30 derniers jours
        recent_swaps = Swap.objects.filter(
            agence=station,
            swap_date__date__gte=start_date
        ).count()

        # Calculs dérivés
        profit = recent_revenue - recent_charges
        margin = (profit / recent_revenue * 100) if recent_revenue > 0 else 0




        stations_data.append({
            'station': station,
            'revenue': recent_revenue,
            'charges': recent_charges,
            'profit': profit,
            'margin': margin,
            'swaps_count': recent_swaps,
            'avg_per_swap': recent_revenue / recent_swaps if recent_swaps > 0 else 0,
        })

    # Statistiques globales
    total_stations = len(stations_data)
    total_revenue = sum(s['revenue'] for s in stations_data)
    total_charges = sum(s['charges'] for s in stations_data)
    total_profit = total_revenue - total_charges
    total_swaps = sum(s['swaps_count'] for s in stations_data)

    # Trier par profit décroissant
    stations_data.sort(key=lambda x: x['profit'], reverse=True)

    # Top 5 stations
    top_stations = stations_data[:5]

    # Données pour les graphiques (JSON)
    chart_data = {
        'stations': [s['station'].nom_agence for s in stations_data[:10]],
        'revenues': [float(s['revenue']) for s in stations_data[:10]],
        'charges': [float(s['charges']) for s in stations_data[:10]],
        'profits': [float(s['profit']) for s in stations_data[:10]],
    }

    context = {
        'stations_data': stations_data,
        'total_stations': total_stations,
        'total_revenue': total_revenue,
        'total_charges': total_charges,
        'total_profit': total_profit,
        'total_swaps': total_swaps,
        'top_stations': top_stations,
        'status_filter': status_filter,
        'search_query': search_query,
        'chart_data_json': json.dumps(chart_data),
        'period_days': 30,
    }

    return render(request, 'stations/station_list.html', context)

