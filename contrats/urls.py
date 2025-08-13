from django.urls import path
from . import views

app_name = 'contrats'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard_contrats, name='dashboard'),

    # URLs pour les associations
    path('associations/', views.liste_associations, name='liste_associations'),
    path('associations/ajouter/', views.ajouter_association, name='ajouter_association'),
    path('associations/<int:association_id>/modifier/', views.modifier_association, name='modifier_association'),
    path('associations/<int:association_id>/supprimer/', views.supprimer_association, name='supprimer_association'),
    path('api/associations/', views.api_associations, name='api_associations'),

    # URLs pour les chauffeurs et motos (si pas déjà existantes)
    path('chauffeurs/ajouter/', views.ajouter_chauffeur, name='ajouter_chauffeur'),
    path('motos/ajouter/', views.ajouter_moto, name='ajouter_moto'),

    # Recherche des contrats
    path('recherche/', views.recherche_contrats, name='recherche_contrats'),

    # Gestion des chauffeurs
    path('chauffeurs/', views.liste_chauffeurs, name='liste_chauffeurs'),
    path('chauffeurs/ajouter/', views.ajouter_chauffeur, name='ajouter_chauffeur'),
    path('chauffeurs/<int:chauffeur_id>/', views.details_chauffeur, name='details_chauffeur'),
    path('chauffeurs/<int:chauffeur_id>/modifier/', views.modifier_chauffeur, name='modifier_chauffeur'),

    # Gestion des garants
    path('garants/', views.liste_garants, name='liste_garants'),
    path('garants/ajouter/', views.ajouter_garant, name='ajouter_garant'),
    path('garants/<int:garant_id>/', views.details_garant, name='details_garant'),
    path('garants/<int:garant_id>/modifier/', views.modifier_garant, name='modifier_garant'),

    # Gestion des contrats chauffeur
    path('chauffeur/', views.liste_contrats_chauffeur, name='liste_contrats_chauffeur'),
    path('chauffeur/ajouter/', views.ajouter_contrat_chauffeur, name='ajouter_contrat_chauffeur'),
    path('chauffeur/<int:contrat_id>/', views.details_contrat_chauffeur, name='details_contrat_chauffeur'),
    path('chauffeur/<int:contrat_id>/modifier/', views.modifier_contrat_chauffeur, name='modifier_contrat_chauffeur'),
    path('chauffeurs/ajax/ajouter/', views.ajouter_chauffeur_ajax, name='ajouter_chauffeur_ajax'),

    # Gestion des contrats partenaire
    path('partenaires/', views.liste_partenaires, name='liste_partenaires'),
    path('partenaires/ajouter/', views.ajouter_partenaire, name='ajouter_partenaire'),
    path('partenaires/<int:partenaire_id>/', views.details_partenaire, name='details_partenaire'),
    path('partenaires/<int:partenaire_id>/modifier/', views.modifier_partenaire, name='modifier_partenaire'),
    path('partenaires/ajax/ajouter/', views.ajouter_partenaire_ajax, name='ajouter_partenaire_ajax'),

    # Gestion des contrats partenaire
    path('partenaire/', views.liste_contrats_partenaire, name='liste_contrats_partenaire'),
    path('partenaire/ajouter/', views.ajouter_contrat_partenaire, name='ajouter_contrat_partenaire'),
    path('partenaire/<int:contrat_id>/', views.details_contrat_partenaire, name='details_contrat_partenaire'),
    path('partenaire/<int:contrat_id>/modifier/', views.modifier_contrat_partenaire,
         name='modifier_contrat_partenaire'),

    # Gestion des contrats batterie
    path('batterie/', views.liste_contrats_batterie, name='liste_contrats_batterie'),
    path('batterie/ajouter/', views.ajouter_contrat_batterie, name='ajouter_contrat_batterie'),
    path('batterie/<int:contrat_id>/', views.details_contrat_batterie, name='details_contrat_batterie'),
    path('batterie/<int:contrat_id>/modifier/', views.modifier_contrat_batterie, name='modifier_contrat_batterie'),

    # Gestion des congés
    path('conges/', views.liste_conges, name='liste_conges'),
    path('conges/ajouter/', views.ajouter_conge, name='ajouter_conge'),
    path('conges/ajouter/<int:contrat_id>/', views.ajouter_conge, name='ajouter_conge_pour_contrat'),
    path('conges/<int:conge_id>/', views.details_conge, name='details_conge'),
    path('conges/<int:conge_id>/statut/', views.modifier_statut_conge, name='modifier_statut_conge'),

    # Nouvelles URLs pour l'API de recherche et l'ajout AJAX
    path('api/recherche-proprietaire/', views.recherche_proprietaire, name='recherche_proprietaire'),
    path('api/ajouter-chauffeur-ajax/', views.ajouter_chauffeur_ajax, name='ajouter_chauffeur_ajax'),
    path('api/ajouter-partenaire-ajax/', views.ajouter_partenaire_ajax, name='ajouter_partenaire_ajax'),

    path('conges/export/', views.export_conges, name='export_conges'),

]