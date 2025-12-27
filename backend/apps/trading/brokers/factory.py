"""
Broker Factory - Factory pattern for creating broker instances.

This module provides a centralized way to create broker instances
based on broker type, ensuring consistent initialization.
"""
from typing import Dict, Any, Type, Optional, List
import logging

from .base import BrokerBase, BrokerError
from .saxo import SaxoBroker
from .binance import BinanceBroker

logger = logging.getLogger('trading.brokers.factory')


class BrokerNotSupportedError(BrokerError):
    """Raised when broker type is not supported."""
    pass


class BrokerFactory:
    """
    Factory for creating broker instances.
    
    Usage:
        broker = BrokerFactory.create_broker('saxo', user, credentials)
        broker = BrokerFactory.create_broker('binance', user, {'api_key': '...', 'api_secret': '...'})
    """
    
    # Registry of supported brokers
    _brokers: Dict[str, Type[BrokerBase]] = {
        'saxo': SaxoBroker,
        'saxobank': SaxoBroker,
        'binance': BinanceBroker,
    }
    
    # Broker display names
    _broker_names: Dict[str, str] = {
        'saxo': 'Saxo Bank',
        'saxobank': 'Saxo Bank',
        'binance': 'Binance',
    }
    
    @classmethod
    def create_broker(
        cls,
        broker_type: str,
        user,
        credentials: Dict[str, Any]
    ) -> BrokerBase:
        """
        Create a broker instance.
        
        Args:
            broker_type: Type of broker ('saxo', 'binance', etc.)
            user: Django User instance
            credentials: Dictionary of credentials
            
        Returns:
            BrokerBase instance
            
        Raises:
            BrokerNotSupportedError: If broker type is not supported
        """
        broker_key = broker_type.lower().replace(' ', '').replace('-', '').replace('_', '')
        
        broker_class = cls._brokers.get(broker_key)
        if not broker_class:
            supported = ', '.join(cls.get_supported_brokers())
            raise BrokerNotSupportedError(
                f"Broker type '{broker_type}' is not supported. "
                f"Supported brokers: {supported}"
            )
        
        logger.info(f"Creating broker instance: {broker_type} for user {user.id}")
        return broker_class(user, credentials)
    
    @classmethod
    def get_supported_brokers(cls) -> List[str]:
        """
        Get list of supported broker types.
        
        Returns:
            List of broker type names
        """
        # Return unique broker types
        return list(set([
            cls._broker_names.get(key, key)
            for key in cls._brokers.keys()
        ]))
    
    @classmethod
    def is_supported(cls, broker_type: str) -> bool:
        """
        Check if a broker type is supported.
        
        Args:
            broker_type: Type of broker
            
        Returns:
            True if supported
        """
        broker_key = broker_type.lower().replace(' ', '').replace('-', '').replace('_', '')
        return broker_key in cls._brokers
    
    @classmethod
    def register_broker(
        cls,
        broker_type: str,
        broker_class: Type[BrokerBase],
        display_name: Optional[str] = None
    ) -> None:
        """
        Register a new broker type.
        
        Args:
            broker_type: Type identifier
            broker_class: Broker class (must extend BrokerBase)
            display_name: Display name for the broker
        """
        if not issubclass(broker_class, BrokerBase):
            raise ValueError("broker_class must extend BrokerBase")
        
        broker_key = broker_type.lower().replace(' ', '').replace('-', '').replace('_', '')
        cls._brokers[broker_key] = broker_class
        cls._broker_names[broker_key] = display_name or broker_type
        
        logger.info(f"Registered new broker: {broker_type}")
    
    @classmethod
    def get_broker_info(cls, broker_type: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a broker type.
        
        Args:
            broker_type: Type of broker
            
        Returns:
            Dict with broker info or None if not supported
        """
        broker_key = broker_type.lower().replace(' ', '').replace('-', '').replace('_', '')
        broker_class = cls._brokers.get(broker_key)
        
        if not broker_class:
            return None
        
        return {
            'type': broker_key,
            'name': cls._broker_names.get(broker_key, broker_key),
            'class': broker_class.__name__,
            'broker_type_constant': getattr(broker_class, 'BROKER_TYPE', 'unknown'),
        }

