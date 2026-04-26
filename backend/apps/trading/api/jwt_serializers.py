"""
Sérialiseurs JWT — cas limites (utilisateur absent en base).
"""
from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenRefreshSerializer


class SafeTokenRefreshSerializer(TokenRefreshSerializer):
    """
    Évite un 500 sur POST /api/auth/jwt/refresh/ lorsque le payload du refresh
    référence un utilisateur inexistant (base vidée, changement SQLite/Postgres,
    compte supprimé, etc.). Le client recevra 401 et pourra effacer ses tokens.
    """

    def validate(self, attrs):
        User = get_user_model()
        try:
            return super().validate(attrs)
        except User.DoesNotExist:
            raise AuthenticationFailed(
                self.error_messages["no_active_account"],
                "no_active_account",
            )
