"""
Utilitaires pour la gestion des utilisateurs dans les commandes management.
"""
from django.core.management.base import CommandError
from django.contrib.auth.models import User
from apps.trading.models import BrokerAccount


def get_user_or_error(user_id: int) -> User:
    """
    Récupère un utilisateur par ID ou lève CommandError.
    
    Args:
        user_id: ID de l'utilisateur
        
    Returns:
        Instance User
        
    Raises:
        CommandError: Si l'utilisateur n'existe pas
    """
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise CommandError(f"User with ID {user_id} does not exist")


def get_broker_account_or_error(account_id: int) -> BrokerAccount:
    """
    Récupère un compte broker par ID ou lève CommandError.
    
    Args:
        account_id: ID du compte broker
        
    Returns:
        Instance BrokerAccount
        
    Raises:
        CommandError: Si le compte n'existe pas
    """
    try:
        return BrokerAccount.objects.get(id=account_id)
    except BrokerAccount.DoesNotExist:
        raise CommandError(f"BrokerAccount with ID {account_id} does not exist")


