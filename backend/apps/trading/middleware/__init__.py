"""
Middleware for the trading application.
"""
from .error_handler import ErrorHandlerMiddleware

__all__ = [
    'ErrorHandlerMiddleware',
]

