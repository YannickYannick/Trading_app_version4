"""
Custom exceptions for the trading application.

Usage:
    from apps.trading.exceptions import (
        TradingAppException,
        BrokerAuthenticationError,
        SyncTimeoutError,
    )
"""
from .base import (
    TradingAppException,
    ValidationError,
    NotFoundError,
    AuthenticationError,
    PermissionDeniedError,
    ConfigurationError,
)
from .broker_exceptions import (
    BrokerException,
    BrokerAuthenticationError,
    BrokerConnectionError,
    BrokerAPIError,
    BrokerRateLimitError,
    BrokerTokenExpiredError,
    BrokerInsufficientFundsError,
    BrokerOrderRejectedError,
)
from .sync_exceptions import (
    SyncException,
    SyncTimeoutError,
    SyncPartialError,
    SyncAuthenticationError,
    SyncDataError,
)

__all__ = [
    # Base exceptions
    'TradingAppException',
    'ValidationError',
    'NotFoundError',
    'AuthenticationError',
    'PermissionDeniedError',
    'ConfigurationError',
    # Broker exceptions
    'BrokerException',
    'BrokerAuthenticationError',
    'BrokerConnectionError',
    'BrokerAPIError',
    'BrokerRateLimitError',
    'BrokerTokenExpiredError',
    'BrokerInsufficientFundsError',
    'BrokerOrderRejectedError',
    # Sync exceptions
    'SyncException',
    'SyncTimeoutError',
    'SyncPartialError',
    'SyncAuthenticationError',
    'SyncDataError',
]

