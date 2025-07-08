# dashboard/views.py

from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages


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

        context = {
            'user_id': user_id,
            'user_name': user_name,
            'user_type': user_type,
            'user_role': user_role,
            'page_title': 'Tableau de bord',
        }

        return render(request, self.template_name, context)


class AdminDashboardView(View):
    """
    Vue pour le tableau de bord administratif.
    """
    template_name = 'dashboard/admin.html'

    def get(self, request):
        # Vérifier si l'utilisateur est connecté et a le rôle approprié
        if 'user_id' not in request.session:
            return redirect('authentication:login')

        user_role = request.session.get('user_role', '')
        if user_role != 'Manager Financier':
            messages.error(request, "Vous n'avez pas les droits nécessaires pour accéder à cette page.")
            return redirect('dashboard:index')

        context = {
            'user_name': request.session.get('user_name'),
            'user_role': user_role,
            'page_title': 'Administration Financière',
        }

        return render(request, self.template_name, context)