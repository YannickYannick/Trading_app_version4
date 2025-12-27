"""
Modèles liés aux assets (actifs financiers).
"""
from django.db import models
from .base import TimeStampedModel


# Choix des brokers/plateformes
BROKER_CHOICES = [
    ('SAXO', 'Saxo Bank'),
    ('BINANCE', 'Binance'),
    ('IB', 'Interactive Brokers'),
    ('OTHER', 'Autre'),
]


class AllAssets(models.Model):
    """Catalogue universel d'actifs récupérés depuis les APIs des brokers."""
    
    # Valeurs possibles pour symbole_yahoo
    class YahooStatus(models.TextChoices):
        NOT_SEARCHED = 'Not_searched', 'Non recherché'
        NOT_FOUND = 'not_found', 'Non trouvé'
        MANUAL = 'manual', 'Validation manuelle requise'
    
    symbol = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    platform = models.CharField(max_length=20, choices=BROKER_CHOICES)
    asset_type = models.CharField(max_length=50)
    market = models.CharField(max_length=50)
    currency = models.CharField(max_length=10, default='USD')
    exchange = models.CharField(max_length=100, blank=True)
    is_tradable = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Champ Yahoo Finance - symbole validé
    symbole_yahoo = models.CharField(
        max_length=50,
        default='Not_searched',
        db_index=True,
        help_text="Symbole Yahoo validé, 'not_found', 'manual', ou 'Not_searched'"
    )
    yahoo_validated_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Date de dernière validation Yahoo"
    )
    yahoo_validation_method = models.CharField(
        max_length=20,
        blank=True,
        help_text="Méthode de validation: Y4 (MIC), Y3 (nom), Y0 (brut)"
    )
    
    # Champs spécifiques Saxo
    saxo_uic = models.IntegerField(null=True, blank=True)
    saxo_exchange_id = models.CharField(max_length=20, blank=True)
    saxo_country_code = models.CharField(max_length=10, blank=True)
    
    # Champs spécifiques Binance
    binance_base_asset = models.CharField(max_length=20, blank=True)
    binance_quote_asset = models.CharField(max_length=20, blank=True)
    binance_status = models.CharField(max_length=20, blank=True)
    
    class Meta:
        unique_together = ['symbol', 'platform']
        indexes = [
            models.Index(fields=['platform', 'asset_type']),
            models.Index(fields=['symbol']),
            models.Index(fields=['name']),
        ]
        verbose_name = 'All Asset'
        verbose_name_plural = 'All Assets'
    
    def __str__(self):
        return f"{self.symbol} ({self.platform}) - {self.name}"
    
    @property
    def is_saxo(self):
        return self.platform == 'SAXO'
    
    @property
    def is_binance(self):
        return self.platform == 'BINANCE'
    
    @property
    def needs_yahoo_validation(self) -> bool:
        """Vérifie si l'asset nécessite une validation Yahoo."""
        return self.symbole_yahoo == 'Not_searched'
    
    @property
    def is_yahoo_validated(self) -> bool:
        """Vérifie si l'asset a un symbole Yahoo validé."""
        return self.symbole_yahoo not in ['Not_searched', 'not_found', 'manual']
    
    @property
    def is_yahoo_manual(self) -> bool:
        """Vérifie si l'asset nécessite une validation manuelle."""
        return self.symbole_yahoo == 'manual'
    
    def set_yahoo_symbol(self, symbol: str, method: str = '') -> None:
        """Met à jour le symbole Yahoo avec la méthode de validation."""
        from django.utils import timezone
        self.symbole_yahoo = symbol
        self.yahoo_validation_method = method
        self.yahoo_validated_at = timezone.now()
        self.save(update_fields=['symbole_yahoo', 'yahoo_validation_method', 'yahoo_validated_at'])


class Asset(TimeStampedModel):
    """Actif sous-jacent avec données enrichies."""
    
    class AssetType(models.TextChoices):
        STOCK = 'STOCK', 'Action'
        CRYPTO = 'CRYPTO', 'Cryptomonnaie'
        ETF = 'ETF', 'ETF'
        FOREX = 'FOREX', 'Forex'
        COMMODITY = 'COMMODITY', 'Matière première'
        BOND = 'BOND', 'Obligation'
        OTHER = 'OTHER', 'Autre'
    
    # Référence vers AllAssets (catalogue universel)
    all_asset = models.ForeignKey(
        AllAssets,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enriched_assets',
        help_text="Référence vers le catalogue universel des actifs"
    )
    
    symbol = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    asset_type = models.CharField(
        max_length=20,
        choices=AssetType.choices,
        default=AssetType.STOCK
    )
    currency = models.CharField(max_length=10, default='USD')
    exchange = models.CharField(max_length=50, blank=True)
    
    # Prix
    current_price = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True
    )
    price_updated_at = models.DateTimeField(null=True, blank=True)
    
    # Métadonnées
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    
    # Données enrichies (Yahoo Finance, etc.)
    sector = models.CharField(max_length=100, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    market_cap = models.BigIntegerField(null=True, blank=True)
    pe_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dividend_yield = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    
    class Meta:
        ordering = ['symbol']
        verbose_name = 'Asset'
        verbose_name_plural = 'Assets'
    
    def __str__(self):
        return f"{self.symbol} - {self.name}"
    
    @classmethod
    def create_from_all_asset(cls, all_asset: AllAssets):
        """Crée un Asset enrichi à partir d'un AllAssets."""
        return cls.objects.create(
            all_asset=all_asset,
            symbol=all_asset.symbol,
            name=all_asset.name,
            currency=all_asset.currency,
            exchange=all_asset.exchange,
        )


class AssetPrice(TimeStampedModel):
    """Historique des prix d'un asset."""
    asset = models.ForeignKey(
        Asset, on_delete=models.CASCADE, related_name='price_history'
    )
    date = models.DateField()
    open_price = models.DecimalField(max_digits=20, decimal_places=8)
    high_price = models.DecimalField(max_digits=20, decimal_places=8)
    low_price = models.DecimalField(max_digits=20, decimal_places=8)
    close_price = models.DecimalField(max_digits=20, decimal_places=8)
    volume = models.BigIntegerField(null=True, blank=True)
    
    class Meta:
        unique_together = ['asset', 'date']
        ordering = ['-date']
        verbose_name = 'Asset Price'
        verbose_name_plural = 'Asset Prices'
    
    def __str__(self):
        return f"{self.asset.symbol} - {self.date}"
