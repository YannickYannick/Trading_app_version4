"""
Brokers module - Abstraction layer for broker APIs.

Usage:
    from apps.trading.brokers import BrokerFactory, BrokerBase
    
    broker = BrokerFactory.create_broker('saxo', user, credentials)
    assets = broker.get_assets(asset_type='Stock', keywords='AAPL')
"""
from .base import BrokerBase
from .factory import BrokerFactory
from .saxo import SaxoBroker
from .binance import BinanceBroker

__all__ = [
    'BrokerBase',
    'BrokerFactory',
    'SaxoBroker',
    'BinanceBroker',
]

