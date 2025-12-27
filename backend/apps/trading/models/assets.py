"""
Modèles liés aux assets (actifs financiers).
"""
from django.db import models
from .base import TimeStampedModel


class Asset(TimeStampedModel):
    """Représente un actif financier (action, crypto, etc.)."""
    
    class AssetType(models.TextChoices):
        STOCK = 'STOCK', 'Action'
        CRYPTO = 'CRYPTO', 'Cryptomonnaie'
        ETF = 'ETF', 'ETF'
        FOREX = 'FOREX', 'Forex'
        COMMODITY = 'COMMODITY', 'Matière première'
        BOND = 'BOND', 'Obligation'
        OTHER = 'OTHER', 'Autre'
    
    symbol = models.CharField(max_length=20, unique=True)
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
    
    class Meta:
        ordering = ['symbol']
        verbose_name = 'Asset'
        verbose_name_plural = 'Assets'
    
    def __str__(self):
        return f"{self.symbol} - {self.name}"


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

