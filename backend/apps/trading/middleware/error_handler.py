"""
Error Handler Middleware for unified error handling.

This middleware catches all exceptions and converts them to
consistent JSON responses with proper HTTP status codes.
"""
import logging
import traceback
from typing import Optional
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from ..exceptions.base import TradingAppException

logger = logging.getLogger('trading.middleware.errors')


class ErrorHandlerMiddleware(MiddlewareMixin):
    """
    Middleware for unified error handling.
    
    Catches all exceptions and converts them to consistent
    JSON responses with proper HTTP status codes.
    
    Features:
    - Converts TradingAppException to structured JSON
    - Logs all errors with context
    - Shows detailed errors in DEBUG mode
    - Hides internal errors in production
    """
    
    # HTTP status code to error code mapping
    STATUS_CODE_MAP = {
        'VALIDATION_ERROR': 400,
        'AUTH_ERROR': 401,
        'BROKER_AUTH_ERROR': 401,
        'BROKER_TOKEN_EXPIRED': 401,
        'SYNC_AUTH_ERROR': 401,
        'PERMISSION_DENIED': 403,
        'NOT_FOUND': 404,
        'SYNC_DATA_ERROR': 422,
        'BROKER_RATE_LIMIT': 429,
        'BROKER_INSUFFICIENT_FUNDS': 400,
        'BROKER_ORDER_REJECTED': 400,
        'GENERAL_ERROR': 500,
        'CONFIGURATION_ERROR': 500,
        'SYNC_ERROR': 500,
        'BROKER_ERROR': 502,
        'BROKER_API_ERROR': 502,
        'BROKER_CONNECTION_ERROR': 503,
        'SYNC_TIMEOUT': 504,
        'SYNC_PARTIAL_ERROR': 207,
    }
    
    def process_exception(
        self,
        request: HttpRequest,
        exception: Exception
    ) -> Optional[HttpResponse]:
        """
        Process an exception and return appropriate response.
        
        Args:
            request: The HTTP request
            exception: The raised exception
            
        Returns:
            JsonResponse with error details, or None to continue
        """
        # Get request context for logging
        context = self._get_request_context(request)
        
        # Handle TradingAppException
        if isinstance(exception, TradingAppException):
            return self._handle_trading_exception(exception, context)
        
        # Handle other exceptions
        return self._handle_generic_exception(exception, context)
    
    def _handle_trading_exception(
        self,
        exception: TradingAppException,
        context: dict
    ) -> JsonResponse:
        """
        Handle TradingAppException.
        
        Args:
            exception: The trading app exception
            context: Request context for logging
            
        Returns:
            JsonResponse with error details
        """
        # Log the error
        logger.warning(
            f"TradingAppException: {exception.message}",
            extra={
                'code': exception.code,
                'details': exception.details,
                **context
            }
        )
        
        # Get appropriate status code
        status_code = self.STATUS_CODE_MAP.get(
            exception.code,
            getattr(exception, 'http_status_code', 500)
        )
        
        return JsonResponse(
            exception.to_dict(),
            status=status_code
        )
    
    def _handle_generic_exception(
        self,
        exception: Exception,
        context: dict
    ) -> JsonResponse:
        """
        Handle generic (non-TradingApp) exceptions.
        
        Args:
            exception: The exception
            context: Request context for logging
            
        Returns:
            JsonResponse with error details
        """
        # Log the full exception with traceback
        logger.error(
            f"Unhandled exception: {str(exception)}",
            extra={
                **context,
                'exception_type': type(exception).__name__,
                'traceback': traceback.format_exc()
            },
            exc_info=True
        )
        
        # In DEBUG mode, show detailed error
        if settings.DEBUG:
            return JsonResponse({
                'error': str(exception),
                'code': 'INTERNAL_ERROR',
                'exception_type': type(exception).__name__,
                'traceback': traceback.format_exc().split('\n')
            }, status=500)
        
        # In production, hide internal details
        return JsonResponse({
            'error': 'An internal error occurred. Please try again later.',
            'code': 'INTERNAL_ERROR'
        }, status=500)
    
    def _get_request_context(self, request: HttpRequest) -> dict:
        """
        Extract context from request for logging.
        
        Args:
            request: The HTTP request
            
        Returns:
            Dict with request context
        """
        context = {
            'path': request.path,
            'method': request.method,
            'user_id': getattr(request.user, 'id', None),
        }
        
        # Add query params if present
        if request.GET:
            context['query_params'] = dict(request.GET)
        
        # Add IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            context['ip_address'] = x_forwarded_for.split(',')[0]
        else:
            context['ip_address'] = request.META.get('REMOTE_ADDR')
        
        return context

