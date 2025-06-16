from django.urls import path
from . import views

app_name = 'stations'

urlpatterns = [
    # URLs existantes pour les catégories
    path('categories/', views.charge_category_list, name='charge_category_list'),
    path('categories/add/', views.charge_category_create, name='charge_category_create'),
    path('categories/<int:pk>/edit/', views.charge_category_update, name='charge_category_update'),
    path('categories/<int:pk>/delete/', views.charge_category_delete, name='charge_category_delete'),

    # URLs existantes pour les charges
    path('charges/', views.station_charge_list, name='station_charge_list'),
    path('charges/add/', views.station_charge_create, name='station_charge_create'),
    path('charges/<int:pk>/edit/', views.station_charge_update, name='station_charge_update'),
    path('charges/<int:pk>/delete/', views.station_charge_delete, name='station_charge_delete'),
    path('station/<int:station_id>/charges/', views.station_charge_list, name='station_specific_charge_list'),

    # NOUVELLES URLs pour la rentabilité et analytiques

    # Liste des stations
    path('', views.station_list, name='station_list'),

    # Dashboard principal
    path('dashboard/', views.dashboard_rentability, name='dashboard_rentability'),

    # Détails des stations
    path('station/<int:station_id>/', views.station_detail, name='station_detail'),

    # Analyses de rentabilité
    path('analyses/', views.rentability_analysis_list, name='rentability_analysis_list'),
    path('analyses/add/', views.rentability_analysis_create, name='rentability_analysis_create'),
    path('analyses/<int:pk>/', views.rentability_analysis_detail, name='rentability_analysis_detail'),
    path('analyses/<int:pk>/edit/', views.rentability_analysis_update, name='rentability_analysis_update'),
    path('analyses/<int:pk>/delete/', views.rentability_analysis_delete, name='rentability_analysis_delete'),

    # Analyse rapide
    path('quick-analysis/', views.quick_analysis, name='quick_analysis'),

    # Comparaison des stations
    path('comparison/', views.stations_comparison, name='stations_comparison'),

    # APIs pour les graphiques (endpoints JSON)
    path('api/station/<int:station_id>/evolution/', views.api_station_evolution, name='api_station_evolution'),
    path('api/global-stats/', views.api_global_stats, name='api_global_stats'),

    # ===== NOUVELLES API POUR LES MODALES =====
    path('api/categories/', views.api_categories, name='api_categories'),
]
