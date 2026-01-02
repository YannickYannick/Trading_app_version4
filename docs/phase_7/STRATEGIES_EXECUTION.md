# Exécution des Stratégies

## Vue d'ensemble

Ce document décrit les modes d'exécution des stratégies et le processus d'exécution complet.

## Modes d'Exécution

### 1. Simulation

**Mode** : `simulation`

**Comportement** :
- Les signaux sont calculés
- Aucun ordre n'est exécuté
- L'historique est enregistré
- Permet de tester la stratégie sans risque

**Utilisation** :
- Tester de nouvelles stratégies
- Backtesting
- Validation des paramètres

### 2. Paper Trading

**Mode** : `paper_trading`

**Comportement** :
- Les signaux sont calculés
- Les ordres sont simulés (pas d'argent réel)
- L'historique est enregistré
- Nécessite une implémentation spécifique du broker

**Utilisation** :
- Tester dans des conditions réelles sans risque
- Valider la logique d'exécution

### 3. Live Trading

**Mode** : `live_trading`

**Comportement** :
- Les signaux sont calculés
- Les ordres sont réellement exécutés sur le broker
- L'historique est enregistré
- Utilise de l'argent réel

**Utilisation** :
- Production réelle
- Trading automatisé actif

## Exécution Manuelle

### Via l'API

```bash
POST /api/strategies/{id}/execute/
```

### Via le Frontend

L'utilisateur clique sur le bouton "Exécuter" dans la liste des stratégies.

### Processus

1. Récupération des prix (Yahoo Finance ou broker)
2. Calcul des signaux via l'algorithme
3. Vérification des conditions (quantités cibles, mode)
4. Passage d'ordre si nécessaire
5. Enregistrement de l'exécution

## Exécution Automatique

### Configuration

Les stratégies avec `is_automated=True` et `status='active'` sont exécutées automatiquement selon leur `check_frequency`.

### Tâche Périodique

**Option 1 : Celery** (Recommandé pour production)

```python
# backend/apps/trading/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

@shared_task
def execute_automated_strategies():
    """Exécute les stratégies automatisées actives."""
    from ..models.strategies import Strategy
    from ..services.strategy_executor import StrategyExecutor
    
    executor = StrategyExecutor()
    
    strategies = Strategy.objects.filter(
        is_automated=True,
        status=Strategy.Status.ACTIVE
    )
    
    for strategy in strategies:
        # Vérifier la fréquence
        if strategy.last_execution:
            time_since = timezone.now() - strategy.last_execution
            if time_since < timedelta(minutes=strategy.check_frequency):
                continue
        
        try:
            executor.execute_strategy(strategy)
        except Exception as e:
            logger.error(f"Erreur exécution stratégie {strategy.id}: {e}")
```

**Configuration Celery** :

```python
# config_django/celery.py
from celery import Celery

app = Celery('trading_app')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Schedule
app.conf.beat_schedule = {
    'execute-strategies': {
        'task': 'apps.trading.tasks.execute_automated_strategies',
        'schedule': 60.0,  # Toutes les minutes
    },
}
```

**Option 2 : Django-Q** (Plus simple)

```python
# backend/apps/trading/management/commands/execute_strategies.py
from django.core.management.base import BaseCommand
from django_q.tasks import schedule
from django_q.models import Schedule

class Command(BaseCommand):
    def handle(self, *args, **options):
        schedule(
            'apps.trading.tasks.execute_automated_strategies',
            schedule_type=Schedule.MINUTES,
            minutes=1,
            repeats=-1
        )
```

## Processus d'Exécution Détaillé

### 1. Récupération des Prix

```python
def _get_price_data(strategy: Strategy) -> List[Dict]:
    """Récupère les données de prix."""
    # Priorité 1 : Yahoo Finance (si symbole validé)
    # Priorité 2 : Broker (via BrokerService)
    # Fallback : Prix actuel uniquement
```

### 2. Calcul des Signaux

```python
algorithm = strategy.get_algorithm_instance()
signal_result = algorithm.calculate_signals(price_data)
# Retourne: {'signal': 'BUY'|'SELL'|'HOLD', 'strength': float, 'reason': str}
```

### 3. Vérification des Conditions

```python
if not strategy.should_execute_order(signal_result):
    return  # Pas d'exécution

if signal_result['signal'] == 'HOLD':
    return  # Pas d'action
```

### 4. Calcul de la Quantité

```python
quantity = signal_result.get('calculated_quantity')
if not quantity:
    from .strategy_service import StrategyService
    service = StrategyService(user)
    quantity = service.calculate_optimal_quantity(strategy, side)
```

### 5. Passage d'Ordre

```python
from ..services.broker_service import BrokerService
broker_service = BrokerService(user)

result = broker_service.place_order(
    broker_account=strategy.broker_account,
    symbol=symbol,
    side=side,
    quantity=quantity,
    order_type='MARKET'
)
```

### 6. Enregistrement

```python
execution = StrategyExecution.objects.create(
    strategy=strategy,
    current_price=current_price,
    signal=signal_result['signal'],
    signal_strength=signal_result['strength'],
    order_executed=order_result['success'],
    order=order if order_result['success'] else None,
    # ...
)
```

## Gestion des Erreurs

### Erreurs de Prix

Si les prix ne peuvent pas être récupérés, l'exécution est annulée avec un message d'erreur.

### Erreurs d'Ordre

Si l'ordre échoue, l'exécution est enregistrée avec `error_message` et `order_executed=False`.

### Logging

Toutes les erreurs sont loggées avec le contexte complet pour le débogage.

## Performance

- Exécution asynchrone recommandée pour les stratégies automatiques
- Mise en cache des prix si applicable
- Limitation du nombre d'exécutions simultanées

---

**Voir aussi** :
- [STRATEGIES_SERVICES.md](STRATEGIES_SERVICES.md) : Services d'exécution
- [STRATEGIES_API.md](STRATEGIES_API.md) : Endpoints d'exécution








