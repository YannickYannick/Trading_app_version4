"""
Modèles liés au trading (positions, trades, ordres).
"""
from django.db import models
from django.contrib.auth.models import User
from .base import TimeStampedModel


class Position(TimeStampedModel):
    """Position ouverte sur un asset."""
    
    class PositionSide(models.TextChoices):
        LONG = 'LONG', 'Long'
        SHORT = 'SHORT', 'Short'
    
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='positions'
    )
    
    # ForeignKey DIRECT vers AllAssets (source de vérité)
    all_asset = models.ForeignKey(
        'AllAssets',
        on_delete=models.CASCADE,
        related_name='positions',
        help_text="Asset depuis le catalogue universel AllAssets"
    )
    
    # Asset devient optionnel (pour compatibilité et enrichissement futur)
    asset = models.ForeignKey(
        'Asset',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='positions',
        help_text="Asset enrichi optionnel (pour données supplémentaires)"
    )
    
    broker = models.ForeignKey(
        'Broker', on_delete=models.CASCADE, related_name='positions'
    )
    strategy = models.ForeignKey(
        'Strategy', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='positions'
    )
    
    side = models.CharField(
        max_length=10, choices=PositionSide.choices, default=PositionSide.LONG
    )
    quantity = models.DecimalField(max_digits=20, decimal_places=8)
    entry_price = models.DecimalField(max_digits=20, decimal_places=8)
    current_price = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True
    )
    
    # Stop loss / Take profit
    stop_loss = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True
    )
    take_profit = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True
    )
    
    is_open = models.BooleanField(default=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-opened_at']
        verbose_name = 'Position'
        verbose_name_plural = 'Positions'
    
    def __str__(self):
        status = "Open" if self.is_open else "Closed"
        symbol = self.all_asset.symbol if self.all_asset else (self.asset.symbol if self.asset else 'Unknown')
        return f"{symbol} {self.side} ({status})"
    
    @property
    def pnl(self):
        """Calcule le P&L non réalisé."""
        if not self.current_price:
            return None
        if self.side == self.PositionSide.LONG:
            return (self.current_price - self.entry_price) * self.quantity
        else:
            return (self.entry_price - self.current_price) * self.quantity
    
    @property
    def pnl_percent(self):
        """Calcule le P&L en pourcentage."""
        if not self.current_price or not self.entry_price:
            return None
        if self.side == self.PositionSide.LONG:
            return ((self.current_price - self.entry_price) / self.entry_price) * 100
        else:
            return ((self.entry_price - self.current_price) / self.entry_price) * 100


class Trade(TimeStampedModel):
    """Trade exécuté (achat ou vente)."""
    
    class TradeType(models.TextChoices):
        BUY = 'BUY', 'Achat'
        SELL = 'SELL', 'Vente'
    
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='trades'
    )
    
    # ForeignKey DIRECT vers AllAssets (source de vérité)
    all_asset = models.ForeignKey(
        'AllAssets',
        on_delete=models.CASCADE,
        related_name='trades',
        help_text="Asset depuis le catalogue universel AllAssets"
    )
    
    # Asset devient optionnel (pour compatibilité et enrichissement futur)
    asset = models.ForeignKey(
        'Asset',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trades',
        help_text="Asset enrichi optionnel (pour données supplémentaires)"
    )
    
    broker = models.ForeignKey(
        'Broker', on_delete=models.CASCADE, related_name='trades'
    )
    position = models.ForeignKey(
        Position, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='trades'
    )
    
    trade_type = models.CharField(
        max_length=10, choices=TradeType.choices
    )
    quantity = models.DecimalField(max_digits=20, decimal_places=8)
    price = models.DecimalField(max_digits=20, decimal_places=8)
    fees = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    
    executed_at = models.DateTimeField()
    broker_trade_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['-executed_at']
        verbose_name = 'Trade'
        verbose_name_plural = 'Trades'
    
    def __str__(self):
        symbol = self.all_asset.symbol if self.all_asset else (self.asset.symbol if self.asset else 'Unknown')
        return f"{self.trade_type} {self.quantity} {symbol} @ {self.price}"
    
    @property
    def total_value(self):
        """Valeur totale du trade (quantité * prix)."""
        return self.quantity * self.price


class Order(TimeStampedModel):
    """Ordre en attente d'exécution."""
    
    class OrderType(models.TextChoices):
        MARKET = 'MARKET', 'Market'
        LIMIT = 'LIMIT', 'Limit'
        STOP = 'STOP', 'Stop'
        STOP_LIMIT = 'STOP_LIMIT', 'Stop Limit'
    
    class OrderSide(models.TextChoices):
        BUY = 'BUY', 'Achat'
        SELL = 'SELL', 'Vente'
    
    class OrderStatus(models.TextChoices):
        PENDING = 'PENDING', 'En attente'
        OPEN = 'OPEN', 'Ouvert'
        FILLED = 'FILLED', 'Exécuté'
        PARTIALLY_FILLED = 'PARTIALLY_FILLED', 'Partiellement exécuté'
        CANCELLED = 'CANCELLED', 'Annulé'
        REJECTED = 'REJECTED', 'Rejeté'
        EXPIRED = 'EXPIRED', 'Expiré'
    
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='orders'
    )
    asset = models.ForeignKey(
        'Asset', on_delete=models.CASCADE, related_name='orders'
    )
    broker = models.ForeignKey(
        'Broker', on_delete=models.CASCADE, related_name='orders'
    )
    
    order_type = models.CharField(
        max_length=20, choices=OrderType.choices, default=OrderType.MARKET
    )
    side = models.CharField(max_length=10, choices=OrderSide.choices)
    status = models.CharField(
        max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING
    )
    
    quantity = models.DecimalField(max_digits=20, decimal_places=8)
    filled_quantity = models.DecimalField(
        max_digits=20, decimal_places=8, default=0
    )
    price = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True
    )
    stop_price = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True
    )
    
    broker_order_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
    
    def __str__(self):
        return f"{self.side} {self.quantity} {self.asset.symbol} ({self.status})"

