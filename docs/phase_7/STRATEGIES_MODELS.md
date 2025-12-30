# Modèles de Données - Système de Stratégies

## Vue d'ensemble

Ce document décrit les modèles Django nécessaires pour le système de stratégies, incluant l'extension du modèle `Strategy` existant et la création du modèle `StrategyExecution` pour l'historique d'exécution.

## Modèle Strategy (Extension)

### Localisation

**Fichier** : `backend/apps/trading/models/strategies.py`

### Champs à Ajouter

Le modèle `Strategy` existe déjà avec des champs de base. Il faut l'étendre avec :

```python
class Strategy(TimeStampedModel):
    """Stratégie de trading automatisée."""
    
    # === CHOIX DISPONIBLES ===
    
    class AlgorithmType(models.TextChoices):
        THRESHOLD = 'threshold', 'Seuils (Threshold)'
        MA_CROSSOVER = 'ma_crossover', 'Moving Average Crossover'
        RSI = 'rsi', 'RSI (Relative Strength Index)'
        BOLLINGER = 'bollinger', 'Bollinger Bands'
        MACD = 'macd', 'MACD'
        GRID = 'grid', 'Grid Trading'
    
    class ExecutionMode(models.TextChoices):
        SIMULATION = 'simulation', 'Simulation'
        PAPER_TRADING = 'paper_trading', 'Paper Trading'
        LIVE_TRADING = 'live_trading', 'Trading Réel'
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        PAUSED = 'paused', 'En Pause'
    
    # === CHAMPS EXISTANTS (à conserver) ===
    user = models.ForeignKey(User, ...)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    risk_level = models.CharField(...)
    max_position_size = models.DecimalField(...)
    max_daily_loss = models.DecimalField(...)
    parameters = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    is_automated = models.BooleanField(default=False)
    
    # === NOUVEAUX CHAMPS À AJOUTER ===
    
    # Asset et Broker
    asset = models.ForeignKey(
        'Asset',
        on_delete=models.CASCADE,
        related_name='strategies',
        help_text="Asset cible de la stratégie"
    )
    all_asset = models.ForeignKey(
        'AllAssets',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='strategies',
        help_text="Asset depuis le catalogue universel (source de vérité)"
    )
    broker_account = models.ForeignKey(
        'BrokerAccount',
        on_delete=models.CASCADE,
        related_name='strategies',
        help_text="Compte broker pour l'exécution"
    )
    
    # Algorithme
    algorithm_type = models.CharField(
        max_length=20,
        choices=AlgorithmType.choices,
        help_text="Type d'algorithme de trading"
    )
    
    # Configuration d'exécution
    execution_mode = models.CharField(
        max_length=20,
        choices=ExecutionMode.choices,
        default=ExecutionMode.SIMULATION,
        help_text="Mode d'exécution (simulation, paper_trading, live_trading)"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.INACTIVE,
        help_text="Statut de la stratégie"
    )
    check_frequency = models.IntegerField(
        default=45,
        help_text="Fréquence de vérification en minutes"
    )
    
    # Gestion des positions
    portfolio_quantity = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=-1,
        help_text="Quantité totale en portefeuille (-1 = non calculé)"
    )
    target_min_quantity = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=0,
        help_text="Quantité minimale cible à maintenir"
    )
    target_max_quantity = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=0,
        help_text="Quantité maximale cible à maintenir"
    )
    
    # Statistiques
    total_trades = models.IntegerField(default=0)
    successful_trades = models.IntegerField(default=0)
    total_pnl = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0
    )
    
    # Métadonnées
    last_execution = models.DateTimeField(null=True, blank=True)
    comments = models.TextField(blank=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Strategy'
        verbose_name_plural = 'Strategies'
        unique_together = ['user', 'asset', 'name']  # Nom unique par user et asset
    
    def __str__(self):
        return f"{self.name} ({self.get_algorithm_type_display()})"
```

### Méthodes du Modèle

```python
def get_algorithm_instance(self):
    """Retourne une instance de l'algorithme correspondant."""
    from ..algorithms.factory import AlgorithmFactory
    return AlgorithmFactory.create_algorithm(
        self.algorithm_type,
        self.parameters,
        self
    )

def calculate_portfolio_quantity(self):
    """
    Calcule la quantité totale en portefeuille pour cet asset.
    
    Utilise les Position ouvertes pour calculer la quantité totale.
    """
    from .trading import Position
    
    if not self.all_asset:
        self.portfolio_quantity = -1
        self.save(update_fields=['portfolio_quantity'])
        return -1
    
    # Chercher toutes les positions ouvertes pour cet asset
    positions = Position.objects.filter(
        user=self.user,
        all_asset=self.all_asset,
        is_open=True
    )
    
    if not positions.exists():
        self.portfolio_quantity = 0
        self.save(update_fields=['portfolio_quantity'])
        return 0
    
    # Sommer les quantités (LONG positives, SHORT négatives)
    total_quantity = sum(
        float(pos.quantity) if pos.side == Position.PositionSide.LONG else -float(pos.quantity)
        for pos in positions
    )
    
    self.portfolio_quantity = total_quantity
    self.save(update_fields=['portfolio_quantity'])
    return total_quantity

def calculate_optimal_quantity(self, side):
    """
    Calcule la quantité optimale à trader selon l'objectif de la stratégie.
    
    Args:
        side: 'BUY' ou 'SELL'
    
    Returns:
        Quantité optimale à trader (peut être 0 si objectif atteint)
    """
    if self.portfolio_quantity == -1:
        self.calculate_portfolio_quantity()
    
    if self.portfolio_quantity == -1:
        return 0
    
    current_quantity = float(self.portfolio_quantity)
    max_trade_size = float(self.parameters.get('order_size', 1000))
    
    if side.upper() == 'BUY' and self.target_max_quantity > 0:
        optimal = float(self.target_max_quantity) - current_quantity
        return max(0, min(optimal, max_trade_size))
    
    elif side.upper() == 'SELL' and self.target_min_quantity > 0:
        optimal = current_quantity - float(self.target_min_quantity)
        return max(0, min(optimal, max_trade_size))
    
    return 0

def should_execute_order(self, signal_result):
    """
    Détermine si un ordre doit être exécuté selon le mode d'exécution.
    
    Args:
        signal_result: Dict avec 'signal' (BUY/SELL/HOLD)
    
    Returns:
        bool: True si l'ordre doit être exécuté
    """
    if signal_result.get('signal') == 'HOLD':
        return False
    
    if self.execution_mode == self.ExecutionMode.SIMULATION:
        return False  # Pas d'exécution en simulation
    
    if self.status != self.Status.ACTIVE:
        return False  # Stratégie inactive ou en pause
    
    return True  # Paper trading ou live trading
```

### Validation

```python
def clean(self):
    """Validation personnalisée du modèle."""
    super().clean()
    
    # Vérifier que target_min <= target_max
    if self.target_min_quantity and self.target_max_quantity:
        if self.target_min_quantity > self.target_max_quantity:
            raise ValidationError({
                'target_min_quantity': 'La quantité minimale ne peut pas être supérieure à la quantité maximale.'
            })
    
    # Vérifier la fréquence
    if self.check_frequency < 1 or self.check_frequency > 1440:
        raise ValidationError({
            'check_frequency': 'La fréquence doit être entre 1 et 1440 minutes (24h).'
        })
```

## Modèle StrategyExecution (Nouveau)

### Localisation

**Fichier** : `backend/apps/trading/models/strategy_execution.py` (nouveau fichier)

### Structure Complète

```python
"""
Modèle pour l'historique d'exécution des stratégies.
"""
from django.db import models
from django.core.validators import MinValueValidator
from .base import TimeStampedModel


class StrategyExecution(TimeStampedModel):
    """Historique des exécutions d'une stratégie."""
    
    class SignalType(models.TextChoices):
        BUY = 'BUY', 'Achat'
        SELL = 'SELL', 'Vente'
        HOLD = 'HOLD', 'Attente'
    
    strategy = models.ForeignKey(
        'Strategy',
        on_delete=models.CASCADE,
        related_name='executions',
        help_text="Stratégie exécutée"
    )
    
    # Données de l'exécution
    execution_time = models.DateTimeField(
        auto_now_add=True,
        help_text="Date et heure d'exécution"
    )
    current_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Prix de l'asset au moment de l'exécution"
    )
    
    # Signal calculé
    signal = models.CharField(
        max_length=10,
        choices=SignalType.choices,
        help_text="Signal généré (BUY/SELL/HOLD)"
    )
    signal_strength = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0)],
        help_text="Force du signal (0-1)"
    )
    signal_reason = models.TextField(
        blank=True,
        help_text="Raison du signal généré"
    )
    
    # Résultat de l'exécution
    order_executed = models.BooleanField(
        default=False,
        help_text="Indique si un ordre a été exécuté"
    )
    order = models.ForeignKey(
        'Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='strategy_executions',
        help_text="Ordre créé lors de l'exécution (si applicable)"
    )
    order_size = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        help_text="Taille de l'ordre exécuté"
    )
    order_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        help_text="Prix de l'ordre exécuté"
    )
    
    # Métadonnées
    execution_duration = models.FloatField(
        default=0.0,
        help_text="Durée d'exécution en secondes"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Message d'erreur si l'exécution a échoué"
    )
    
    class Meta:
        ordering = ['-execution_time']
        verbose_name = 'Strategy Execution'
        verbose_name_plural = 'Strategy Executions'
        indexes = [
            models.Index(fields=['strategy', '-execution_time']),
            models.Index(fields=['execution_time']),
        ]
    
    def __str__(self):
        return f"{self.strategy.name} - {self.signal} - {self.execution_time}"
    
    @property
    def is_successful(self):
        """Indique si l'exécution a réussi."""
        if self.signal == 'HOLD':
            return True  # HOLD est toujours considéré comme réussi
        return self.order_executed and not self.error_message
```

## Relations avec Autres Modèles

### Asset

```python
# Strategy a une ForeignKey vers Asset et AllAssets
strategy.asset  # Asset enrichi
strategy.all_asset  # AllAssets (source de vérité)
```

### BrokerAccount

```python
# Strategy utilise un BrokerAccount pour l'exécution
strategy.broker_account  # Compte broker
strategy.broker_account.broker  # Broker (Binance, Saxo, etc.)
```

### Order

```python
# StrategyExecution peut être lié à un Order
execution.order  # Ordre créé lors de l'exécution
```

### Position

```python
# Les positions peuvent être liées à une stratégie
position.strategy  # Stratégie qui a créé la position
```

## Migrations

### Migration pour Extension de Strategy

Créer une migration :

```python
# backend/apps/trading/migrations/XXXX_extend_strategy_model.py

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('trading', 'XXXX_previous_migration'),
    ]

    operations = [
        # Ajouter les nouveaux champs
        migrations.AddField(
            model_name='strategy',
            name='asset',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='strategies',
                to='trading.asset'
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='strategy',
            name='all_asset',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='strategies',
                to='trading.allassets'
            ),
        ),
        migrations.AddField(
            model_name='strategy',
            name='broker_account',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='strategies',
                to='trading.brokeraccount'
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='strategy',
            name='algorithm_type',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('threshold', 'Seuils (Threshold)'),
                    ('ma_crossover', 'Moving Average Crossover'),
                    ('rsi', 'RSI (Relative Strength Index)'),
                    ('bollinger', 'Bollinger Bands'),
                    ('macd', 'MACD'),
                    ('grid', 'Grid Trading'),
                ],
                null=True
            ),
            preserve_default=False,
        ),
        # ... autres champs ...
    ]
```

### Migration pour StrategyExecution

```python
# backend/apps/trading/migrations/XXXX_create_strategy_execution.py

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('trading', 'XXXX_extend_strategy_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='StrategyExecution',
            fields=[
                # ... tous les champs ...
            ],
            options={
                'ordering': ['-execution_time'],
                'verbose_name': 'Strategy Execution',
                'verbose_name_plural': 'Strategy Executions',
            },
        ),
    ]
```

## Index et Optimisations

### Index Recommandés

```python
class Strategy(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['asset', 'status']),
        ]
```

## Points Critiques

1. **Asset vs AllAssets** :
   - `all_asset` est la source de vérité (obligatoire)
   - `asset` est optionnel (pour données enrichies)

2. **portfolio_quantity** :
   - `-1` signifie "non calculé"
   - `0` signifie "pas de position"
   - Valeur positive = quantité en portefeuille

3. **Quantités cibles** :
   - `target_min_quantity` : Quantité minimale à maintenir
   - `target_max_quantity` : Quantité maximale à maintenir
   - Validation : `target_min <= target_max`

4. **Statut** :
   - `INACTIVE` : Stratégie créée mais non activée
   - `ACTIVE` : Stratégie active (peut être exécutée)
   - `PAUSED` : Stratégie temporairement en pause

---

**Voir aussi** :
- [STRATEGIES_ALGORITHMS.md](STRATEGIES_ALGORITHMS.md) : Algorithmes de trading
- [STRATEGIES_API.md](STRATEGIES_API.md) : API REST
- [STRATEGIES_SERVICES.md](STRATEGIES_SERVICES.md) : Services backend

