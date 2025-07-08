from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView



urlpatterns = [
    path('', RedirectView.as_view(url='/login/', permanent=False)),

    path('dashboard/', include('dashboard.urls')),
    path('', include('authentication.urls')),
    path('contrats/', include('contrats.urls', namespace='contrats')),
    path('payments/', include('payments.urls', namespace='payments')),
    path('stations/', include('stations.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
