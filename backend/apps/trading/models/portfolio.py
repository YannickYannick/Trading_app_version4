from django.db import models
from django.contrib.auth.models import User
from .base import TimeStampedModel

class PortfolioSnapshot(TimeStampedModel):
    """
    Snapshot de la valeur du portefeuille à un instant T.
    Utilisé pour tracer l'historique de la valeur totale.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portfolio_snapshots')
    date = models.DateTimeField(auto_now_add=True)
    
    # Valeurs totales
    total_value = models.DecimalField(max_digits=20, decimal_places=2)
    total_cash = models.DecimalField(max_digits=20, decimal_places=2)
    total_invested = models.DecimalField(max_digits=20, decimal_places=2)
    
    # Détail pour le diagramme circulaire (JSON)
    # Ex: { "Saxo Custom": {"total": 12000, "cash": 2000, "invested": 10000}, "Binance": ... }
    breakdown = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-date']
        get_latest_by = 'date'
        
    def __str__(self):
        return f"Snapshot {self.user.username} - {self.date} - {self.total_value}€"
