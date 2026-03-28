"""
URLs pour l'authentification JWT.
"""
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    # POST /api/auth/jwt/login/ - Obtenir access + refresh tokens
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    
    # POST /api/auth/jwt/refresh/ - Rafraîchir l'access token
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # POST /api/auth/jwt/verify/ - Vérifier la validité d'un token
    path('verify/', TokenVerifyView.as_view(), name='token_verify'),
]
