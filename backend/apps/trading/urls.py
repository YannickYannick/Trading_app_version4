"""
URLs pour l'application Trading.
"""
from django.urls import path, include

app_name = 'trading'

urlpatterns = [
    # API REST
    path('api/', include('apps.trading.api.urls')),
    
    # Vues web (à ajouter plus tard)
    # path('', views.home, name='home'),
]
