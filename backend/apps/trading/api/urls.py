"""
URLs de l'API REST Trading.

Configuration des routes API avec DefaultRouter.

Le router génère automatiquement ces URLs pour chaque ViewSet :
- GET    /endpoint/          → list() - Liste tous les objets
- POST   /endpoint/          → create() - Crée un objet
- GET    /endpoint/{id}/     → retrieve() - Détails d'un objet
- PUT    /endpoint/{id}/     → update() - Met à jour un objet
- PATCH  /endpoint/{id}/     → partial_update() - Met à jour partiellement
- DELETE /endpoint/{id}/     → destroy() - Supprime un objet

Les @action décorées créent des endpoints supplémentaires :
- detail=True  → /endpoint/{id}/action_name/
- detail=False → /endpoint/action_name/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from . import views
from . import auth_views
from .health import health_check, ping

# ============================================
# ROUTER PRINCIPAL
# ============================================

router = DefaultRouter()

# --------------------------------------------
# CATALOGUE UNIVERSEL (AllAssets)
# Endpoints :
#   GET  /all-assets/           → Liste le catalogue
#   GET  /all-assets/{id}/      → Détails d'un asset
#   GET  /all-assets/saxo/      → Assets Saxo uniquement
#   GET  /all-assets/binance/   → Assets Binance uniquement
#   GET  /all-assets/stats/     → Statistiques du catalogue
#   GET  /all-assets/search/    → Recherche avancée
# --------------------------------------------
router.register(r'all-assets', views.AllAssetsViewSet, basename='all-asset')

# --------------------------------------------
# ASSETS ENRICHIS
# Endpoints :
#   CRUD /assets/               → CRUD standard
#   GET  /assets/{id}/prices/   → Historique des prix
#   GET  /assets/{id}/positions/→ Positions sur l'asset
#   GET  /assets/{id}/trades/   → Trades sur l'asset
#   GET  /assets/{id}/summary/  → Résumé complet
#   POST /assets/{id}/update_price/ → Met à jour le prix
# --------------------------------------------
router.register(r'assets', views.AssetViewSet, basename='asset')

# --------------------------------------------
# POSITIONS
# Endpoints :
#   CRUD /positions/            → CRUD standard
#   GET  /positions/open/       → Positions ouvertes
#   GET  /positions/closed/     → Positions fermées
#   GET  /positions/summary/    → Résumé du portefeuille
#   GET  /positions/by_broker/  → Groupées par broker
#   POST /positions/{id}/close/ → Fermer une position
# --------------------------------------------
router.register(r'positions', views.PositionViewSet, basename='position')

# --------------------------------------------
# TRADES
# Endpoints :
#   CRUD /trades/               → CRUD standard
#   GET  /trades/recent/        → Trades récents (20)
#   GET  /trades/today/         → Trades du jour
#   GET  /trades/stats/         → Statistiques de trading
#   GET  /trades/by_asset/      → Groupés par asset
# --------------------------------------------
router.register(r'trades', views.TradeViewSet, basename='trade')

# --------------------------------------------
# ORDRES
# Endpoints :
#   CRUD /orders/               → CRUD standard
#   GET  /orders/pending/       → Ordres en attente
#   GET  /orders/filled/        → Ordres exécutés
#   POST /orders/{id}/cancel/   → Annuler un ordre
# --------------------------------------------
router.register(r'orders', views.OrderViewSet, basename='order')

# --------------------------------------------
# STRATEGIES
# Endpoints :
#   CRUD /strategies/                  → CRUD standard
#   GET  /strategies/{id}/performance/ → Performance
#   GET  /strategies/{id}/positions/   → Positions de la stratégie
#   POST /strategies/{id}/activate/    → Activer
#   POST /strategies/{id}/deactivate/  → Désactiver
# --------------------------------------------
router.register(r'strategies', views.StrategyViewSet, basename='strategy')

# --------------------------------------------
# BROKERS
# Endpoints :
#   GET  /brokers/              → Liste des brokers
#   GET  /brokers/{id}/         → Détails d'un broker
# --------------------------------------------
router.register(r'brokers', views.BrokerViewSet, basename='broker')

# --------------------------------------------
# COMPTES BROKER
# Endpoints :
#   CRUD /broker-accounts/                    → CRUD standard
#   GET  /broker-accounts/{id}/sync_status/   → Statut sync
#   POST /broker-accounts/{id}/refresh_balance/ → Rafraîchir balance
# --------------------------------------------
router.register(r'broker-accounts', views.BrokerAccountViewSet, basename='broker-account')


# ============================================
# URLS FINALES
# ============================================

urlpatterns = [
    # ============================================
    # HEALTH CHECK (public, no auth required)
    # ============================================
    path('health/', health_check, name='health-check'),
    path('ping/', ping, name='ping'),
    
    # Toutes les URLs du router (ViewSets)
    path('', include(router.urls)),
    
    # ============================================
    # AUTHENTIFICATION
    # ============================================
    
    # Session Authentication (navigateur)
    path('auth/login/', auth_views.login_session, name='api-login'),
    path('auth/logout/', auth_views.logout_session, name='api-logout'),
    
    # JWT Authentication (apps/API)
    path('auth/jwt/login/', auth_views.login_jwt, name='jwt-login'),
    path('auth/jwt/logout/', auth_views.logout_jwt, name='jwt-logout'),
    path('auth/jwt/refresh/', TokenRefreshView.as_view(), name='jwt-refresh'),
    path('auth/jwt/verify/', TokenVerifyView.as_view(), name='jwt-verify'),
    
    # User
    path('auth/user/', auth_views.user_info, name='api-user'),
    path('auth/register/', auth_views.register, name='api-register'),
]
