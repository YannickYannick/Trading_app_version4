"""
Base exceptions for the trading application.

All custom exceptions inherit from TradingAppException,
providing consistent error handling and serialization.
"""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger('trading.exceptions')


class TradingAppException(Exception):
    """
    Base exception for all trading application errors.
    
    Provides:
    - Consistent error structure
    - Serialization to dict/JSON
    - Logging integration
    - HTTP status code mapping
    
    Usage:
        raise TradingAppException(
            message="Something went wrong",
            code="CUSTOM_ERROR",
            details={'key': 'value'}
        )
    """
    
    # Default HTTP status code for this exception
    http_status_code: int = 500
    
    def __init__(
        self,
        message: str,
        code: str = 'GENERAL_ERROR',
        details: Optional[Dict[str, Any]] = None,
        log_error: bool = True
    ):
        """
        Initialize the exception.
        
        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
            log_error: Whether to log the error automatically
        """
        self.message = message
        self.code = code
        self.details = details or {}
        
        super().__init__(self.message)
        
        if log_error:
            logger.warning(
                f"[{self.code}] {self.message}",
                extra={'details': self.details}
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for API responses.
        
        Returns:
            Dict with error, code, and details
        """
        return {
            'error': self.message,
            'code': self.code,
            'details': self.details
        }
    
    def __str__(self) -> str:
        """String representation of the exception."""
        return f"[{self.code}] {self.message}"
    
    def __repr__(self) -> str:
        """Debug representation of the exception."""
        return f"{self.__class__.__name__}(message='{self.message}', code='{self.code}')"


class ValidationError(TradingAppException):
    """
    Raised when data validation fails.
    
    Usage:
        raise ValidationError("Invalid email format", field="email")
    """
    
    http_status_code = 400
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if field:
            details['field'] = field
        super().__init__(
            message=message,
            code='VALIDATION_ERROR',
            details=details,
            **kwargs
        )


class NotFoundError(TradingAppException):
    """
    Raised when a requested resource is not found.
    
    Usage:
        raise NotFoundError("Asset", identifier="AAPL")
    """
    
    http_status_code = 404
    
    def __init__(
        self,
        resource: str,
        identifier: Optional[str] = None,
        **kwargs
    ):
        message = f"{resource} not found"
        if identifier:
            message += f" (id: {identifier})"
        
        details = kwargs.pop('details', {})
        details['resource'] = resource
        if identifier:
            details['identifier'] = identifier
        
        super().__init__(
            message=message,
            code='NOT_FOUND',
            details=details,
            **kwargs
        )


class AuthenticationError(TradingAppException):
    """
    Raised when authentication fails.
    
    Usage:
        raise AuthenticationError("Invalid token")
    """
    
    http_status_code = 401
    
    def __init__(
        self,
        message: str = "Authentication failed",
        **kwargs
    ):
        super().__init__(
            message=message,
            code='AUTH_ERROR',
            **kwargs
        )


class PermissionDeniedError(TradingAppException):
    """
    Raised when user lacks required permissions.
    
    Usage:
        raise PermissionDeniedError("Cannot delete this resource")
    """
    
    http_status_code = 403
    
    def __init__(
        self,
        message: str = "Permission denied",
        required_permission: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if required_permission:
            details['required_permission'] = required_permission
        
        super().__init__(
            message=message,
            code='PERMISSION_DENIED',
            details=details,
            **kwargs
        )


class ConfigurationError(TradingAppException):
    """
    Raised when there's a configuration problem.
    
    Usage:
        raise ConfigurationError("Missing API key for Saxo")
    """
    
    http_status_code = 500
    
    def __init__(
        self,
        message: str,
        setting: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if setting:
            details['setting'] = setting
        
        super().__init__(
            message=message,
            code='CONFIGURATION_ERROR',
            details=details,
            **kwargs
        )

