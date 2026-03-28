"""
Configuration des URLs principales du projet Trading App.

Structure des URLs :
==================

/admin/                     → Administration Django
/api/                       → API REST principale
    /api/all-assets/        → Catalogue universel
    /api/assets/            → Assets enrichis
    /api/positions/         → Positions
    /api/trades/            → Trades
    /api/orders/            → Ordres
    /api/strategies/        → Stratégies
    /api/brokers/           → Brokers
    /api/broker-accounts/   → Comptes broker
/api/auth/                  → Authentification DRF (login/logout navigateur)
/api/schema/                → Schéma OpenAPI
/api/docs/                  → Documentation Swagger UI
/api/redoc/                 → Documentation ReDoc
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView, 
    SpectacularSwaggerView, 
    SpectacularRedocView
)

urlpatterns = [
    # ============================================
    # ADMINISTRATION DJANGO
    # ============================================
    path('admin/', admin.site.urls),
    
    # ============================================
    # API REST - APPLICATION TRADING
    # ============================================
    # Inclut tous les endpoints de l'app trading
    # /api/assets/, /api/positions/, /api/trades/, etc.
    path('api/', include('apps.trading.urls')),
    
    # ============================================
    # AUTHENTIFICATION
    # ============================================
    # Interface de login/logout pour l'API navigable DRF
    path('api/auth/', include('rest_framework.urls', namespace='rest_framework')),
    
    # Note: Pour JWT, décommenter après installation de djangorestframework-simplejwt
    # from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
    # path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    # path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # ============================================
    # DOCUMENTATION API (OpenAPI/Swagger)
    # ============================================
    # Schéma OpenAPI (JSON/YAML)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Interface Swagger UI
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # Interface ReDoc (alternative à Swagger)
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # ============================================
    # AUTRES APPLICATIONS (futures)
    # ============================================
    # Décommenter quand les apps seront prêtes
    # path('api/macro/', include('apps.macro_economics.urls')),
    path('api/ai/', include('apps.ai_assistant.api.urls')),
]

# ============================================
# FICHIERS STATIQUES ET MÉDIA (développement)
# ============================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug Toolbar (si installé)
    # import debug_toolbar
    # urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
