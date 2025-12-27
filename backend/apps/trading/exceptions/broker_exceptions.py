"""
Broker-specific exceptions for the trading application.

These exceptions handle errors related to broker API interactions.
"""
from typing import Optional, Dict, Any
from .base import TradingAppException


class BrokerException(TradingAppException):
    """
    Base exception for all broker-related errors.
    
    Usage:
        raise BrokerException("Something went wrong", broker_type="saxo")
    """
    
    http_status_code = 502  # Bad Gateway
    
    def __init__(
        self,
        message: str,
        broker_type: Optional[str] = None,
        code: str = 'BROKER_ERROR',
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if broker_type:
            details['broker_type'] = broker_type
        
        self.broker_type = broker_type
        
        super().__init__(
            message=message,
            code=code,
            details=details,
            **kwargs
        )


class BrokerAuthenticationError(BrokerException):
    """
    Raised when broker authentication fails.
    
    Usage:
        raise BrokerAuthenticationError("saxo", message="Invalid credentials")
    """
    
    http_status_code = 401
    
    def __init__(
        self,
        broker_type: str,
        message: Optional[str] = None,
        **kwargs
    ):
        message = message or f"Authentication failed with {broker_type}"
        super().__init__(
            message=message,
            broker_type=broker_type,
            code='BROKER_AUTH_ERROR',
            **kwargs
        )


class BrokerConnectionError(BrokerException):
    """
    Raised when connection to broker API fails.
    
    Usage:
        raise BrokerConnectionError("binance", message="Connection timeout")
    """
    
    http_status_code = 503  # Service Unavailable
    
    def __init__(
        self,
        broker_type: str,
        message: Optional[str] = None,
        timeout: Optional[int] = None,
        **kwargs
    ):
        message = message or f"Failed to connect to {broker_type}"
        
        details = kwargs.pop('details', {})
        if timeout:
            details['timeout'] = timeout
        
        super().__init__(
            message=message,
            broker_type=broker_type,
            code='BROKER_CONNECTION_ERROR',
            details=details,
            **kwargs
        )


class BrokerAPIError(BrokerException):
    """
    Raised when broker API returns an error.
    
    Usage:
        raise BrokerAPIError("saxo", status_code=400, response="Bad request")
    """
    
    http_status_code = 502  # Bad Gateway
    
    def __init__(
        self,
        broker_type: str,
        status_code: Optional[int] = None,
        response: Optional[str] = None,
        endpoint: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        
        if status_code:
            details['status_code'] = status_code
        if response:
            # Truncate long responses
            details['response'] = response[:500] if len(response) > 500 else response
        if endpoint:
            details['endpoint'] = endpoint
        
        message = f"API error from {broker_type}"
        if status_code:
            message += f" (status: {status_code})"
        
        super().__init__(
            message=message,
            broker_type=broker_type,
            code='BROKER_API_ERROR',
            details=details,
            **kwargs
        )


class BrokerRateLimitError(BrokerException):
    """
    Raised when broker rate limit is exceeded.
    
    Usage:
        raise BrokerRateLimitError("binance", retry_after=60)
    """
    
    http_status_code = 429  # Too Many Requests
    
    def __init__(
        self,
        broker_type: str,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if retry_after:
            details['retry_after'] = retry_after
        
        message = f"Rate limit exceeded for {broker_type}"
        if retry_after:
            message += f" (retry after {retry_after}s)"
        
        self.retry_after = retry_after
        
        super().__init__(
            message=message,
            broker_type=broker_type,
            code='BROKER_RATE_LIMIT',
            details=details,
            **kwargs
        )


class BrokerTokenExpiredError(BrokerException):
    """
    Raised when broker access token has expired.
    
    Usage:
        raise BrokerTokenExpiredError("saxo")
    """
    
    http_status_code = 401
    
    def __init__(
        self,
        broker_type: str,
        can_refresh: bool = False,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        details['can_refresh'] = can_refresh
        
        message = f"Access token expired for {broker_type}"
        
        super().__init__(
            message=message,
            broker_type=broker_type,
            code='BROKER_TOKEN_EXPIRED',
            details=details,
            **kwargs
        )


class BrokerInsufficientFundsError(BrokerException):
    """
    Raised when account has insufficient funds for an operation.
    
    Usage:
        raise BrokerInsufficientFundsError("binance", required=1000, available=500)
    """
    
    http_status_code = 400
    
    def __init__(
        self,
        broker_type: str,
        required: Optional[float] = None,
        available: Optional[float] = None,
        currency: str = 'USD',
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if required:
            details['required'] = required
        if available:
            details['available'] = available
        details['currency'] = currency
        
        message = f"Insufficient funds on {broker_type}"
        if required and available:
            message += f" (required: {required} {currency}, available: {available} {currency})"
        
        super().__init__(
            message=message,
            broker_type=broker_type,
            code='BROKER_INSUFFICIENT_FUNDS',
            details=details,
            **kwargs
        )


class BrokerOrderRejectedError(BrokerException):
    """
    Raised when an order is rejected by the broker.
    
    Usage:
        raise BrokerOrderRejectedError("saxo", reason="Market closed")
    """
    
    http_status_code = 400
    
    def __init__(
        self,
        broker_type: str,
        reason: Optional[str] = None,
        order_details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if reason:
            details['reason'] = reason
        if order_details:
            details['order'] = order_details
        
        message = f"Order rejected by {broker_type}"
        if reason:
            message += f": {reason}"
        
        super().__init__(
            message=message,
            broker_type=broker_type,
            code='BROKER_ORDER_REJECTED',
            details=details,
            **kwargs
        )

