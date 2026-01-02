# API REST - Système de Stratégies

## Vue d'ensemble

Ce document décrit les endpoints API REST pour le système de stratégies, utilisant Django REST Framework.

## StrategyViewSet

### Localisation

**Fichier** : `backend/apps/trading/api/views.py`

### Endpoints CRUD Standards

- `GET /api/strategies/` : Liste des stratégies de l'utilisateur
- `POST /api/strategies/` : Créer une nouvelle stratégie
- `GET /api/strategies/{id}/` : Détails d'une stratégie
- `PUT /api/strategies/{id}/` : Mettre à jour une stratégie complète
- `PATCH /api/strategies/{id}/` : Mettre à jour partielle
- `DELETE /api/strategies/{id}/` : Supprimer une stratégie

### Actions Personnalisées

#### 1. POST /api/strategies/{id}/execute/

Exécute une stratégie manuellement.

**Requête** :
```json
POST /api/strategies/1/execute/
```

**Réponse** :
```json
{
  "success": true,
  "signal": "BUY",
  "signal_strength": 0.85,
  "signal_reason": "Prix (95.50) en dessous du seuil bas (100.00)",
  "current_price": 95.50,
  "order_executed": true,
  "order": {
    "id": 123,
    "broker_order_id": "abc123",
    "status": "OPEN"
  },
  "execution": {
    "id": 456,
    "execution_time": "2025-12-31T10:30:00Z"
  }
}
```

#### 2. POST /api/strategies/{id}/calculate-signal/

Calcule un signal sans exécuter d'ordre (simulation).

**Requête** :
```json
POST /api/strategies/1/calculate-signal/
```

**Réponse** :
```json
{
  "signal": "BUY",
  "signal_strength": 0.85,
  "signal_reason": "Prix (95.50) en dessous du seuil bas (100.00)",
  "current_price": 95.50,
  "price_data_points": 100
}
```

#### 3. GET /api/strategies/{id}/executions/

Historique d'exécution d'une stratégie.

**Paramètres de requête** :
- `limit` : Nombre de résultats (défaut: 50)
- `offset` : Décalage pour pagination

**Réponse** :
```json
{
  "count": 150,
  "next": "/api/strategies/1/executions/?limit=50&offset=50",
  "previous": null,
  "results": [
    {
      "id": 456,
      "execution_time": "2025-12-31T10:30:00Z",
      "signal": "BUY",
      "signal_strength": 0.85,
      "current_price": 95.50,
      "order_executed": true,
      "order_size": 100.0
    }
  ]
}
```

#### 4. POST /api/strategies/{id}/activate/

Active une stratégie.

**Réponse** :
```json
{
  "status": "Strategy activated",
  "strategy": {
    "id": 1,
    "name": "RSI Strategy",
    "status": "active"
  }
}
```

#### 5. POST /api/strategies/{id}/deactivate/

Désactive une stratégie.

#### 6. GET /api/strategies/algorithms/

Liste des algorithmes disponibles.

**Réponse** :
```json
{
  "algorithms": {
    "threshold": "Seuils (Threshold)",
    "ma_crossover": "Moving Average Crossover",
    "rsi": "RSI (Relative Strength Index)",
    "bollinger": "Bollinger Bands",
    "macd": "MACD",
    "grid": "Grid Trading"
  },
  "parameters": {
    "threshold": [
      {
        "name": "threshold_low",
        "label": "Seuil bas",
        "type": "number",
        "default": 100.0
      },
      {
        "name": "threshold_high",
        "label": "Seuil haut",
        "type": "number",
        "default": 200.0
      }
    ]
  }
}
```

### Code du ViewSet

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class StrategyViewSet(viewsets.ModelViewSet):
    """ViewSet pour les stratégies."""
    serializer_class = StrategySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'algorithm_type', 'execution_mode']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'last_execution']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Strategy.objects.filter(user=self.request.user).select_related(
            'asset', 'all_asset', 'broker_account'
        )
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Exécuter une stratégie manuellement."""
        strategy = self.get_object()
        executor = StrategyExecutor()
        result = executor.execute_strategy(strategy, user=request.user)
        return Response(result, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def calculate_signal(self, request, pk=None):
        """Calculer un signal sans exécuter."""
        strategy = self.get_object()
        executor = StrategyExecutor()
        result = executor.calculate_signal(strategy)
        return Response(result, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """Historique d'exécution."""
        strategy = self.get_object()
        executions = StrategyExecution.objects.filter(
            strategy=strategy
        ).order_by('-execution_time')
        
        # Pagination
        page = self.paginate_queryset(executions)
        if page is not None:
            serializer = StrategyExecutionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = StrategyExecutionSerializer(executions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def algorithms(self, request):
        """Liste des algorithmes disponibles."""
        from ..services.algorithm_service import AlgorithmService
        service = AlgorithmService()
        return Response(service.get_algorithms_info())
```

## Serializers

### StrategySerializer

**Fichier** : `backend/apps/trading/api/serializers.py`

```python
class StrategySerializer(serializers.ModelSerializer):
    """Serializer pour les stratégies."""
    asset_name = serializers.CharField(source='asset.symbol', read_only=True)
    broker_name = serializers.CharField(source='broker_account.account_name', read_only=True)
    algorithm_type_display = serializers.CharField(source='get_algorithm_type_display', read_only=True)
    execution_mode_display = serializers.CharField(source='get_execution_mode_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Strategy
        fields = [
            'id', 'name', 'description', 'user',
            'asset', 'all_asset', 'asset_name',
            'broker_account', 'broker_name',
            'algorithm_type', 'algorithm_type_display',
            'parameters', 'execution_mode', 'execution_mode_display',
            'status', 'status_display',
            'check_frequency',
            'target_min_quantity', 'target_max_quantity', 'portfolio_quantity',
            'total_trades', 'successful_trades', 'total_pnl',
            'last_execution', 'is_active', 'is_automated',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'created_at', 'updated_at',
            'total_trades', 'successful_trades', 'total_pnl', 'last_execution'
        ]
```

### StrategyExecutionSerializer

```python
class StrategyExecutionSerializer(serializers.ModelSerializer):
    """Serializer pour l'historique d'exécution."""
    signal_display = serializers.CharField(source='get_signal_display', read_only=True)
    order_id = serializers.IntegerField(source='order.id', read_only=True)
    
    class Meta:
        model = StrategyExecution
        fields = [
            'id', 'strategy', 'execution_time',
            'current_price', 'signal', 'signal_display',
            'signal_strength', 'signal_reason',
            'order_executed', 'order', 'order_id',
            'order_size', 'order_price',
            'execution_duration', 'error_message'
        ]
        read_only_fields = ['id', 'execution_time']
```

## Permissions

Toutes les actions nécessitent une authentification (`IsAuthenticated`). Les stratégies sont filtrées automatiquement par utilisateur dans `get_queryset()`.

## Filtres et Recherche

- **Filtres** : `status`, `algorithm_type`, `execution_mode`
- **Recherche** : `name`, `description`
- **Tri** : `name`, `created_at`, `last_execution`

---

**Voir aussi** :
- [STRATEGIES_SERVICES.md](STRATEGIES_SERVICES.md) : Services utilisés par l'API
- [STRATEGIES_EXECUTION.md](STRATEGIES_EXECUTION.md) : Détails sur l'exécution








