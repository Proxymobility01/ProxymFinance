# dashboard/urls.py

from django.urls import path
from .views import (
    DashboardView,
    StationDashboardView,
    OperationsDashboardView,
    LeasesDashboardView,
    AdminDashboardView
)

app_name = 'dashboard'

urlpatterns = [
    # Dashboard principal
    path('', DashboardView.as_view(), name='index'),

    # Dashboards spécialisés par rôle
    path('station/', StationDashboardView.as_view(), name='station'),
    path('operations/', OperationsDashboardView.as_view(), name='operations'),
    path('leases/', LeasesDashboardView.as_view(), name='leases'),
    path('admin/', AdminDashboardView.as_view(), name='admin'),
]