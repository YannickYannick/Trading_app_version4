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
    
    # Regroupement des assets (relation vers Asset normalisé)
    parent_asset = models.ForeignKey(
        'Asset',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='variants',
        help_text="Asset normalisé parent (ex: AAPL pour AAPL:xnas, AAPL:xnys)"
    )
    is_best_variant = models.BooleanField(
        default=False,
        help_text="Indique si c'est la meilleure variante pour le parent_asset (USD prioritaire)"
    )
    
    # Historique des prix en format JSONB (compact)
    price_history_json = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text="Historique des prix au format JSON: {'YYYY-MM-DD': {'open': x, 'high': y, 'low': z, 'close': w, 'volume': v, 'source': 'YAHOO'}, ...}"
    )
    price_history_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date de dernière mise à jour de l'historique des prix"
    )
    price_history_days = models.IntegerField(
        default=0,
        help_text="Nombre de jours d'historique stockés"
    )
    
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
    
    @property
    def has_price_history(self) -> bool:
        """Vérifie si l'asset a un historique de prix stocké."""
        return bool(self.price_history_json) and len(self.price_history_json) > 0
    
    def get_price_history_count(self) -> int:
        """Retourne le nombre de jours d'historique stockés."""
        if not self.price_history_json:
            return 0
        return len(self.price_history_json)
    
    def get_price_history_dates(self) -> list:
        """Retourne la liste des dates disponibles dans l'historique, triées du plus récent au plus ancien."""
        if not self.price_history_json:
            return []
        return sorted(self.price_history_json.keys(), reverse=True)
    
    def get_price_for_date(self, date_str: str) -> dict:
        """Récupère les données de prix pour une date spécifique (format 'YYYY-MM-DD')."""
        if not self.price_history_json:
            return {}
        return self.price_history_json.get(date_str, {})
    
    def set_yahoo_symbol(self, symbol: str, method: str = '') -> None:
        """Met à jour le symbole Yahoo avec la méthode de validation."""
        from django.utils import timezone
        self.symbole_yahoo = symbol
        self.yahoo_validation_method = method
        self.yahoo_validated_at = timezone.now()
        self.save(update_fields=['symbole_yahoo', 'yahoo_validation_method', 'yahoo_validated_at'])


class Asset(TimeStampedModel):
    """Asset normalisé regroupant plusieurs variantes broker.
    
    Ex: AAPL regroupe AAPL:xnas (NASDAQ), AAPL:xpar (Euronext), etc.
    Le symbole est simplifié (sans MIC), la devise est prioritairement USD.
    """
    
    class AssetType(models.TextChoices):
        STOCK = 'STOCK', 'Action'
        CRYPTO = 'CRYPTO', 'Cryptomonnaie'
        ETF = 'ETF', 'ETF'
        FOREX = 'FOREX', 'Forex'
        COMMODITY = 'COMMODITY', 'Matière première'
        BOND = 'BOND', 'Obligation'
        OTHER = 'OTHER', 'Autre'
    
    # Meilleure variante (USD prioritaire, bourse principale)
    best_variant = models.ForeignKey(
        AllAssets,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text="Meilleur AllAssets pour trading (USD, NYSE/NASDAQ prioritaires)"
    )
    
    # Suivi et favoris
    is_tracked = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Asset suivi (a des trades/positions ou ajouté manuellement)"
    )
    is_favorite = models.BooleanField(
        default=False,
        help_text="Asset ajouté manuellement à la watchlist"
    )
    
    # Référence vers AllAssets (DEPRECATED - utilisé pour compatibilité)
    all_asset = models.ForeignKey(
        AllAssets,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enriched_assets',
        help_text="[DEPRECATED] Utiliser best_variant à la place"
    )
    
    symbol = models.CharField(
        max_length=50, 
        unique=True,
        help_text="Symbole normalisé sans MIC (ex: AAPL, BTC, ETH)"
    )
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


class AllAssetPriceHistory(TimeStampedModel):
    """Historique des prix consolidé pour un AllAsset."""
    
    class PriceSource(models.TextChoices):
        YAHOO_FINANCE = 'YAHOO', 'Yahoo Finance'
        SAXO = 'SAXO', 'Saxo Bank'
        BINANCE = 'BINANCE', 'Binance'
        INTERACTIVE_BROKERS = 'IB', 'Interactive Brokers'
        MANUAL = 'MANUAL', 'Manuel'
    
    all_asset = models.ForeignKey(
        AllAssets,
        on_delete=models.CASCADE,
        related_name='price_history',
        help_text="AllAsset pour lequel cet historique est enregistré"
    )
    date = models.DateField(db_index=True)
    open_price = models.DecimalField(max_digits=20, decimal_places=8)
    high_price = models.DecimalField(max_digits=20, decimal_places=8)
    low_price = models.DecimalField(max_digits=20, decimal_places=8)
    close_price = models.DecimalField(max_digits=20, decimal_places=8)
    volume = models.BigIntegerField(null=True, blank=True)
    source = models.CharField(
        max_length=10,
        choices=PriceSource.choices,
        default=PriceSource.YAHOO_FINANCE,
        help_text="Source des données de prix"
    )
    
    class Meta:
        unique_together = ['all_asset', 'date', 'source']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['all_asset', 'date']),
            models.Index(fields=['all_asset', '-date']),
        ]
        verbose_name = 'AllAsset Price History'
        verbose_name_plural = 'AllAssets Price History'
    
    def __str__(self):
        return f"{self.all_asset.symbol} - {self.date} - {self.get_source_display()}"
