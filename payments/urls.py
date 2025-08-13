from django.urls import path
from . import views
from django.urls import path, include

app_name = 'payments'  # Nomespace en minuscules, cohérent avec le fichier urls.py principal

urlpatterns = [
    # Centre de paiements

    path('contrats/', include('contrats.urls', namespace='contrats')),
    path('', views.centre_paiements, name='centre_paiements'),
    path('historique/', views.liste_paiements, name='liste_paiements'),
    path('rapide/<str:contrat_type>/<int:contrat_id>/', views.paiement_rapide, name='paiement_rapide'),
    path('recherche-avancee/', views.recherche_avancee, name='recherche_avancee'),
    path('details/<int:paiement_id>/', views.details_paiement, name='details_paiement'),
    # Pénalités
    path('penalites/', views.gestion_penalites, name='gestion_penalites'),
    path('penalites/creer/<str:contrat_type>/<int:contrat_id>/', views.creer_penalite, name='creer_penalite'),
    path('penalites/gerer/<int:penalite_id>/', views.gerer_penalite, name='gerer_penalite'),

    # Fonction d'application automatique des pénalités
    path('penalites/appliquer-auto/', views.appliquer_penalites_view, name='appliquer_penalites'),
    path('penalites/appliquer/', views.appliquer_penalites_view, name='appliquer_penalites'),

    path('penalites/export/', views.export_penalites, name='export_penalites'),
    path('penalites/<int:penalite_id>/pardonner/', views.pardonner_penalite, name='pardonner_penalite'),
    path('penalites/corriger-manquees/', views.corriger_penalites_manquees, name='corriger_penalites_manquees'),
    path('penalites/traiter-groupees/', views.traiter_penalites_groupees, name='traiter_penalites_groupees'),

    # Swaps (échanges de batteries)
    path('swaps/', views.liste_swaps, name='liste_swaps'),

    # Dashboard analytique
    path('analytique/', views.tableau_bord_analytique, name='analytique'),

    path('api/verifier-conge/', views.verifier_conge_api, name='verifier_conge_api'),
]