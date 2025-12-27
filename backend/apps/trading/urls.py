"""
URLs pour l'application Trading.

Structure :
- config_django/urls.py → path('api/', include('apps.trading.urls'))
- apps/trading/urls.py  → path('', include('apps.trading.api.urls'))
- apps/trading/api/urls.py → router.urls

Résultat final : /api/assets/, /api/positions/, etc.
"""
from django.urls import path, include

app_name = 'trading'

urlpatterns = [
    # API REST (toutes les routes DRF)
    # Note: Pas de préfixe ici car déjà sous /api/ dans config_django/urls.py
    path('', include('apps.trading.api.urls')),
    
    # Vues web traditionnelles (templates Django - futures)
    # path('dashboard/', views.dashboard, name='dashboard'),
    # path('portfolio/', views.portfolio, name='portfolio'),
]
