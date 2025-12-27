"""
Data Providers module.

This module contains integrations with external data providers
like Yahoo Finance for enriched market data.
"""
from .yahoo_finance import YahooFinanceService

__all__ = [
    'YahooFinanceService',
]

