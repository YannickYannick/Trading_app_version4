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
    
    # API Keys (pour Binance et autres brokers avec clé API)
    api_key = models.CharField(max_length=255, blank=True)
    api_secret = models.CharField(max_length=255, blank=True)
    
    # OAuth credentials (pour Saxo)
    client_id = models.CharField(max_length=255, blank=True)
    client_secret = models.CharField(max_length=255, blank=True)
    
    # Tokens API (chiffrés en production)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Extra credentials (JSON pour données supplémentaires)
    extra_credentials = models.JSONField(default=dict, blank=True)
    
    # Balance
    balance = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=10, default='EUR')
    balance_updated_at = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=False)
    is_sandbox = models.BooleanField(default=True, help_text="Use sandbox/simulation environment")
    
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
        CONNECTION_TEST = 'CONNECTION_TEST', 'Test connexion'
        ORDER_PLACED = 'ORDER_PLACED', 'Ordre placé'
        ORDER_CANCELLED = 'ORDER_CANCELLED', 'Ordre annulé'
    
    class SyncStatus(models.TextChoices):
        SUCCESS = 'SUCCESS', 'Succès'
        PARTIAL = 'PARTIAL', 'Partiel'
        FAILED = 'FAILED', 'Échec'
        ERROR = 'ERROR', 'Erreur'
        WARNING = 'WARNING', 'Avertissement'
    
    broker_account = models.ForeignKey(
        BrokerAccount, on_delete=models.CASCADE, related_name='sync_logs'
    )
    sync_type = models.CharField(max_length=50)  # Allow custom sync types
    status = models.CharField(max_length=20, choices=SyncStatus.choices)
    
    records_synced = models.IntegerField(default=0)
    items_synced = models.IntegerField(default=0)  # Legacy field
    error_message = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Broker Sync Log'
        verbose_name_plural = 'Broker Sync Logs'
    
    def __str__(self):
        return f"{self.broker_account} - {self.sync_type} ({self.status})"

