# authentication/views.py

from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.models import update_last_login
from django.contrib.auth import login as django_login

import bcrypt
from django.contrib.auth import login as django_login, logout
from .forms import LoginForm, ForgotPasswordForm, RegistrationForm
from .models import Employe, RoleFinance, EmployeRoleFinance


class LoginView(View):
    """
    Vue pour la page de connexion.
    """
    template_name = 'authentication/login.html'

    def get(self, request):
        # Si l'utilisateur est déjà connecté, le rediriger vers le dashboard
        if 'user_id' in request.session and 'user_type' in request.session:
            return redirect('dashboard:index')

        form = LoginForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = LoginForm(request.POST)

        if form.is_valid():
            # Les vérifications d'authentification sont déjà faites dans le formulaire
            user_type = form.user_type
            user_data = form.user_data

            # ───> Désactivation temporaire du signal qui écrit last_login
            user_logged_in.disconnect(update_last_login)

            # On “log in” l’utilisateur sans provoquer d’update_last_login()
            django_login(request, user_data)
            request.session['user_id'] = user_data.pk

            # (Optionnel) Si vous voulez remettre le signal pour d’autres logins:
            user_logged_in.connect(update_last_login)

            # 💾 Conservez ici seulement ce que vous voulez en session
            request.session['user_type'] = user_type
            # Si c'est un employé, récupérer son rôle financier pour la redirection
            if user_type == 'employe':
                try:
                    employe_role = EmployeRoleFinance.objects.get(employe=user_data)
                    role = employe_role.role_finance
                    request.session['user_role'] = role.title

                    # Rediriger vers différentes pages selon le rôle
                    if role.title == 'Gestionnaire de Station':
                        return redirect('station:index')
                    elif role.title == 'Gestionnaire des Opérations':
                        return redirect('rapports:index')
                    elif role.title == 'Responsable des Leases':
                        return redirect('investisseurs:index')
                    elif role.title == 'Manager Financier':
                        return redirect('dashboard:admin')

                except EmployeRoleFinance.DoesNotExist:
                    # Si l'employé n'a pas de rôle spécifique, rediriger vers le dashboard général
                    pass

            # Pour les autres types d'utilisateurs ou si pas de rôle spécifique
            return redirect('dashboard:index')

        return render(request, self.template_name, {'form': form})


class LogoutView(View):
    """
    Vue pour la déconnexion.
    """

    def get(self, request):
        # Supprimer toutes les données de session
        request.session.flush()
        return redirect('authentication:login')


class ForgotPasswordView(View):
    """
    Vue pour la réinitialisation de mot de passe (modal).
    """

    def post(self, request):
        form = ForgotPasswordForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data['email']
            # Ici, vous implémenteriez la logique d'envoi d'email pour réinitialiser le mot de passe
            # Pour l'instant, on simule juste un succès
            messages.success(request, f"Un lien de réinitialisation a été envoyé à {email}")
            return redirect('authentication:login')

        # Si le formulaire n'est pas valide, retourner à la page de connexion avec des erreurs
        messages.error(request, "Veuillez fournir une adresse email valide.")
        return redirect('authentication:login')


class RegisterView(View):
    """
    Vue pour la page d'enregistrement.
    """
    template_name = 'authentication/register.html'

    def get(self, request):
        form = RegistrationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = RegistrationForm(request.POST)

        if form.is_valid():
            employe = form.save()
            messages.success(request, "Votre compte a été créé avec succès. Vous pouvez maintenant vous connecter.")
            return redirect('authentication:login')

        return render(request, self.template_name, {'form': form})


# Middleware pour vérifier l'authentification
# authentication/middleware.py (ou où se trouve votre AuthRequiredMiddleware)

class AuthRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_paths = (
            '/login/',
            '/logout/',
            '/admin/',
            '/register/',
            '/forgot-password/',
            '/static/',
        )

    def __call__(self, request):
        # Auth custom : on vérifie si user_id est en session
        if not request.path_info.startswith(self.exempt_paths):
            if not request.session.get('user_id') or not request.session.get('user_type'):
                return redirect('authentication:login')
        return self.get_response(request)






