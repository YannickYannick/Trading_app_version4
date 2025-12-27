"""
Synchronization-specific exceptions for the trading application.

These exceptions handle errors related to data synchronization operations.
"""
from typing import Optional, List, Dict, Any
from .base import TradingAppException


class SyncException(TradingAppException):
    """
    Base exception for all synchronization-related errors.
    
    Usage:
        raise SyncException("Sync failed", sync_type="assets")
    """
    
    http_status_code = 500
    
    def __init__(
        self,
        message: str,
        sync_type: Optional[str] = None,
        code: str = 'SYNC_ERROR',
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if sync_type:
            details['sync_type'] = sync_type
        
        self.sync_type = sync_type
        
        super().__init__(
            message=message,
            code=code,
            details=details,
            **kwargs
        )


class SyncTimeoutError(SyncException):
    """
    Raised when synchronization times out.
    
    Usage:
        raise SyncTimeoutError("positions", timeout=30)
    """
    
    http_status_code = 504  # Gateway Timeout
    
    def __init__(
        self,
        sync_type: str,
        timeout: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if timeout:
            details['timeout_seconds'] = timeout
        
        message = f"Synchronization timeout for {sync_type}"
        if timeout:
            message += f" (after {timeout}s)"
        
        self.timeout = timeout
        
        super().__init__(
            message=message,
            sync_type=sync_type,
            code='SYNC_TIMEOUT',
            details=details,
            **kwargs
        )


class SyncPartialError(SyncException):
    """
    Raised when synchronization partially succeeds.
    
    Usage:
        raise SyncPartialError(
            sync_type="assets",
            succeeded=80,
            failed=20,
            errors=[{'symbol': 'XXX', 'error': 'Not found'}]
        )
    """
    
    http_status_code = 207  # Multi-Status
    
    def __init__(
        self,
        sync_type: str,
        succeeded: int,
        failed: int,
        errors: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        details['succeeded'] = succeeded
        details['failed'] = failed
        details['total'] = succeeded + failed
        
        if errors:
            # Limit errors to first 10 for response size
            details['errors'] = errors[:10]
            if len(errors) > 10:
                details['errors_truncated'] = True
                details['total_errors'] = len(errors)
        
        message = f"Partial sync error for {sync_type}: {succeeded} succeeded, {failed} failed"
        
        self.succeeded = succeeded
        self.failed = failed
        self.errors = errors or []
        
        super().__init__(
            message=message,
            sync_type=sync_type,
            code='SYNC_PARTIAL_ERROR',
            details=details,
            **kwargs
        )


class SyncAuthenticationError(SyncException):
    """
    Raised when sync fails due to authentication issues.
    
    Usage:
        raise SyncAuthenticationError("positions", broker_type="saxo")
    """
    
    http_status_code = 401
    
    def __init__(
        self,
        sync_type: str,
        broker_type: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if broker_type:
            details['broker_type'] = broker_type
        
        message = f"Authentication failed during {sync_type} sync"
        if broker_type:
            message += f" with {broker_type}"
        
        super().__init__(
            message=message,
            sync_type=sync_type,
            code='SYNC_AUTH_ERROR',
            details=details,
            **kwargs
        )


class SyncDataError(SyncException):
    """
    Raised when sync fails due to data issues.
    
    Usage:
        raise SyncDataError("trades", reason="Invalid data format")
    """
    
    http_status_code = 422  # Unprocessable Entity
    
    def __init__(
        self,
        sync_type: str,
        reason: Optional[str] = None,
        invalid_records: Optional[List[Dict]] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if reason:
            details['reason'] = reason
        if invalid_records:
            details['invalid_records'] = invalid_records[:5]  # Limit to 5
        
        message = f"Data error during {sync_type} sync"
        if reason:
            message += f": {reason}"
        
        super().__init__(
            message=message,
            sync_type=sync_type,
            code='SYNC_DATA_ERROR',
            details=details,
            **kwargs
        )

