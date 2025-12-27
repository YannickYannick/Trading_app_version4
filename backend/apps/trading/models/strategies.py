"""
Modèles liés aux stratégies de trading.
"""
from django.db import models
from django.contrib.auth.models import User
from .base import TimeStampedModel


class Strategy(TimeStampedModel):
    """Stratégie de trading."""
    
    class RiskLevel(models.TextChoices):
        LOW = 'LOW', 'Faible'
        MEDIUM = 'MEDIUM', 'Moyen'
        HIGH = 'HIGH', 'Élevé'
    
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='strategies'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Configuration
    risk_level = models.CharField(
        max_length=10, choices=RiskLevel.choices, default=RiskLevel.MEDIUM
    )
    max_position_size = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Taille maximale d'une position en %"
    )
    max_daily_loss = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Perte maximale journalière en %"
    )
    
    # Paramètres
    parameters = models.JSONField(default=dict, blank=True)
    
    is_active = models.BooleanField(default=True)
    is_automated = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Strategy'
        verbose_name_plural = 'Strategies'
    
    def __str__(self):
        return self.name


class StrategyPerformance(TimeStampedModel):
    """Performance journalière d'une stratégie."""
    strategy = models.ForeignKey(
        Strategy, on_delete=models.CASCADE, related_name='performances'
    )
    date = models.DateField()
    
    # Métriques
    total_trades = models.IntegerField(default=0)
    winning_trades = models.IntegerField(default=0)
    losing_trades = models.IntegerField(default=0)
    
    gross_pnl = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    fees = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    net_pnl = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ['strategy', 'date']
        ordering = ['-date']
        verbose_name = 'Strategy Performance'
        verbose_name_plural = 'Strategy Performances'
    
    def __str__(self):
        return f"{self.strategy.name} - {self.date}"
    
    @property
    def win_rate(self):
        """Calcule le taux de réussite."""
        if self.total_trades == 0:
            return 0
        return (self.winning_trades / self.total_trades) * 100

