from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count, F, Q
from django.http import JsonResponse
from datetime import datetime, timedelta
from payments.models import Swap
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods



from .models import (
    ValidatedUser,
    Garant,
    ContratChauffeur,
    ContratPartenaire,
    ContratBatterie,
    CongesChauffeur,
    ContratPartenaireMoto,  # Ajoute cette ligne
    MotosValides,

    Partenaire  # Ajoute aussi cette ligne si elle n'y est pas déjà
)

from .forms import (
    ChauffeurForm,
    GarantForm,
            MotoForm,
    AssociationUserMotoForm,
    ContratChauffeurForm,
    ContratPartenaireForm,
    ContratBatterieForm,
    CongesChauffeurForm,
    PartenaireForm,
)


@login_required(login_url='/login/')
def liste_chauffeurs(request):
    """Modifie un chauffeur existant."""

    """Affiche la liste de tous les chauffeurs."""
    chauffeurs = ValidatedUser.objects.all().order_by('nom', 'prenom')

    return render(request, 'contrats/chauffeurs/liste.html', {
        'chauffeurs': chauffeurs,
        'titre': 'Liste des Chauffeurs'
    })


@login_required(login_url='/login/')
def details_chauffeur(request, chauffeur_id):
    """Affiche les détails d'un chauffeur spécifique."""
    chauffeur = get_object_or_404(ValidatedUser, id=chauffeur_id)

    contrats_chauffeur = ContratChauffeur.objects.filter(association__validated_user=chauffeur)
 # Related name du modèle ContratChauffeur
    contrats_batterie = chauffeur.contrats_batterie.all()    # Related name du modèle ContratBatterie

    # Regrouper tous les contrats
    tous_contrats = list(contrats_chauffeur) + list(contrats_batterie)

    return render(request, 'contrats/chauffeurs/details.html', {
        'chauffeur': chauffeur,
        'contrats_chauffeur': contrats_chauffeur,
        'contrats_batterie': contrats_batterie,
        'tous_contrats': tous_contrats,
        'titre': f'Détails du chauffeur : {chauffeur.nom} {chauffeur.prenom}'
    })


@login_required(login_url='/login/')
def ajouter_chauffeur(request):
    """Ajoute un nouveau chauffeur."""

    if request.method == 'POST':
        form = ChauffeurForm(request.POST, request.FILES)
        if form.is_valid():
            chauffeur = form.save()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax'):
                # Utiliser explicitement la méthode __str__ ou une propriété spécifique
                chauffeur_name = f"{chauffeur.prenom} {chauffeur.nom}"

                # Retourner une réponse JSON avec des données explicites
                return JsonResponse({
                    'success': True,
                    'id': chauffeur.id,
                    'name': chauffeur_name,  # Nom complet explicite
                    'message': 'Chauffeur ajouté avec succès!'
                })
            # Si c'est une requête AJAX (depuis le modal)
            if 'ajax' in request.GET:
                return JsonResponse({
                    'success': True,
                    'id': chauffeur.id,
                    'nom_complet': chauffeur.nom_complet
                })

            messages.success(request, f'Le chauffeur {chauffeur.nom} {chauffeur.prenom} a été ajouté avec succès.')

            return redirect('contrats:details_chauffeur', chauffeur_id=chauffeur.id)
        else:
            # Si c'est une requête AJAX, retourner les erreurs au format JSON
            if 'ajax' in request.GET:
                errors = []
                for field, error_list in form.errors.items():
                    for error in error_list:
                        errors.append(f"{field}: {error}")
                return JsonResponse({
                    'success': False,
                    'errors': errors
                })
    else:
        form = ChauffeurForm()

    # Si c'est une requête AJAX, rendre le formulaire modal
    if 'ajax' in request.GET:
        return render(request, 'contrats/chauffeurs/formulaire_modal.html', {
            'form': form,
            'titre': 'Ajouter un chauffeur',
            'action': 'Ajouter'
        })

    return render(request, 'contrats/chauffeurs/formulaire.html', {
        'form': form,
        'titre': 'Ajouter un chauffeur',
        'action': 'Ajouter'
    })


@login_required(login_url='/login/')
def modifier_chauffeur(request, chauffeur_id):
    """Modifie un chauffeur existant."""

    chauffeur = get_object_or_404(ValidatedUser, id=chauffeur_id)

    if request.method == 'POST':
        form = ChauffeurForm(request.POST, request.FILES, instance=chauffeur)
        if form.is_valid():
            chauffeur = form.save()
            messages.success(request, f'Le chauffeur {chauffeur.nom} {chauffeur.prenom} a été mis à jour avec succès.')
            return redirect('details_chauffeur', chauffeur_id=chauffeur.id)
    else:
        form = ChauffeurForm(instance=chauffeur)

    return render(request, 'contrats/chauffeurs/formulaire.html', {
        'form': form,
        'chauffeur': chauffeur,
        'titre': f'Modifier le chauffeur: {chauffeur.nom} {chauffeur.prenom}',
        'action': 'Modifier'
    })


@login_required(login_url='/login/')
def liste_garants(request):
    """Affiche la liste de tous les garants."""
    garants = Garant.objects.all().order_by('nom', 'prenom')

    return render(request, 'contrats/garants/liste.html', {
        'garants': garants,
        'titre': 'Liste des Garants'
    })


@login_required(login_url='/login/')
def details_garant(request, garant_id):
    """Affiche les détails d'un garant spécifique."""
    garant = get_object_or_404(Garant, id=garant_id)
    contrats_garantis = garant.contrats_garantis.all()

    return render(request, 'contrats/garants/details.html', {
        'garant': garant,
        'contrats_garantis': contrats_garantis,
        'titre': f'Détails du garant: {garant.prenom} {garant.nom}'
    })


@login_required(login_url='/login/')
def ajouter_garant(request):
    """Ajoute un nouveau garant."""
    if request.method == 'POST':
        form = GarantForm(request.POST, request.FILES)
        if form.is_valid():
            garant = form.save()
            messages.success(request, f'Le garant {garant.prenom} {garant.nom} a été ajouté avec succès.')

            # Si ajouté depuis un formulaire de contrat, retourner l'ID pour sélection
            if 'ajax' in request.GET:
                return JsonResponse({
                    'success': True,
                    'id': garant.id,
                    'nom': f'{garant.prenom} {garant.nom} - {garant.numero_cni}'
                })

            return redirect('details_garant', garant_id=garant.id)
    else:
        form = GarantForm()

    context = {
        'form': form,
        'titre': 'Ajouter un garant',
        'action': 'Ajouter'
    }

    # Si c'est une requête ajax pour un modal, renvoyer juste le formulaire
    if 'ajax' in request.GET:
        return render(request, 'contrats/garants/formulaire_modal.html', context)

    return render(request, 'contrats/garants/formulaire.html', context)


@login_required(login_url='/login/')
def modifier_garant(request, garant_id):
    """Modifie un garant existant."""
    garant = get_object_or_404(Garant, id=garant_id)

    if request.method == 'POST':
        form = GarantForm(request.POST, request.FILES, instance=garant)
        if form.is_valid():
            garant = form.save()
            messages.success(request, f'Le garant {garant.prenom} {garant.nom} a été mis à jour avec succès.')
            return redirect('details_garant', garant_id=garant.id)
    else:
        form = GarantForm(instance=garant)

    return render(request, 'contrats/garants/formulaire.html', {
        'form': form,
        'garant': garant,
        'titre': f'Modifier le garant: {garant.prenom} {garant.nom}',
        'action': 'Modifier'
    })


@login_required(login_url='/login/')
def liste_partenaires(request):
    partenaires = Partenaire.objects.all().order_by('nom', 'prenom')
    return render(request, 'contrats/partenaires/liste.html', {
        'partenaires': partenaires,
        'titre': 'Liste de Partenaires'
    })


@login_required(login_url='/login/')
def ajouter_partenaire(request):
    """Ajoute un nouveau partenaire."""

    if request.method == 'POST':
        form = PartenaireForm(request.POST, request.FILES)
        if form.is_valid():
            partenaire = form.save()
            messages.success(request, f'Le Partenaire {partenaire.prenom} {partenaire.nom} a été ajouté avec succès.')
            return redirect('contrats:details_partenaire', partenaire_id=partenaire.id)
    else:
        form = PartenaireForm()  # Vous aviez juste form=PartenaireForm sans les parenthèses

    context = {
        'form': form,
        'titre': 'Ajouter Partenaire',
        'action': 'Ajouter'
    }
    return render(request, 'contrats/partenaires/formulaire.html', context)  # Correction du chemin du template


@login_required(login_url='/login/')
def details_partenaire(request, partenaire_id):
    """Affiche les détails d'un partenaire spécifique."""
    partenaire = get_object_or_404(Partenaire, id=partenaire_id)
    contrats = partenaire.contrats.all()

    return render(request, 'contrats/partenaires/details.html', {
        'partenaire': partenaire,
        'contrats_partenaire': contrats,
        'titre': f'Details du partenaire:{partenaire.prenom} {partenaire.nom}'
    })


@login_required(login_url='/login/')
def modifier_partenaire(request, partenaire_id):
    partenaire = get_object_or_404(Partenaire, id=partenaire_id)

    if request.method == 'POST':
        form = PartenaireForm(request.POST, request.FILES, instance=partenaire)
        if form.is_valid():
            partenaire = form.save()
            messages.success(request,
                             f'Le partenaire {partenaire.nom} {partenaire.prenom} a été mis à jour avec succès.')
            return redirect('contrats:details_partenaire', partenaire_id=partenaire.id)
    else:
        form = PartenaireForm(instance=partenaire)

    return render(request, 'contrats/partenaires/formulaire.html', {
        'form': form,
        'partenaire': partenaire,
        'titre': f'Modifier le partenaire: {partenaire.prenom} {partenaire.nom}',
        'action': 'Modifier'
    })


@login_required(login_url='/login/')
def liste_contrats_chauffeur(request):
    contrats = ContratChauffeur.objects.all().order_by('-date_signature')

    for contrat in contrats:
        if contrat.montant_total > 0:
            contrat.pourcentage_paye = (contrat.montant_paye / contrat.montant_total) * 100
        else:
            contrat.pourcentage_paye = 0

    return render(request, 'contrats/contrats_chauffeur/liste.html', {
        'contrats': contrats,
        'titre': 'Liste des Contrats Chauffeur'
    })


@login_required(login_url='/login/')
def details_contrat_chauffeur(request, contrat_id):
    """Affiche les détails d'un contrat chauffeur spécifique."""
    contrat = get_object_or_404(ContratChauffeur, id=contrat_id)
    conges = contrat.conges.all().order_by('-date_demande')

    return render(request, 'contrats/contrats_chauffeur/details.html', {
        'contrat': contrat,
        'conges': conges,
        'titre': f'Contrat Chauffeur: {contrat.reference}'
    })


@login_required(login_url='/login/')
def ajouter_contrat_chauffeur(request):
    if request.method == 'POST':
        form = ContratChauffeurForm(request.POST, request.FILES)
        if form.is_valid():
            contrat = form.save(commit=False)

            # Calcul automatique du montant par paiement principal
            contrat.montant_par_paiement = contrat.calculer_montant_par_paiement()

            # Calculer la date de fin en fonction de la durée
            if contrat.duree_semaines:
                contrat.duree_jours = contrat.duree_semaines * 7
                contrat.date_fin = contrat.date_debut + timedelta(days=contrat.duree_jours)

            contrat.save()

            # Génération de la référence pour le contrat batterie
            prefix = "CBA"
            date_str = datetime.now().strftime("%Y%m%d")
            count = ContratBatterie.objects.filter(reference__startswith=f"{prefix}{date_str}").count() + 1
            reference_batterie = f"{prefix}{date_str}-{count:03d}"

            # Création automatique du contrat batterie associé
            contrat_batterie = ContratBatterie(
                reference=reference_batterie,
                chauffeur = contrat.association.validated_user,
                montant_total=contrat.montant_caution_batterie,
                montant_paye=0,
                montant_engage=contrat.montant_engage_batterie,  # Utiliser le montant engagé saisi
                montant_engage_batterie=contrat.montant_engage_batterie,  # Nouveau champ
                frequence_paiement=contrat.frequence_paiement,
                date_signature=contrat.date_signature,
                date_debut=contrat.date_debut,
                duree_semaines=contrat.duree_semaines,
                duree_jours=contrat.duree_jours,
                date_fin=contrat.date_debut + timedelta(days=contrat.duree_caution_batterie),
                montant_caution=contrat.montant_caution_batterie,
                duree_caution=contrat.duree_caution_batterie,
                statut=contrat.statut,
            )

            # Le montant par paiement sera calculé automatiquement lors du save() du contrat batterie
            contrat_batterie.save()

            messages.success(request,
                             f'Le contrat chauffeur {contrat.reference} et le contrat batterie associé ont été créés avec succès.')
            return redirect('contrats:details_contrat_chauffeur', contrat_id=contrat.id)
    else:
        # Générer une référence unique automatiquement
        prefix = "PXM"
        date_str = datetime.now().strftime("%Y%m%d")
        count = ContratChauffeur.objects.filter(reference__startswith=f"{prefix}{date_str}").count() + 1
        reference_auto = f"{prefix}{date_str}-{count:03d}"

        form = ContratChauffeurForm(initial={'reference': reference_auto})

    return render(request, 'contrats/contrats_chauffeur/formulaire.html', {
        'form': form,
        'titre': 'Nouveau Contrat Chauffeur',
        'action': 'Créer'
    })


@login_required(login_url='/login/')
def modifier_contrat_chauffeur(request, contrat_id):
    """Modifie un contrat chauffeur existant."""
    contrat = get_object_or_404(ContratChauffeur, id=contrat_id)

    if request.method == 'POST':
        form = ContratChauffeurForm(request.POST, request.FILES, instance=contrat)
        if form.is_valid():
            contrat = form.save(commit=False)

            # Recalculer le montant par paiement si nécessaire
            if 'montant_total' in form.changed_data or 'frequence_paiement' in form.changed_data or 'duree_semaines' in form.changed_data:
                contrat.montant_par_paiement = contrat.calculer_montant_par_paiement()

            # Recalculer la date de fin si la durée ou la date de début a changé
            if 'date_debut' in form.changed_data or 'duree_semaines' in form.changed_data:
                if contrat.duree_semaines:
                    contrat.duree_jours = contrat.duree_semaines * 7
                    contrat.date_fin = contrat.date_debut + timedelta(days=contrat.duree_jours)

            contrat.save()

            # Mettre à jour le contrat batterie associé si nécessaire
            if 'montant_engage_batterie' in form.changed_data:
                contrat_batterie = ContratBatterie.objects.filter(chauffeur=contrat.chauffeur).first()
                if contrat_batterie:
                    contrat_batterie.montant_engage_batterie = contrat.montant_engage_batterie
                    contrat_batterie.montant_engage = contrat.montant_engage_batterie
                    contrat_batterie.save()

            messages.success(request, f'Le contrat chauffeur {contrat.reference} a été mis à jour avec succès.')
            return redirect('contrats:details_contrat_chauffeur', contrat_id=contrat.id)

    else:
        form = ContratChauffeurForm(instance=contrat)

    return render(request, 'contrats/contrats_chauffeur/formulaire.html', {
        'form': form,
        'contrat': contrat,
        'titre': f'Modifier le contrat: {contrat.reference}',
        'action': 'Modifier'
    })


# VUES POUR LA GESTION DES CONGÉS CHAUFFEUR AVEC CORRECTION COMPLÈTE


@login_required(login_url='/login/')
def liste_conges(request):
    conges = CongesChauffeur.objects.all().order_by('-date_demande')

    # Filtres
    statut = request.GET.get('statut')
    if statut:
        conges = conges.filter(statut=statut)

    periode = request.GET.get('periode')
    if periode:
        today = timezone.now().date()
        if periode == 'en_cours':
            conges = conges.filter(date_debut__lte=today, date_fin__gte=today)
        elif periode == 'a_venir':
            conges = conges.filter(date_debut__gt=today)
        elif periode == 'termines':
            conges = conges.filter(date_fin__lt=today)

    return render(request, 'contrats/conges/liste.html', {
        'conges': conges,
        'statut_filter': statut,
        'periode_filter': periode,
        'titre': 'Liste des Congés'
    })


@login_required(login_url='/login/')
def details_conge(request, conge_id):
    conge = get_object_or_404(CongesChauffeur, id=conge_id)
    return render(request, 'contrats/conges/details.html', {
        'conge': conge,
        'titre': f"Détails du congé: {conge.contrat.chauffeur.nom_complet}"
    })


@login_required(login_url='/login/')
def ajouter_conge(request, contrat_id=None):
    contrat = None
    if contrat_id:
        contrat = get_object_or_404(ContratChauffeur, id=contrat_id)

    if request.method == 'POST':
        form = CongesChauffeurForm(request.POST)
        if form.is_valid():
            conge = form.save(commit=False)

            # Rattacher le contrat si passé par l'URL
            if contrat_id and not conge.contrat_id:
                conge.contrat = contrat

            # Calcul du nombre de jours
            if conge.date_debut and conge.date_fin:
                conge.nombre_jours = (conge.date_fin - conge.date_debut).days + 1

            # Validation du solde de congés
            jours_restant = conge.contrat.jours_conges_restants if conge.contrat else 0
            if conge.nombre_jours is not None and jours_restant is not None:
                if conge.nombre_jours > jours_restant:
                    messages.error(
                        request,
                        f"Le nombre de jours demandés ({conge.nombre_jours}) dépasse le solde disponible ({jours_restant})."
                    )
                    return render(request, 'contrats/conges/formulaire.html', {
                        'form': form,
                        'contrat': contrat,
                        'titre': 'Demander un congé',
                        'action': 'Demander'
                    })

            # Enregistrer le congé
            conge.save()

            messages.success(request, 'La demande de congé a été enregistrée avec succès.')

            # Si le congé est approuvé, mettre à jour le contrat
            if conge.statut in ['approuvé', 'planifié', 'en_cours']:
                # La méthode save de CongesChauffeur gère déjà la prolongation du contrat
                messages.info(request,
                              f"La durée du contrat a été prolongée de {conge.nombre_jours} jours "
                              f"pour tenir compte du congé."
                              )

            if contrat_id:
                return redirect('contrats:details_contrat_chauffeur', contrat_id=contrat_id)
            return redirect('contrats:details_conge', conge_id=conge.id)
    else:
        initial = {'contrat': contrat} if contrat else {}
        form = CongesChauffeurForm(initial=initial)
        if contrat:
            form.fields['contrat'].queryset = ContratChauffeur.objects.filter(id=contrat.id)

    return render(request, 'contrats/conges/formulaire.html', {
        'form': form,
        'contrat': contrat,
        'titre': 'Demander un congé',
        'action': 'Demander'
    })


@login_required(login_url='/login/')
def modifier_statut_conge(request, conge_id):
    """Modifie le statut d'un congé."""
    conge = get_object_or_404(CongesChauffeur, id=conge_id)

    if request.method == 'POST':
        nouveau_statut = request.POST.get('statut')
        commentaire = request.POST.get('commentaire', '')

        if nouveau_statut:
            # Sauvegarde de l'ancien statut pour comparaison
            ancien_statut = conge.statut

            # Mise à jour du statut
            conge.statut = nouveau_statut
            conge.commentaire = commentaire

            # Si le congé est approuvé, enregistrer la date d'approbation
            if nouveau_statut in ['approuvé', 'planifié'] and ancien_statut not in ['approuvé', 'planifié', 'en_cours']:
                conge.date_approbation = timezone.now()
                conge.approuve_par = f"{request.user.prenom} {request.user.nom}"

            conge.save()

            # Message approprié selon le type de changement
            if nouveau_statut in ['approuvé', 'planifié']:
                messages.success(request, f'Le congé a été approuvé avec succès.')
            elif nouveau_statut in ['annulé', 'rejeté']:
                messages.success(request, f'Le congé a été {nouveau_statut}.')
            else:
                messages.success(request, f'Le statut du congé a été mis à jour avec succès.')

            if 'contrat_id' in request.GET:
                return redirect('details_contrat_chauffeur', contrat_id=request.GET.get('contrat_id'))
            return redirect('contrats:details_conge', conge_id=conge.id)

    # Redirection en cas de méthode non-POST
    if 'contrat_id' in request.GET:
        return redirect('contrats: details_contrat_chauffeur', contrat_id=request.GET.get('contrat_id'))
    return redirect('contrats:details_conge', conge_id=conge.id)


@login_required(login_url='/login/')
def dashboard_contrats(request):
    """Tableau de bord des contrats."""
    # Statistiques générales
    total_contrats_chauffeur = ContratChauffeur.objects.count()
    total_contrats_partenaire = ContratPartenaire.objects.count()
    total_contrats_batterie = ContratBatterie.objects.count()

    # Contrats par statut
    contrats_actifs = ContratChauffeur.objects.filter(statut='actif').count()
    contrats_termines = ContratChauffeur.objects.filter(statut='terminé').count()
    contrats_suspendus = ContratChauffeur.objects.filter(statut='suspendu').count()

    # Contrats récents
    contrats_recents = list(ContratChauffeur.objects.order_by('-date_signature')[:5])

    # Congés en cours et à venir
    today = timezone.now().date()
    conges_en_cours = CongesChauffeur.objects.filter(
        statut__in=['approuvé', 'planifié', 'en_cours'],
        date_debut__lte=today,
        date_fin__gte=today
    ).order_by('date_fin')[:5]

    conges_a_venir = CongesChauffeur.objects.filter(
        statut__in=['approuvé', 'planifié'],
        date_debut__gt=today
    ).order_by('date_debut')[:5]

    # Demandes de congés en attente
    demandes_conges = CongesChauffeur.objects.filter(
        statut='en_attente'
    ).order_by('date_demande')[:10]

    return render(request, 'contrats/dashboard.html', {
        'titre': 'Tableau de Bord des Contrats',
        'total_contrats_chauffeur': total_contrats_chauffeur,
        'total_contrats_partenaire': total_contrats_partenaire,
        'total_contrats_batterie': total_contrats_batterie,
        'contrats_actifs': contrats_actifs,
        'contrats_termines': contrats_termines,
        'contrats_suspendus': contrats_suspendus,
        'contrats_recents': contrats_recents,
        'conges_en_cours': conges_en_cours,
        'conges_a_venir': conges_a_venir,
        'demandes_conges': demandes_conges,
    })


@login_required(login_url='/login/')
def liste_contrats_partenaire(request):
    """Affiche la liste de tous les contrats partenaire."""
    contrats = ContratPartenaire.objects.all().order_by('-date_signature')

    return render(request, 'contrats/contrats_partenaire/liste.html', {
        'contrats': contrats,
        'titre': 'Liste des Contrats Partenaire'
    })


# 2. Modifie la fonction details_contrat_partenaire


@login_required(login_url='/login/')
def details_contrat_partenaire(request, contrat_id):
    """Affiche les détails d'un contrat partenaire spécifique."""
    contrat = get_object_or_404(ContratPartenaire, id=contrat_id)

    # Obtenir les motos via ContratPartenaireMoto au lieu de contrat.motos
    motos = MotosValides.objects.filter(
        contrats_partenaire__contrat=contrat
    )

    return render(request, 'contrats/contrats_partenaire/details.html', {
        'contrat': contrat,
        'motos': motos,
        'titre': f'Contrat Partenaire: {contrat.reference}'
    })


@login_required(login_url='/login/')
def ajouter_contrat_partenaire(request):
    """Ajoute un nouveau contrat partenaire."""
    if request.method == 'POST':
        form = ContratPartenaireForm(request.POST, request.FILES)
        if form.is_valid():
            contrat = form.save(commit=False)

            # Calcul du montant par paiement avant sauvegarde
            contrat.montant_par_paiement = contrat.calculer_montant_par_paiement()

            # Calcul de la date de fin en fonction de la durée et de la date de début
            if contrat.duree_semaines:
                contrat.duree_jours = contrat.duree_semaines * 7
                contrat.date_fin = contrat.date_debut + timedelta(days=contrat.duree_jours)

            contrat.save()

            # Gérer les motos associées
            if form.cleaned_data.get('motos'):
                # Supprimer les associations existantes
                ContratPartenaireMoto.objects.filter(contrat=contrat).delete()

                # Créer les nouvelles associations
                for moto in form.cleaned_data['motos']:
                    ContratPartenaireMoto.objects.create(contrat=contrat, moto=moto)

            # Accéder aux motos via le FormField personnalisé
            nombre_motos = len(form.cleaned_data.get('motos', []))
            contrat.montant_caution_batterie = 50000 * nombre_motos  # 50 000 FCFA par moto
            contrat.save()

            # Génération de la référence pour le contrat batterie
            prefix = "CBA"
            date_str = datetime.now().strftime("%Y%m%d")
            count = ContratBatterie.objects.filter(reference__startswith=f"{prefix}{date_str}").count() + 1
            reference_batterie = f"{prefix}{date_str}-{count:03d}"

            # Création automatique du contrat batterie associé
            contrat_batterie = ContratBatterie(
                reference=reference_batterie,
                partenaire=contrat.partenaire,  # Utiliser le partenaire au lieu du chauffeur
                chauffeur=None,  # Pas de chauffeur pour un contrat partenaire
                montant_total=contrat.montant_caution_batterie,
                montant_paye=0,
                montant_engage=contrat.montant_engage_batterie,  # Utiliser le montant engagé saisi
                montant_engage_batterie=contrat.montant_engage_batterie,  # Nouveau champ
                frequence_paiement=contrat.frequence_paiement,
                date_signature=contrat.date_signature,
                date_debut=contrat.date_debut,
                duree_semaines=contrat.duree_semaines,
                duree_jours=contrat.duree_jours,
                date_fin=contrat.date_debut + timedelta(days=contrat.duree_caution_batterie),
                montant_caution=contrat.montant_caution_batterie,
                duree_caution=contrat.duree_caution_batterie,
                statut=contrat.statut,
            )

            # Le montant par paiement sera calculé automatiquement lors du save()
            contrat_batterie.save()

            messages.success(request,
                             f'Le contrat partenaire {contrat.reference} et le contrat batterie associé ont été créés avec succès.')
            return redirect('contrats:details_contrat_partenaire', contrat_id=contrat.id)
    else:
        # Générer une référence unique automatiquement
        prefix = "CPA"
        date_str = datetime.now().strftime("%Y%m%d")
        count = ContratPartenaire.objects.filter(reference__startswith=f"{prefix}{date_str}").count() + 1
        reference_auto = f"{prefix}{date_str}-{count:03d}"

        form = ContratPartenaireForm(initial={'reference': reference_auto})

    return render(request, 'contrats/contrats_partenaire/formulaire.html', {
        'form': form,
        'titre': 'Nouveau Contrat Partenaire',
        'action': 'Créer'
    })


@login_required(login_url='/login/')
def modifier_contrat_partenaire(request, contrat_id):
    """Modifie un contrat partenaire existant."""
    contrat = get_object_or_404(ContratPartenaire, id=contrat_id)

    if request.method == 'POST':
        form = ContratPartenaireForm(request.POST, request.FILES, instance=contrat)
        if form.is_valid():
            contrat = form.save(commit=False)

            # Recalculer le montant par paiement si nécessaire
            if 'montant_total' in form.changed_data or 'frequence_paiement' in form.changed_data or 'duree_semaines' in form.changed_data:
                contrat.montant_par_paiement = contrat.calculer_montant_par_paiement()

            # Recalculer la date de fin si la durée ou la date de début a changé
            if 'date_debut' in form.changed_data or 'duree_semaines' in form.changed_data:
                if contrat.duree_semaines:
                    contrat.duree_jours = contrat.duree_semaines * 7
                    contrat.date_fin = contrat.date_debut + timedelta(days=contrat.duree_jours)

            contrat.save()

            # Gérer les motos associées
            if 'motos' in form.cleaned_data:
                # Supprimer les associations existantes
                ContratPartenaireMoto.objects.filter(contrat=contrat).delete()

                # Créer les nouvelles associations
                for moto in form.cleaned_data['motos']:
                    ContratPartenaireMoto.objects.create(contrat=contrat, moto=moto)

            # Si les motos ont changé, recalculer le montant de caution batterie
            if 'motos' in form.changed_data:
                nombre_motos = len(form.cleaned_data.get('motos', []))
                contrat.montant_caution_batterie = 50000 * nombre_motos  # 50 000 FCFA par moto
                contrat.save()

            # Mise à jour du contrat batterie associé
            contrat_batterie = ContratBatterie.objects.filter(partenaire=contrat.partenaire).first()

            if contrat_batterie:
                contrat_batterie.montant_total = contrat.montant_caution_batterie
                contrat_batterie.montant_caution = contrat.montant_caution_batterie
                contrat_batterie.montant_engage_batterie = contrat.montant_engage_batterie
                contrat_batterie.montant_engage = contrat.montant_engage_batterie
                contrat_batterie.frequence_paiement = contrat.frequence_paiement
                contrat_batterie.date_signature = contrat.date_signature
                contrat_batterie.date_debut = contrat.date_debut
                contrat_batterie.duree_semaines = contrat.duree_semaines
                contrat_batterie.duree_jours = contrat.duree_jours
                contrat_batterie.date_fin = contrat.date_debut + timedelta(days=contrat.duree_caution_batterie)
                contrat_batterie.duree_caution = contrat.duree_caution_batterie
                contrat_batterie.statut = contrat.statut

                # Le montant par paiement sera recalculé automatiquement lors du save()
                contrat_batterie.save()

            messages.success(request, f'Le contrat partenaire {contrat.reference} a été mis à jour avec succès.')
            return redirect('contrats:details_contrat_partenaire', contrat_id=contrat.id)
    else:
        form = ContratPartenaireForm(instance=contrat)

    return render(request, 'contrats/contrats_partenaire/formulaire.html', {
        'form': form,
        'contrat': contrat,
        'titre': f'Modifier le contrat: {contrat.reference}',
        'action': 'Modifier'
    })


@login_required(login_url='/login/')
def liste_contrats_batterie(request):
    """Affiche la liste de tous les contrats batterie."""
    contrats = ContratBatterie.objects.all().order_by('-date_signature')

    # Ajouter un attribut pour le type de propriétaire et calculer le pourcentage payé
    for contrat in contrats:
        if contrat.chauffeur:
            contrat.type_proprietaire = 'chauffeur'
            contrat.proprietaire = contrat.chauffeur
            contrat.proprietaire_nom = f"{contrat.chauffeur.prenom} {contrat.chauffeur.nom}"
        elif contrat.partenaire:
            contrat.type_proprietaire = 'partenaire'
            contrat.proprietaire = contrat.partenaire
            contrat.proprietaire_nom = f"{contrat.partenaire.prenom} {contrat.partenaire.nom}"
        else:
            contrat.type_proprietaire = 'inconnu'
            contrat.proprietaire = None
            contrat.proprietaire_nom = "Non défini"

        if contrat.montant_total > 0:
            contrat.pourcentage_paye = (contrat.montant_paye / contrat.montant_total) * 100
        else:
            contrat.pourcentage_paye = 0

        # Calculer le nombre de batteries
        contrat.nombre_batteries = int(contrat.montant_caution / 50000) if contrat.montant_caution else 0

    return render(request, 'contrats/contrats_batterie/liste.html', {
        'contrats': contrats,
        'titre': 'Liste des Contrats Batterie'
    })


from payments.models import Swap  # ou l'endroit où tu mets le modèle Swap


@login_required(login_url='/login/')
def details_contrat_batterie(request, contrat_id):
    contrat = get_object_or_404(ContratBatterie, id=contrat_id)

    # Identité
    if contrat.chauffeur:
        contrat.type_proprietaire = 'chauffeur'
        contrat.proprietaire = contrat.chauffeur
        contrat.proprietaire_nom = contrat.chauffeur.nom_complet
        swaps = Swap.objects.filter(phone=contrat.chauffeur.phone)
    elif contrat.partenaire:
        contrat.type_proprietaire = 'partenaire'
        contrat.proprietaire = contrat.partenaire
        contrat.proprietaire_nom = f"{contrat.partenaire.prenom} {contrat.partenaire.nom}"
        swaps = Swap.objects.filter(phone=contrat.partenaire.phone)
    else:
        contrat.type_proprietaire = 'inconnu'
        contrat.proprietaire = None
        contrat.proprietaire_nom = "Non défini"
        swaps = Swap.objects.none()

    # Autres calculs...
    # [ inchangé ]

    return render(request, 'contrats/contrats_batterie/details.html', {
        'contrat': contrat,
        'swaps': swaps,
        'titre': f'Contrat Batterie: {contrat.reference}'
    })


@login_required(login_url='/login/')
@require_http_methods(["GET", "POST"])
def ajouter_contrat_batterie(request):
    if request.method == 'POST':
        print("POST data:", request.POST)

        # Créer une copie mutable du QueryDict
        post_data = request.POST.copy()

        # Extraire et traiter le montant de caution
        montant_caution_str = post_data.get('montant_caution', '0')
        montant_caution_clean = ''.join(c for c in montant_caution_str if c.isdigit())

        try:
            montant_caution = int(montant_caution_clean)
        except ValueError:
            nombre_batteries = int(post_data.get('nombre_batteries', 1))
            montant_caution = 50000 * nombre_batteries

        # Ajouter les champs manquants pour la validation du formulaire
        post_data['montant_total'] = montant_caution  # Montant total = montant caution
        post_data['montant_caution'] = montant_caution  # Remplacer par la version nettoyée
        post_data['statut'] = 'actif'  # Valeur par défaut pour le statut

        # Gérer la liaison chauffeur ou partenaire
        proprietaire_id = post_data.get('proprietaire_id')
        proprietaire_type = post_data.get('proprietaire_type')

        if proprietaire_type == 'chauffeur':
            post_data['chauffeur'] = proprietaire_id
            post_data['type_proprietaire'] = 'chauffeur'
        elif proprietaire_type == 'partenaire':
            post_data['partenaire'] = proprietaire_id
            post_data['type_proprietaire'] = 'partenaire'

        form = ContratBatterieForm(post_data)
        print("Form errors:", form.errors)

        if form.is_valid():
            contrat = form.save(commit=False)

            # Mise à jour des champs additionnels
            if contrat.duree_semaines:
                contrat.duree_jours = contrat.duree_semaines * 7
                contrat.date_fin = contrat.date_debut + timedelta(days=contrat.duree_jours)

            # Le montant par paiement sera calculé automatiquement lors du save()
            contrat.save()

            messages.success(request, f'Le contrat batterie {contrat.reference} a été créé avec succès.')
            return redirect('contrats:details_contrat_batterie', contrat_id=contrat.id)
        else:
            messages.error(request, 'Des erreurs ont été détectées dans le formulaire.')
    else:
        # Générer une référence unique automatiquement
        prefix = "CBA"
        date_str = datetime.now().strftime("%Y%m%d")
        count = ContratBatterie.objects.filter(reference__startswith=f"{prefix}{date_str}").count() + 1
        reference_auto = f"{prefix}{date_str}-{count:03d}"

        form = ContratBatterieForm(initial={
            'reference': reference_auto,
            'date_signature': datetime.now().date(),
            'date_debut': datetime.now().date(),
            'duree_semaines': 61,  # Valeur par défaut
            'duree_caution': 100,  # 100 jours par défaut
            'frequence_paiement': 'journalier',
            'statut': 'actif'
        })

    return render(request, 'contrats/contrats_batterie/formulaire.html', {
        'form': form,
        'titre': 'Nouveau Contrat Batterie'
    })


@login_required(login_url='/login/')
def modifier_contrat_batterie(request, contrat_id):
    """Modifie un contrat batterie existant."""
    contrat = get_object_or_404(ContratBatterie, id=contrat_id)

    if request.method == 'POST':
        form = ContratBatterieForm(request.POST, instance=contrat)
        if form.is_valid():
            contrat = form.save()
            messages.success(request, f'Le contrat batterie {contrat.reference} a été mis à jour avec succès.')
            return redirect('contrats:details_contrat_batterie', contrat_id=contrat.id)
    else:
        form = ContratBatterieForm(instance=contrat)

    return render(request, 'contrats/contrats_batterie/formulaire.html', {
        'form': form,
        'contrat': contrat,
        'titre': f'Modifier le contrat: {contrat.reference}',
        'action': 'Modifier'
    })


# Fonction pour ajouter un nouveau chauffeur via AJAX
@login_required(login_url='/login/')
def ajouter_chauffeur_ajax(request):
    if request.method == 'POST':
        form = ChauffeurForm(request.POST, request.FILES)
        if form.is_valid():
            chauffeur = form.save()
            return JsonResponse({
                'success': True,
                'id': chauffeur.id,
                'nom_complet': chauffeur.nom_complet
            })
        else:
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = str(error_list[0])
            return JsonResponse({'success': False, 'errors': errors})

    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})


# Fonction pour ajouter un nouveau partenaire via AJAX
@login_required(login_url='/login/')
def ajouter_partenaire_ajax(request):
    if request.method == 'POST':
        form = PartenaireForm(request.POST, request.FILES)
        if form.is_valid():
            partenaire = form.save()
            return JsonResponse({
                'success': True,
                'id': partenaire.id,
                'nom_complet': f"{partenaire.prenom} {partenaire.nom}"
            })
        else:
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = str(error_list[0])
            return JsonResponse({'success': False, 'errors': errors})

    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})


@login_required(login_url='/login/')
def ajouter_contrat_batterie(request):
    if request.method == 'POST':
        print("POST data:", request.POST)

        # Créer une copie mutable du QueryDict
        post_data = request.POST.copy()

        # Extraire et traiter le montant de caution
        montant_caution_str = post_data.get('montant_caution', '0')
        montant_caution_clean = ''.join(c for c in montant_caution_str if c.isdigit())

        try:
            montant_caution = int(montant_caution_clean)
        except ValueError:
            nombre_batteries = int(post_data.get('nombre_batteries', 1))
            montant_caution = 50000 * nombre_batteries

        # Ajouter les champs manquants pour la validation du formulaire
        post_data['montant_total'] = montant_caution  # Montant total = montant caution
        post_data['montant_caution'] = montant_caution  # Remplacer par la version nettoyée
        post_data['statut'] = 'actif'  # Valeur par défaut pour le statut

        # Gérer la liaison chauffeur ou partenaire
        proprietaire_id = post_data.get('proprietaire_id')
        proprietaire_type = post_data.get('proprietaire_type')

        if proprietaire_type == 'chauffeur':
            post_data['chauffeur'] = proprietaire_id
            post_data['type_proprietaire'] = 'chauffeur'
        elif proprietaire_type == 'partenaire':
            post_data['partenaire'] = proprietaire_id
            post_data['type_proprietaire'] = 'partenaire'

        form = ContratBatterieForm(post_data)
        print("Form errors:", form.errors)

        if form.is_valid():
            contrat = form.save(commit=False)

            # Mise à jour des champs additionnels
            contrat.date_fin = contrat.date_debut + timedelta(weeks=contrat.duree_semaines)
            contrat.montant_par_paiement = contrat.calculer_montant_par_paiement()
            contrat.save()

            messages.success(request, f'Le contrat batterie {contrat.reference} a été créé avec succès.')
            return redirect('contrats:details_contrat_batterie', contrat_id=contrat.id)
        else:
            messages.error(request, 'Des erreurs ont été détectées dans le formulaire.')
    else:
        # Générer une référence unique automatiquement
        prefix = "CBA"
        date_str = datetime.now().strftime("%Y%m%d")
        count = ContratBatterie.objects.filter(reference__startswith=f"{prefix}{date_str}").count() + 1
        reference_auto = f"{prefix}{date_str}-{count:03d}"

        form = ContratBatterieForm(initial={
            'reference': reference_auto,
            'date_signature': datetime.now().date(),
            'date_debut': datetime.now().date(),
            'duree_semaines': 61,  # Valeur par défaut
            'duree_caution': 100,  # 100 jours par défaut
            'frequence_paiement': 'journalier',
            'statut': 'actif'
        })

    return render(request, 'contrats/contrats_batterie/formulaire.html', {
        'form': form,
        'titre': 'Nouveau Contrat Batterie'
    })


@login_required(login_url='/login/')
def recherche_proprietaire(request):
    """
    API pour rechercher un propriétaire (chauffeur ou partenaire) par nom, prénom ou téléphone.
    Utilisé pour l'autocomplétion dans le formulaire d'ajout de contrat batterie.
    """

    query = request.GET.get('query', '')
    type_proprietaire = request.GET.get('type', 'chauffeur')

    if len(query) < 2:
        return JsonResponse({'error': 'La requête doit contenir au moins 2 caractères'}, status=400)

    results = []

    if type_proprietaire == 'chauffeur':
        chauffeurs = Chauffeur.objects.filter(
            Q(nom__icontains=query) |
            Q(prenom__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query) |
            Q(numero_cni__icontains=query)
        )[:10]

        results = [{
            'id': c.id,
            'nom': c.nom,
            'prenom': c.prenom,
            'email': c.email,
            'phone': c.phone,
            'numero_cni': c.numero_cni
        } for c in chauffeurs]
    else:
        partenaires = Partenaire.objects.filter(
            Q(nom__icontains=query) |
            Q(prenom__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query) |
            Q(numero_cni__icontains=query)
        )[:10]

        results = [{
            'id': p.id,
            'nom': p.nom,
            'prenom': p.prenom,
            'email': p.email,
            'phone': p.phone,
            'numero_cni': p.numero_cni
        } for p in partenaires]

    return JsonResponse({'results': results})


@login_required(login_url='/login/')
def ajouter_chauffeur_ajax(request):
    """
    Vue pour ajouter un chauffeur via AJAX, utilisée dans la modale du formulaire d'ajout de contrat.
    """

    if request.method == 'POST':
        form = ChauffeurForm(request.POST, request.FILES)
        if form.is_valid():
            chauffeur = form.save()
            return JsonResponse({
                'success': True,
                'id': chauffeur.id,
                'nom_complet': f"{chauffeur.prenom} {chauffeur.nom}"
            })
        else:
            # Retourner les erreurs du formulaire
            errors = {}
            for field in form:
                if field.errors:
                    errors[field.name] = [error for error in field.errors]

            return JsonResponse({
                'success': False,
                'errors': errors
            })

    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)


@login_required(login_url='/login/')
def ajouter_partenaire_ajax(request):
    """
    Vue pour ajouter un partenaire via AJAX, utilisée dans la modale du formulaire d'ajout de contrat.
    """

    if request.method == 'POST':
        form = PartenaireForm(request.POST, request.FILES)
        if form.is_valid():
            partenaire = form.save()
            return JsonResponse({
                'success': True,
                'id': partenaire.id,
                'nom_complet': f"{partenaire.prenom} {partenaire.nom}"
            })
        else:
            # Retourner les erreurs du formulaire
            errors = {}
            for field in form:
                if field.errors:
                    errors[field.name] = [error for error in field.errors]

            return JsonResponse({
                'success': False,
                'errors': errors
            })

    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)


@login_required(login_url='/login/')
def recherche_contrats(request):
    """Recherche et filtre les contrats."""
    # Paramètres de recherche
    query = request.GET.get('q', '')
    type_contrat = request.GET.get('type', '')
    statut = request.GET.get('statut', '')
    date_debut = request.GET.get('date_debut', '')
    date_fin = request.GET.get('date_fin', '')

    # Résultats par défaut vides
    resultats_chauffeur = ContratChauffeur.objects.none()
    resultats_partenaire = ContratPartenaire.objects.none()
    resultats_batterie = ContratBatterie.objects.none()

    # Convertir les dates si fournies
    try:
        date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date() if date_debut else None
        date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date() if date_fin else None
    except ValueError:
        date_debut_obj = None
        date_fin_obj = None
        messages.error(request, "Format de date invalide. Utilisez le format YYYY-MM-DD.")

    # Appliquer les filtres
    if type_contrat in ['', 'chauffeur', 'tous']:
        resultats_chauffeur = ContratChauffeur.objects.all()

        # Filtre sur la référence ou le nom du chauffeur
        if query:
            resultats_chauffeur = resultats_chauffeur.filter(
                Q(reference__icontains=query) |
                Q(chauffeur__nom__icontains=query) |
                Q(chauffeur__prenom__icontains=query)
            )

        # Filtre sur le statut
        if statut:
            resultats_chauffeur = resultats_chauffeur.filter(statut=statut)

        # Filtre sur la date de signature
        if date_debut_obj:
            resultats_chauffeur = resultats_chauffeur.filter(date_signature__gte=date_debut_obj)
        if date_fin_obj:
            resultats_chauffeur = resultats_chauffeur.filter(date_signature__lte=date_fin_obj)

    if type_contrat in ['', 'partenaire', 'tous']:
        resultats_partenaire = ContratPartenaire.objects.all()

        # Filtre sur la référence ou le nom du partenaire
        if query:
            resultats_partenaire = resultats_partenaire.filter(
                Q(reference__icontains=query) |
                Q(partenaire__nom__icontains=query) |
                Q(partenaire__prenom__icontains=query)
            )

            # Si tu veux chercher aussi dans les motos associées, tu peux ajouter:
            moto_ids = ContratPartenaireMoto.objects.filter(
                moto__vin__icontains=query
            ).values_list('contrat_id', flat=True)
            resultats_partenaire = resultats_partenaire | ContratPartenaire.objects.filter(id__in=moto_ids)

        # Filtre sur le statut
        if statut:
            resultats_partenaire = resultats_partenaire.filter(statut=statut)

        # Filtre sur la date de signature
        if date_debut_obj:
            resultats_partenaire = resultats_partenaire.filter(date_signature__gte=date_debut_obj)
        if date_fin_obj:
            resultats_partenaire = resultats_partenaire.filter(date_signature__lte=date_fin_obj)

    if type_contrat in ['', 'batterie', 'tous']:
        resultats_batterie = ContratBatterie.objects.all()

        # Filtre sur la référence ou le nom du chauffeur
        if query:
            resultats_batterie = resultats_batterie.filter(
                Q(reference__icontains=query) |
                Q(chauffeur__nom__icontains=query) |
                Q(chauffeur__prenom__icontains=query)
            )

        # Filtre sur le statut
        if statut:
            resultats_batterie = resultats_batterie.filter(statut=statut)

        # Filtre sur la date de signature
        if date_debut_obj:
            resultats_batterie = resultats_batterie.filter(date_signature__gte=date_debut_obj)
        if date_fin_obj:
            resultats_batterie = resultats_batterie.filter(date_signature__lte=date_fin_obj)

    # Pagination des résultats
    page = request.GET.get('page', 1)

    # Trier les résultats par date de signature (décroissante)
    resultats_chauffeur = resultats_chauffeur.order_by('-date_signature')
    resultats_partenaire = resultats_partenaire.order_by('-date_signature')
    resultats_batterie = resultats_batterie.order_by('-date_signature')

    return render(request, 'contrats/recherche.html', {
        'titre': 'Recherche de Contrats',
        'resultats_chauffeur': resultats_chauffeur,
        'resultats_partenaire': resultats_partenaire,
        'resultats_batterie': resultats_batterie,
        'query': query,
        'type_contrat': type_contrat,
        'statut': statut,
        'date_debut': date_debut,
        'date_fin': date_fin,
    })


@login_required(login_url='/login/')
def export_conges(request):
    # ton code ici
    return HttpResponse("Export des congés")


@login_required
@require_http_methods(["GET", "POST"])
def ajouter_association(request):
    """Vue pour ajouter une nouvelle association chauffeur-moto."""

    if request.method == 'POST':
        form = AssociationUserMotoForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    association = form.save()

                    # Si c'est une requête AJAX (pour le modal)
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax'):
                        return JsonResponse({
                            'success': True,
                            'association_id': association.id,
                            'association_display': str(association),
                            'message': 'Association créée avec succès!'
                        })

                    messages.success(request, 'Association chauffeur-moto créée avec succès!')
                    return redirect('contrats:liste_associations')

            except ValidationError as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax'):
                    return JsonResponse({
                        'success': False,
                        'errors': form.errors,
                        'message': 'Erreur lors de la création de l\'association.'
                    })
                messages.error(request, f'Erreur: {e}')
        else:
            # Erreurs de validation du formulaire
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax'):
                return JsonResponse({
                    'success': False,
                    'errors': form.errors,
                    'message': 'Veuillez corriger les erreurs dans le formulaire.'
                })
    else:
        form = AssociationUserMotoForm()

    # Pour les requêtes AJAX, renvoyer le template modal
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax'):
        template_name = 'contrats/associations/modal_ajouter.html'
    else:
        template_name = 'contrats/associations/ajouter.html'

    context = {
        'form': form,
        'title': 'Ajouter une association chauffeur-moto',
        'action_url': 'contrats:ajouter_association',
    }

    return render(request, template_name, context)


@login_required
def liste_associations(request):
    """Vue pour lister toutes les associations."""
    associations = AssociationUserMoto.objects.select_related(
        'validated_user', 'moto_valide'
    ).all()

    context = {
        'associations': associations,
        'title': 'Liste des associations chauffeur-moto'
    }

    return render(request, 'contrats/associations/liste.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def modifier_association(request, association_id):
    """Vue pour modifier une association existante."""
    association = get_object_or_404(AssociationUserMoto, id=association_id)

    if request.method == 'POST':
        form = AssociationUserMotoForm(request.POST, instance=association)

        if form.is_valid():
            try:
                association = form.save()
                messages.success(request, 'Association modifiée avec succès!')
                return redirect('contrats:liste_associations')
            except ValidationError as e:
                messages.error(request, f'Erreur: {e}')
        else:
            messages.error(request, 'Veuillez corriger les erreurs dans le formulaire.')
    else:
        form = AssociationUserMotoForm(instance=association)

    context = {
        'form': form,
        'association': association,
        'title': 'Modifier l\'association',
        'action_url': 'contrats:modifier_association',
    }

    return render(request, 'contrats/associations/modifier.html', context)


@login_required
@require_http_methods(["POST"])
def supprimer_association(request, association_id):
    """Vue pour supprimer une association."""
    association = get_object_or_404(AssociationUserMoto, id=association_id)

    try:
        association.delete()
        messages.success(request, 'Association supprimée avec succès!')
    except Exception as e:
        messages.error(request, f'Erreur lors de la suppression: {e}')

    return redirect('contrats:liste_associations')


@login_required
def api_associations(request):
    """API pour récupérer les associations (pour Select2 par exemple)."""
    term = request.GET.get('term', '')

    associations = AssociationUserMoto.objects.select_related(
        'validated_user', 'moto_valide'
    )

    if term:
        associations = associations.filter(
            validated_user__nom__icontains=term
        ) | associations.filter(
            validated_user__prenom__icontains=term
        ) | associations.filter(
            moto_valide__model__icontains=term
        )

    results = []
    for association in associations[:20]:  # Limiter à 20 résultats
        results.append({
            'id': association.id,
            'text': str(association)
        })

    return JsonResponse({'results': results})


# Ajoutez ces vues dans votre views.py




@login_required
@require_http_methods(["GET", "POST"])
def ajouter_moto(request):
    """Vue pour ajouter une nouvelle moto."""

    if request.method == 'POST':
        form = MotoForm(request.POST)  # Vous devrez créer ce formulaire

        if form.is_valid():
            try:
                with transaction.atomic():
                    moto = form.save(commit=False)

                    # Générer un moto_unique_id s'il n'existe pas
                    if not moto.moto_unique_id:
                        import uuid
                        moto.moto_unique_id = str(uuid.uuid4())

                    # Définir les timestamps
                    from django.utils import timezone
                    if not moto.created_at:
                        moto.created_at = timezone.now()
                    moto.updated_at = timezone.now()

                    moto.save()

                    # Si c'est une requête AJAX
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax'):
                        return JsonResponse({
                            'success': True,
                            'moto_id': moto.id,
                            'moto_display': f"{moto.model} ({moto.vin})",
                            'message': 'Moto créée avec succès!'
                        })

                    messages.success(request, 'Moto créée avec succès!')
                    return redirect('contrats:liste_motos')  # Ajustez selon votre URL

            except ValidationError as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax'):
                    return JsonResponse({
                        'success': False,
                        'errors': form.errors,
                        'message': 'Erreur lors de la création de la moto.'
                    })
                messages.error(request, f'Erreur: {e}')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax'):
                return JsonResponse({
                    'success': False,
                    'errors': form.errors,
                    'message': 'Veuillez corriger les erreurs dans le formulaire.'
                })
    else:
        form = MotoForm()

    # Template différent pour AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax'):
        template_name = 'contrats/motos/modal_ajouter.html'
    else:
        template_name = 'contrats/motos/ajouter.html'

    context = {
        'form': form,
        'title': 'Ajouter une moto',
        'action_url': 'contrats:ajouter_moto',
    }

    return render(request, template_name, context)






