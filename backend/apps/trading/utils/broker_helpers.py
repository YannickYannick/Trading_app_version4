"""
Utilitaires pour travailler avec les brokers.
"""
from typing import Optional
from ..models.brokers import BrokerAccount


def get_broker_type_safe(broker_account: BrokerAccount) -> str:
    """
    Récupère le broker_type de manière sécurisée.
    Utilise le champ broker_type directement, ou fallback sur broker.broker_type.
    
    Args:
        broker_account: Instance de BrokerAccount
        
    Returns:
        Type de broker (SAXO, BINANCE, etc.)
    """
    if broker_account.broker_type:
        return broker_account.broker_type
    elif broker_account.broker and broker_account.broker.broker_type:
        # Mettre à jour le champ pour éviter de refaire cette vérification
        broker_account.broker_type = broker_account.broker.broker_type
        broker_account.save(update_fields=['broker_type'])
        return broker_account.broker_type
    else:
        return 'OTHER'

