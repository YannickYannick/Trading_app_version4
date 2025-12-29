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
    """
    Compte utilisateur chez un broker.
    Architecture inspirée de BrokerCredentials de la v3.
    """
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='broker_accounts'
    )
    broker = models.ForeignKey(
        Broker, on_delete=models.CASCADE, related_name='accounts', null=True, blank=True
    )
    
    # Nom pour identifier cette configuration (comme dans v3)
    name = models.CharField(
        max_length=100,
        default='',
        blank=True,
        help_text="Nom pour identifier cette configuration (ex: 'Mon compte Saxo principal')"
    )
    
    # Type de broker (redondant avec broker.broker_type mais utile pour compatibilité v3)
    broker_type = models.CharField(
        max_length=20,
        choices=Broker.BrokerType.choices,
        default=Broker.BrokerType.OTHER,
        help_text="Type de broker (Saxo, Binance, etc.)"
    )
    
    # Environnement de trading
    ENVIRONMENT_CHOICES = [
        ('live', 'Live Trading'),
        ('simulation', 'Simulation/Demo'),
    ]
    environment = models.CharField(
        max_length=20, 
        choices=ENVIRONMENT_CHOICES, 
        default='live',  # ✅ MIGRATION: Défaut changé de 'simulation' vers 'live'
        help_text="Environnement de trading (Live ou Simulation)"
    )
    
    # Account ID (optionnel, pour identifier le compte chez le broker)
    account_id = models.CharField(max_length=100, blank=True, help_text="ID du compte chez le broker")
    
    # ============================================
    # CREDENTIALS SAXO BANK
    # ============================================
    saxo_client_id = models.CharField(max_length=255, blank=True, null=True)
    saxo_client_secret = models.CharField(max_length=255, blank=True, null=True)
    saxo_redirect_uri = models.URLField(blank=True, null=True)
    saxo_environment = models.CharField(
        max_length=20,
        choices=[('live', 'Live'), ('simulation', 'Simulation')],
        default='live',  # ✅ MIGRATION: Défaut changé de 'simulation' vers 'live'
        verbose_name="Environnement Saxo"
    )
    saxo_access_token = models.TextField(blank=True, null=True)
    saxo_refresh_token = models.TextField(blank=True, null=True)
    saxo_token_expires_at = models.DateTimeField(blank=True, null=True)
    
    # ============================================
    # CREDENTIALS BINANCE
    # ============================================
    binance_api_key = models.CharField(max_length=255, blank=True, null=True)
    binance_api_secret = models.CharField(max_length=255, blank=True, null=True)
    binance_testnet = models.BooleanField(default=False)
    
    # ============================================
    # CREDENTIALS GÉNÉRIQUES (pour autres brokers)
    # ============================================
    # API Keys génériques (pour compatibilité avec l'ancien modèle)
    api_key = models.CharField(max_length=255, blank=True)
    api_secret = models.CharField(max_length=255, blank=True)
    client_id = models.CharField(max_length=255, blank=True)
    client_secret = models.CharField(max_length=255, blank=True)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Extra credentials (JSON pour données supplémentaires)
    extra_credentials = models.JSONField(default=dict, blank=True)
    
    # ============================================
    # CONFIGURATION AUTO-REFRESH (Saxo)
    # ============================================
    auto_refresh_enabled = models.BooleanField(
        default=True, 
        verbose_name="Auto-refresh activé",
        help_text="Activer le rafraîchissement automatique des tokens"
    )
    auto_refresh_frequency = models.IntegerField(
        default=45,
        verbose_name="Fréquence auto-refresh (minutes)",
        help_text="Fréquence en minutes (15-55 min)"
    )
    
    # ============================================
    # BALANCE ET STATUT
    # ============================================
    balance = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=10, default='EUR')
    balance_updated_at = models.DateTimeField(null=True, blank=True)
    last_sync = models.DateTimeField(null=True, blank=True, help_text="Dernière synchronisation")
    
    is_active = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=False)
    is_sandbox = models.BooleanField(
        default=True, 
        help_text="Use sandbox/simulation environment"
    )
    
    class Meta:
        unique_together = ['user', 'broker_type', 'name']
        ordering = ['broker_type', 'name']
        verbose_name = 'Broker Account'
        verbose_name_plural = 'Broker Accounts'
    
    def __str__(self):
        return f"{self.user.username} - {self.get_broker_type_display()} - {self.name}"
    
    def get_broker_type(self) -> str:
        """
        Récupère le broker_type de manière sécurisée.
        Utilise le champ broker_type directement, ou fallback sur broker.broker_type.
        
        Returns:
            Type de broker (SAXO, BINANCE, etc.)
        """
        if self.broker_type:
            return self.broker_type
        elif self.broker and self.broker.broker_type:
            # Mettre à jour le champ pour éviter de refaire cette vérification
            self.broker_type = self.broker.broker_type
            self.save(update_fields=['broker_type'])
            return self.broker_type
        else:
            return 'OTHER'
    
    def get_credentials_dict(self) -> dict:
        """
        Retourner les credentials sous forme de dictionnaire.
        Compatible avec l'architecture v3.
        """
        broker_type = self.get_broker_type()
        
        if broker_type == 'SAXO':
            return {
                'client_id': self.saxo_client_id or self.client_id,
                'client_secret': self.saxo_client_secret or self.client_secret,
                'redirect_uri': self.saxo_redirect_uri,
                'access_token': self.saxo_access_token or self.access_token,
                'refresh_token': self.saxo_refresh_token or self.refresh_token,
                'token_expires_at': self.saxo_token_expires_at or self.token_expires_at,
                # ✅ MIGRATION: Pour Saxo, privilégier saxo_environment, sinon environment, sinon défaut 'live'
                'environment': (self.saxo_environment if hasattr(self, 'saxo_environment') and self.saxo_environment else None) or self.environment or 'live',
            }
        elif broker_type == 'BINANCE':
            return {
                'api_key': self.binance_api_key or self.api_key,
                'api_secret': self.binance_api_secret or self.api_secret,
                'testnet': self.binance_testnet if hasattr(self, 'binance_testnet') else self.is_sandbox,
                'environment': self.environment,
            }
        else:
            # Pour les autres brokers, utiliser les champs génériques
            return {
                'api_key': self.api_key,
                'api_secret': self.api_secret,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
                'token_expires_at': self.token_expires_at,
                'environment': self.environment or 'simulation',
            }


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
    error_message = models.TextField(blank=True, default='')
    details = models.JSONField(default=dict, blank=True)
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Broker Sync Log'
        verbose_name_plural = 'Broker Sync Logs'
    
    def __str__(self):
        return f"{self.broker_account} - {self.sync_type} ({self.status})"

