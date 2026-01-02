# Services Backend - Système de Stratégies

## Vue d'ensemble

Ce document décrit les services backend pour la logique métier des stratégies.

## StrategyService

### Localisation

**Fichier** : `backend/apps/trading/services/strategy_service.py`

### Méthodes Principales

```python
class StrategyService:
    """Service pour la gestion des stratégies."""
    
    def __init__(self, user):
        self.user = user
    
    def calculate_portfolio_quantity(self, strategy: Strategy) -> float:
        """
        Calcule la quantité totale en portefeuille pour l'asset de la stratégie.
        
        Returns:
            float: Quantité totale (-1 si non calculable)
        """
        from ..models.trading import Position
        
        if not strategy.all_asset:
            return -1
        
        positions = Position.objects.filter(
            user=self.user,
            all_asset=strategy.all_asset,
            is_open=True
        )
        
        if not positions.exists():
            return 0
        
        total = sum(
            float(pos.quantity) if pos.side == Position.PositionSide.LONG else -float(pos.quantity)
            for pos in positions
        )
        
        strategy.portfolio_quantity = total
        strategy.save(update_fields=['portfolio_quantity'])
        return total
    
    def calculate_optimal_quantity(
        self,
        strategy: Strategy,
        side: str
    ) -> float:
        """
        Calcule la quantité optimale à trader selon l'objectif.
        
        Args:
            strategy: Instance Strategy
            side: 'BUY' ou 'SELL'
        
        Returns:
            float: Quantité optimale (0 si objectif atteint)
        """
        if strategy.portfolio_quantity == -1:
            self.calculate_portfolio_quantity(strategy)
        
        if strategy.portfolio_quantity == -1:
            return 0
        
        current = float(strategy.portfolio_quantity)
        max_size = float(strategy.parameters.get('order_size', 1000))
        
        if side.upper() == 'BUY' and strategy.target_max_quantity > 0:
            optimal = float(strategy.target_max_quantity) - current
            return max(0, min(optimal, max_size))
        
        elif side.upper() == 'SELL' and strategy.target_min_quantity > 0:
            optimal = current - float(strategy.target_min_quantity)
            return max(0, min(optimal, max_size))
        
        return 0
    
    def validate_strategy(self, strategy: Strategy) -> Dict[str, Any]:
        """
        Valide une stratégie avant activation.
        
        Returns:
            Dict avec 'valid' (bool) et 'errors' (list)
        """
        errors = []
        
        if not strategy.asset and not strategy.all_asset:
            errors.append("Asset requis")
        
        if not strategy.broker_account:
            errors.append("Compte broker requis")
        
        if not strategy.algorithm_type:
            errors.append("Type d'algorithme requis")
        
        if strategy.target_min_quantity > strategy.target_max_quantity:
            errors.append("Quantité min > quantité max")
        
        if strategy.check_frequency < 1 or strategy.check_frequency > 1440:
            errors.append("Fréquence invalide (1-1440 minutes)")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
```

## AlgorithmService

### Localisation

**Fichier** : `backend/apps/trading/services/algorithm_service.py`

### Méthodes Principales

```python
class AlgorithmService:
    """Service pour la gestion des algorithmes."""
    
    def get_available_algorithms(self) -> Dict[str, str]:
        """Retourne la liste des algorithmes disponibles."""
        from ..algorithms.factory import AlgorithmFactory
        return AlgorithmFactory.get_available_algorithms()
    
    def get_algorithm_parameters(self, algorithm_type: str) -> List[Dict]:
        """
        Retourne les paramètres nécessaires pour un algorithme.
        
        Returns:
            Liste de dicts avec 'name', 'label', 'type', 'default'
        """
        # Configuration des paramètres par algorithme
        PARAMETERS = {
            'threshold': [
                {'name': 'threshold_low', 'label': 'Seuil bas', 'type': 'number', 'default': 100.0},
                {'name': 'threshold_high', 'label': 'Seuil haut', 'type': 'number', 'default': 200.0},
                {'name': 'order_size', 'label': 'Taille ordre', 'type': 'number', 'default': 1.0},
                {'name': 'stop_loss', 'label': 'Stop Loss (%)', 'type': 'number', 'default': 5.0}
            ],
            'rsi': [
                {'name': 'rsi_period', 'label': 'Période RSI', 'type': 'number', 'default': 14},
                {'name': 'rsi_low', 'label': 'Seuil bas RSI', 'type': 'number', 'default': 30},
                {'name': 'rsi_high', 'label': 'Seuil haut RSI', 'type': 'number', 'default': 70},
                {'name': 'order_size', 'label': 'Taille ordre', 'type': 'number', 'default': 1.0},
                {'name': 'stop_loss', 'label': 'Stop Loss (%)', 'type': 'number', 'default': 5.0}
            ],
            # ... autres algorithmes
        }
        
        return PARAMETERS.get(algorithm_type, [])
    
    def validate_parameters(
        self,
        algorithm_type: str,
        parameters: Dict
    ) -> Dict[str, Any]:
        """
        Valide les paramètres d'un algorithme.
        
        Returns:
            Dict avec 'valid' (bool) et 'errors' (list)
        """
        errors = []
        required_params = self.get_algorithm_parameters(algorithm_type)
        
        for param in required_params:
            if param['name'] not in parameters:
                if 'default' in param:
                    continue  # Paramètre optionnel avec défaut
                errors.append(f"Paramètre requis: {param['name']}")
        
        # Validations spécifiques par algorithme
        if algorithm_type == 'rsi':
            rsi_low = parameters.get('rsi_low', 30)
            rsi_high = parameters.get('rsi_high', 70)
            if rsi_low >= rsi_high:
                errors.append("RSI low doit être < RSI high")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def get_algorithms_info(self) -> Dict:
        """Retourne toutes les informations sur les algorithmes."""
        algorithms = self.get_available_algorithms()
        parameters = {}
        
        for algo_type in algorithms.keys():
            parameters[algo_type] = self.get_algorithm_parameters(algo_type)
        
        return {
            'algorithms': algorithms,
            'parameters': parameters
        }
```

## StrategyExecutor

### Localisation

**Fichier** : `backend/apps/trading/services/strategy_executor.py`

### Méthodes Principales

```python
class StrategyExecutor:
    """Service pour l'exécution des stratégies."""
    
    def __init__(self):
        from .broker_service import BrokerService
        self.broker_service = BrokerService
    
    def execute_strategy(
        self,
        strategy: Strategy,
        user=None
    ) -> Dict[str, Any]:
        """
        Exécute une stratégie complète.
        
        Processus :
        1. Récupérer les prix
        2. Calculer les signaux
        3. Vérifier si ordre doit être exécuté
        4. Passer l'ordre si nécessaire
        5. Enregistrer l'exécution
        
        Returns:
            Dict avec les résultats de l'exécution
        """
        import time
        start_time = time.time()
        
        try:
            # 1. Récupérer les prix
            price_data = self._get_price_data(strategy)
            if not price_data:
                return {
                    'success': False,
                    'error': 'Impossible de récupérer les prix'
                }
            
            current_price = float(price_data[-1]['close'])
            
            # 2. Calculer les signaux
            signal_result = self.calculate_signal(strategy, price_data)
            
            # 3. Vérifier si ordre doit être exécuté
            order_executed = False
            order = None
            
            if strategy.should_execute_order(signal_result):
                # 4. Passer l'ordre
                order_result = self._execute_order(strategy, signal_result, user)
                order_executed = order_result.get('success', False)
                order = order_result.get('order')
            
            # 5. Enregistrer l'exécution
            execution = StrategyExecution.objects.create(
                strategy=strategy,
                current_price=current_price,
                signal=signal_result['signal'],
                signal_strength=signal_result.get('strength', 0.0),
                signal_reason=signal_result.get('reason', ''),
                order_executed=order_executed,
                order=order,
                order_size=signal_result.get('calculated_quantity'),
                order_price=current_price if order_executed else None,
                execution_duration=time.time() - start_time
            )
            
            # Mettre à jour last_execution
            strategy.last_execution = timezone.now()
            strategy.save(update_fields=['last_execution'])
            
            return {
                'success': True,
                'signal': signal_result['signal'],
                'signal_strength': signal_result.get('strength', 0.0),
                'signal_reason': signal_result.get('reason', ''),
                'current_price': current_price,
                'order_executed': order_executed,
                'order': OrderSerializer(order).data if order else None,
                'execution': StrategyExecutionSerializer(execution).data
            }
        
        except Exception as e:
            logger.exception(f"Erreur lors de l'exécution de la stratégie {strategy.id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def calculate_signal(
        self,
        strategy: Strategy,
        price_data: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Calcule un signal sans exécuter d'ordre.
        
        Returns:
            Dict avec 'signal', 'strength', 'reason'
        """
        if price_data is None:
            price_data = self._get_price_data(strategy)
        
        if not price_data:
            return {
                'signal': 'HOLD',
                'strength': 0.0,
                'reason': 'Impossible de récupérer les prix'
            }
        
        algorithm = strategy.get_algorithm_instance()
        signal_result = algorithm.calculate_signals(price_data)
        
        return {
            'signal': signal_result.get('signal', 'HOLD'),
            'signal_strength': signal_result.get('strength', 0.0),
            'signal_reason': signal_result.get('reason', ''),
            'current_price': float(price_data[-1]['close']),
            'price_data_points': len(price_data)
        }
    
    def _get_price_data(self, strategy: Strategy) -> List[Dict]:
        """Récupère les données de prix pour l'asset."""
        from ..services.data_providers.yahoo_finance import YahooFinanceService
        
        symbol = strategy.all_asset.symbol if strategy.all_asset else strategy.asset.symbol
        # Nettoyer le symbole (enlever :XNAS, .PA, etc.)
        clean_symbol = symbol.split(':')[0].split('.')[0].strip().upper()
        
        yahoo_service = YahooFinanceService()
        if yahoo_service.is_available:
            # Utiliser le symbole Yahoo validé si disponible
            yahoo_symbol = strategy.all_asset.symbole_yahoo if strategy.all_asset else clean_symbol
            if yahoo_symbol and yahoo_symbol not in ['Not_searched', 'not_found', 'manual']:
                price_data = yahoo_service.get_historical_data(yahoo_symbol, period='1mo')
                if price_data:
                    return price_data
        
        return []
    
    def _execute_order(
        self,
        strategy: Strategy,
        signal_result: Dict,
        user
    ) -> Dict[str, Any]:
        """Passe un ordre via le broker."""
        from ..api.views import OrderViewSet
        
        side = signal_result['signal']  # BUY ou SELL
        
        # Calculer la quantité
        quantity = signal_result.get('calculated_quantity')
        if not quantity:
            from .strategy_service import StrategyService
            service = StrategyService(user)
            quantity = service.calculate_optimal_quantity(strategy, side)
        
        if quantity <= 0:
            return {'success': False, 'error': 'Quantité invalide'}
        
        # Créer l'ordre via l'API
        order_data = {
            'broker_account_id': strategy.broker_account.id,
            'symbol': strategy.all_asset.symbol if strategy.all_asset else strategy.asset.symbol,
            'side': side,
            'quantity': str(quantity),
            'order_type': 'MARKET',
            'all_asset_id': strategy.all_asset.id if strategy.all_asset else None,
            'asset_id': strategy.asset.id if strategy.asset else None
        }
        
        # Appel à OrderViewSet.place()
        # (simulation - en réalité via BrokerService)
        from .broker_service import BrokerService
        broker_service = BrokerService(user)
        
        result = broker_service.place_order(
            broker_account=strategy.broker_account,
            symbol=order_data['symbol'],
            side=side,
            quantity=quantity,
            order_type='MARKET'
        )
        
        return result
```

---

**Voir aussi** :
- [STRATEGIES_EXECUTION.md](STRATEGIES_EXECUTION.md) : Détails sur l'exécution
- [STRATEGIES_ALGORITHMS.md](STRATEGIES_ALGORITHMS.md) : Algorithmes utilisés








