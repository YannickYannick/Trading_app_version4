"""
Error handling utilities and decorators.

Provides decorators and functions for consistent error handling
across the trading application.
"""
import time
import logging
from typing import Callable, Any, Optional, Type
from functools import wraps

import requests
from rest_framework.views import exception_handler
from rest_framework.response import Response

from ..exceptions.base import TradingAppException
from ..exceptions.broker_exceptions import (
    BrokerException,
    BrokerConnectionError,
    BrokerAPIError,
    BrokerRateLimitError,
)

logger = logging.getLogger('trading.utils.errors')


def handle_broker_errors(broker_type: str):
    """
    Decorator to handle broker-specific errors.
    
    Catches common request exceptions and converts them to
    appropriate BrokerException subclasses.
    
    Usage:
        @handle_broker_errors('saxo')
        def fetch_data():
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
    
    Args:
        broker_type: The broker identifier (e.g., 'saxo', 'binance')
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            
            except requests.exceptions.Timeout as e:
                raise BrokerConnectionError(
                    broker_type=broker_type,
                    message=f"Request timeout in {func.__name__}",
                    timeout=getattr(e, 'timeout', None)
                )
            
            except requests.exceptions.ConnectionError:
                raise BrokerConnectionError(
                    broker_type=broker_type,
                    message=f"Connection error in {func.__name__}"
                )
            
            except requests.exceptions.HTTPError as e:
                response = e.response
                status_code = response.status_code if response else None
                
                if status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    raise BrokerRateLimitError(
                        broker_type=broker_type,
                        retry_after=retry_after
                    )
                
                raise BrokerAPIError(
                    broker_type=broker_type,
                    status_code=status_code,
                    response=response.text if response else None,
                    endpoint=func.__name__
                )
            
            except TradingAppException:
                # Re-raise trading app exceptions
                raise
            
            except Exception as e:
                logger.error(
                    f"Unexpected error in {func.__name__}: {e}",
                    exc_info=True
                )
                raise BrokerException(
                    message=f"Unexpected error in {func.__name__}: {str(e)}",
                    broker_type=broker_type
                )
        
        return wrapper
    return decorator


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator to retry a function on error with exponential backoff.
    
    Usage:
        @retry_on_error(max_retries=3, delay=1, exceptions=(ConnectionError,))
        def fetch_data():
            return requests.get(url).json()
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Factor to multiply delay after each retry
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Optional callback called on each retry (attempt, exception)
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        # Log retry
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        
                        # Call retry callback if provided
                        if on_retry:
                            on_retry(attempt + 1, e)
                        
                        # Wait before retry
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}"
                        )
            
            # All retries failed
            raise last_exception
        
        return wrapper
    return decorator


def log_execution_time(func: Callable) -> Callable:
    """
    Decorator to log function execution time.
    
    Usage:
        @log_execution_time
        def slow_function():
            time.sleep(2)
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            
            duration = time.time() - start_time
            logger.info(
                f"{func.__name__} completed in {duration:.3f}s"
            )
            
            return result
        
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"{func.__name__} failed after {duration:.3f}s: {e}"
            )
            raise
    
    return wrapper


def custom_exception_handler(exc, context):
    """
    Custom exception handler for Django REST Framework.
    
    Converts TradingAppException to consistent API responses
    while still using DRF's built-in handling for other errors.
    
    Configuration (settings.py):
        REST_FRAMEWORK = {
            'EXCEPTION_HANDLER': 'apps.trading.utils.error_utils.custom_exception_handler',
        }
    
    Args:
        exc: The exception
        context: DRF context (view, request, etc.)
        
    Returns:
        Response or None
    """
    # Handle TradingAppException
    if isinstance(exc, TradingAppException):
        logger.warning(
            f"API Exception: {exc.message}",
            extra={
                'code': exc.code,
                'details': exc.details,
                'view': context.get('view').__class__.__name__ if context.get('view') else None,
            }
        )
        
        return Response(
            exc.to_dict(),
            status=getattr(exc, 'http_status_code', 500)
        )
    
    # Use default DRF handler for other exceptions
    response = exception_handler(exc, context)
    
    if response is not None:
        # Wrap DRF errors in consistent format
        error_data = {
            'error': str(response.data.get('detail', response.data)),
            'code': 'DRF_ERROR',
            'details': response.data if isinstance(response.data, dict) else {'data': response.data}
        }
        response.data = error_data
    
    return response


class ErrorContext:
    """
    Context manager for handling errors in a block of code.
    
    Usage:
        with ErrorContext(sync_type='assets', broker_type='saxo') as ctx:
            # Do something that might fail
            result = sync_assets()
            ctx.add_success('assets_synced', 100)
        
        if ctx.has_errors:
            handle_errors(ctx.errors)
    """
    
    def __init__(
        self,
        reraise: bool = True,
        log_errors: bool = True,
        **context
    ):
        """
        Initialize error context.
        
        Args:
            reraise: Whether to re-raise caught exceptions
            log_errors: Whether to log errors automatically
            **context: Additional context for logging
        """
        self.reraise = reraise
        self.log_errors = log_errors
        self.context = context
        self.errors = []
        self.successes = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self.add_error(exc_val)
            
            if self.log_errors:
                logger.error(
                    f"Error in context: {exc_val}",
                    extra=self.context,
                    exc_info=True
                )
            
            return not self.reraise
        return False
    
    def add_error(self, error: Exception, key: str = None):
        """Add an error to the context."""
        self.errors.append({
            'key': key,
            'error': str(error),
            'type': type(error).__name__,
        })
    
    def add_success(self, key: str, value: Any = None):
        """Add a success to the context."""
        self.successes.append({
            'key': key,
            'value': value,
        })
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    def get_summary(self) -> dict:
        """Get summary of the context."""
        return {
            'success': not self.has_errors,
            'errors': self.errors,
            'successes': self.successes,
            **self.context
        }

