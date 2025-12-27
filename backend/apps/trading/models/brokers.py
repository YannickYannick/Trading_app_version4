"""
Modèles liés aux brokers et connexions API.
"""
from django.db import models
from django.contrib.auth.models import User
from .base import TimeStampedModel


class Broker(TimeStampedModel):
    """Broker (courtier) supporté."""
    
    class BrokerType(models.TextChoices):
        SAXO = 'SAXO', 'Saxo Bank'
        BINANCE = 'BINANCE', 'Binance'
        INTERACTIVE_BROKERS = 'IB', 'Interactive Brokers'
        OTHER = 'OTHER', 'Autre'
    
    name = models.CharField(max_length=100)
    broker_type = models.CharField(
        max_length=20, choices=BrokerType.choices
    )
    
    # Configuration API
    api_base_url = models.URLField(blank=True)
    api_version = models.CharField(max_length=20, blank=True)
    
    is_active = models.BooleanField(default=True)
    supports_stocks = models.BooleanField(default=True)
    supports_crypto = models.BooleanField(default=False)
    supports_forex = models.BooleanField(default=False)
    supports_futures = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Broker'
        verbose_name_plural = 'Brokers'
    
    def __str__(self):
        return self.name


class BrokerAccount(TimeStampedModel):
    """Compte utilisateur chez un broker."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='broker_accounts'
    )
    broker = models.ForeignKey(
        Broker, on_delete=models.CASCADE, related_name='accounts'
    )
    
    account_id = models.CharField(max_length=100)
    account_name = models.CharField(max_length=100, blank=True)
    
    # Tokens API (chiffrés en production)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Balance
    balance = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=10, default='EUR')
    balance_updated_at = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['user', 'broker', 'account_id']
        ordering = ['broker__name']
        verbose_name = 'Broker Account'
        verbose_name_plural = 'Broker Accounts'
    
    def __str__(self):
        return f"{self.user.username} - {self.broker.name} ({self.account_id})"


class BrokerSyncLog(TimeStampedModel):
    """Log de synchronisation avec un broker."""
    
    class SyncType(models.TextChoices):
        POSITIONS = 'POSITIONS', 'Positions'
        TRADES = 'TRADES', 'Trades'
        ORDERS = 'ORDERS', 'Ordres'
        BALANCE = 'BALANCE', 'Balance'
        ASSETS = 'ASSETS', 'Assets'
        PRICES = 'PRICES', 'Prix'
    
    class SyncStatus(models.TextChoices):
        SUCCESS = 'SUCCESS', 'Succès'
        PARTIAL = 'PARTIAL', 'Partiel'
        FAILED = 'FAILED', 'Échec'
    
    broker_account = models.ForeignKey(
        BrokerAccount, on_delete=models.CASCADE, related_name='sync_logs'
    )
    sync_type = models.CharField(max_length=20, choices=SyncType.choices)
    status = models.CharField(max_length=20, choices=SyncStatus.choices)
    
    items_synced = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        verbose_name = 'Broker Sync Log'
        verbose_name_plural = 'Broker Sync Logs'
    
    def __str__(self):
        return f"{self.broker_account} - {self.sync_type} ({self.status})"

