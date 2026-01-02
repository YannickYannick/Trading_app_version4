# Algorithmes de Trading - Système de Stratégies

## Vue d'ensemble

Ce document décrit l'architecture et l'implémentation des algorithmes de trading disponibles dans le système. Tous les algorithmes héritent d'une classe abstraite `TradingAlgorithm` et implémentent la méthode `calculate_signals()`.

## Architecture

### Pattern Strategy

Le système utilise le pattern Strategy pour permettre l'ajout facile de nouveaux algorithmes :

```python
# Classe abstraite
class TradingAlgorithm(ABC):
    @abstractmethod
    def calculate_signals(self, price_data: List[Dict]) -> Dict:
        """Calcule les signaux d'achat/vente."""
        pass

# Implémentation concrète
class ThresholdAlgorithm(TradingAlgorithm):
    def calculate_signals(self, price_data: List[Dict]) -> Dict:
        # Implémentation spécifique
        pass
```

### Structure des Fichiers

```
backend/apps/trading/algorithms/
├── __init__.py              # Exports principaux
├── base.py                  # TradingAlgorithm (classe abstraite)
├── threshold.py             # ThresholdAlgorithm
├── ma_crossover.py          # MovingAverageCrossoverAlgorithm
├── rsi.py                   # RSIAlgorithm
├── bollinger.py             # BollingerBandsAlgorithm
├── macd.py                  # MACDAlgorithm
├── grid.py                  # GridTradingAlgorithm
└── factory.py               # AlgorithmFactory
```

### Format de Retour

Tous les algorithmes retournent un dictionnaire standardisé :

```python
{
    'signal': 'BUY' | 'SELL' | 'HOLD',
    'strength': float,  # 0.0 à 1.0
    'reason': str,      # Explication du signal
    'auto_quantity': bool,  # Optionnel : si True, utiliser calculated_quantity
    'calculated_quantity': float  # Optionnel : quantité calculée automatiquement
}
```

## Classe Abstraite TradingAlgorithm

### Localisation

**Fichier** : `backend/apps/trading/algorithms/base.py`

### Code

```python
"""
Classe abstraite pour les algorithmes de trading.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import numpy as np


class TradingAlgorithm(ABC):
    """Classe abstraite pour les algorithmes de trading."""
    
    def __init__(self, parameters: Dict, strategy=None):
        """
        Initialise l'algorithme.
        
        Args:
            parameters: Dict des paramètres de l'algorithme
            strategy: Instance de Strategy (optionnel, pour accéder aux quantités cibles)
        """
        self.parameters = parameters or {}
        self.strategy = strategy
    
    @abstractmethod
    def calculate_signals(self, price_data: List[Dict]) -> Dict:
        """
        Calcule les signaux d'achat/vente basés sur les données de prix.
        
        Args:
            price_data: Liste de dicts avec 'close', 'open', 'high', 'low', 'volume'
        
        Returns:
            Dict avec 'signal', 'strength', 'reason'
        """
        pass
    
    def _get_prices(self, price_data: List[Dict]) -> np.ndarray:
        """Extrait les prix de clôture depuis price_data."""
        if not price_data:
            return np.array([])
        return np.array([float(d.get('close', 0)) for d in price_data])
    
    def _calculate_sma(self, prices: np.ndarray, period: int) -> float:
        """Calcule la Simple Moving Average."""
        if len(prices) < period:
            return 0.0
        return float(np.mean(prices[-period:]))
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calcule l'Exponential Moving Average."""
        if len(prices) < period:
            return 0.0
        
        alpha = 2.0 / (period + 1.0)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        
        return float(ema)
```

## Algorithmes Disponibles

### 1. ThresholdAlgorithm - Seuils Simple

**Fichier** : `backend/apps/trading/algorithms/threshold.py`

**Principe** :
- Acheter quand prix ≤ seuil bas
- Vendre quand prix ≥ seuil haut
- Gère automatiquement les quantités cibles si configurées

**Paramètres** :
```python
{
    'threshold_low': float,    # Seuil bas (ex: 100.0)
    'threshold_high': float,   # Seuil haut (ex: 200.0)
    'order_size': float,       # Limite max par trade (ex: 1000.0)
    'stop_loss': float         # Stop Loss en % (ex: 5.0)
}
```

**Implémentation** :

```python
class ThresholdAlgorithm(TradingAlgorithm):
    """Algorithme basé sur des seuils de prix."""
    
    def calculate_signals(self, price_data: List[Dict]) -> Dict:
        if not price_data:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas de données'}
        
        current_price = float(price_data[-1]['close'])
        threshold_low = float(self.parameters.get('threshold_low', 0))
        threshold_high = float(self.parameters.get('threshold_high', float('inf')))
        
        # Gestion des quantités cibles si configurées
        target_min_quantity = 0
        target_max_quantity = 0
        portfolio_quantity = -1
        
        if self.strategy:
            target_min_quantity = float(self.strategy.target_min_quantity or 0)
            target_max_quantity = float(self.strategy.target_max_quantity or 0)
            if self.strategy.portfolio_quantity != -1:
                portfolio_quantity = float(self.strategy.portfolio_quantity)
        
        # Signal BUY
        if current_price <= threshold_low:
            if target_max_quantity > 0 and portfolio_quantity >= 0:
                if portfolio_quantity < target_max_quantity:
                    # Calculer quantité automatiquement
                    quantity_to_buy = target_max_quantity - portfolio_quantity
                    max_trade_size = float(self.parameters.get('order_size', 1000))
                    final_quantity = min(quantity_to_buy, max_trade_size)
                    
                    strength = min(1.0, (threshold_low - current_price) / threshold_low * 2)
                    return {
                        'signal': 'BUY',
                        'strength': strength,
                        'reason': f'Prix ({current_price}) en dessous du seuil bas ({threshold_low})',
                        'auto_quantity': True,
                        'calculated_quantity': final_quantity
                    }
            else:
                strength = min(1.0, (threshold_low - current_price) / threshold_low * 2)
                return {
                    'signal': 'BUY',
                    'strength': strength,
                    'reason': f'Prix ({current_price}) en dessous du seuil bas ({threshold_low})'
                }
        
        # Signal SELL
        elif current_price >= threshold_high:
            if target_min_quantity > 0 and portfolio_quantity >= 0:
                if portfolio_quantity > target_min_quantity:
                    quantity_to_sell = portfolio_quantity - target_min_quantity
                    max_trade_size = float(self.parameters.get('order_size', 1000))
                    final_quantity = min(quantity_to_sell, max_trade_size)
                    
                    strength = min(1.0, (current_price - threshold_high) / threshold_high * 2)
                    return {
                        'signal': 'SELL',
                        'strength': strength,
                        'reason': f'Prix ({current_price}) au-dessus du seuil haut ({threshold_high})',
                        'auto_quantity': True,
                        'calculated_quantity': final_quantity
                    }
            else:
                strength = min(1.0, (current_price - threshold_high) / threshold_high * 2)
                return {
                    'signal': 'SELL',
                    'strength': strength,
                    'reason': f'Prix ({current_price}) au-dessus du seuil haut ({threshold_high})'
                }
        
        return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Prix dans la zone neutre'}
```

**Utilisation** :
- Simple et efficace
- Parfait pour range trading
- Gère automatiquement les quantités cibles

### 2. MovingAverageCrossoverAlgorithm

**Fichier** : `backend/apps/trading/algorithms/ma_crossover.py`

**Principe** :
- Calculer deux moyennes mobiles (MA1 courte, MA2 longue)
- Signal BUY quand MA1 croise au-dessus de MA2
- Signal SELL quand MA1 croise en-dessous de MA2

**Paramètres** :
```python
{
    'ma1_period': int,        # Période MA1 (ex: 20)
    'ma2_period': int,        # Période MA2 (ex: 50)
    'order_size': float,      # Taille ordre
    'stop_loss': float        # Stop Loss en %
}
```

**Implémentation** :

```python
class MovingAverageCrossoverAlgorithm(TradingAlgorithm):
    """Algorithme basé sur le croisement de moyennes mobiles."""
    
    def calculate_signals(self, price_data: List[Dict]) -> Dict:
        if len(price_data) < 50:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données'}
        
        prices = self._get_prices(price_data)
        ma1_period = int(self.parameters.get('ma1_period', 20))
        ma2_period = int(self.parameters.get('ma2_period', 50))
        
        # Calculer les moyennes mobiles
        ma1 = self._calculate_sma(prices, ma1_period)
        ma2 = self._calculate_sma(prices, ma2_period)
        
        # Calculer les MA précédentes pour détecter le croisement
        if len(prices) < ma1_period + 1 or len(prices) < ma2_period + 1:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données historiques'}
        
        ma1_prev = self._calculate_sma(prices[:-1], ma1_period)
        ma2_prev = self._calculate_sma(prices[:-1], ma2_period)
        
        # Détecter le croisement
        if ma1 > ma2 and ma1_prev <= ma2_prev:
            strength = min(1.0, abs(ma1 - ma2) / ma2)
            return {
                'signal': 'BUY',
                'strength': strength,
                'reason': f'Croisement haussier: MA{ma1_period} ({ma1:.2f}) > MA{ma2_period} ({ma2:.2f})'
            }
        elif ma1 < ma2 and ma1_prev >= ma2_prev:
            strength = min(1.0, abs(ma2 - ma1) / ma2)
            return {
                'signal': 'SELL',
                'strength': strength,
                'reason': f'Croisement baissier: MA{ma1_period} ({ma1:.2f}) < MA{ma2_period} ({ma2:.2f})'
            }
        
        return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas de croisement détecté'}
```

### 3. RSIAlgorithm

**Fichier** : `backend/apps/trading/algorithms/rsi.py`

**Principe** :
- Calcule le RSI (indicateur 0-100)
- Signal BUY si RSI ≤ seuil bas (survente)
- Signal SELL si RSI ≥ seuil haut (surachat)

**Paramètres** :
```python
{
    'rsi_period': int,        # Période RSI (ex: 14)
    'rsi_low': float,         # Seuil bas RSI (ex: 30)
    'rsi_high': float,        # Seuil haut RSI (ex: 70)
    'order_size': float,      # Taille ordre
    'stop_loss': float        # Stop Loss en %
}
```

**Implémentation** :

```python
class RSIAlgorithm(TradingAlgorithm):
    """Algorithme basé sur le Relative Strength Index."""
    
    def _calculate_rsi(self, prices: np.ndarray, period: int) -> float:
        """Calcule le RSI."""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi)
    
    def calculate_signals(self, price_data: List[Dict]) -> Dict:
        if len(price_data) < 30:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données'}
        
        prices = self._get_prices(price_data)
        rsi_period = int(self.parameters.get('rsi_period', 14))
        rsi_low = float(self.parameters.get('rsi_low', 30))
        rsi_high = float(self.parameters.get('rsi_high', 70))
        
        rsi = self._calculate_rsi(prices, rsi_period)
        
        if rsi <= rsi_low:
            strength = min(1.0, (rsi_low - rsi) / rsi_low)
            return {
                'signal': 'BUY',
                'strength': strength,
                'reason': f'RSI ({rsi:.2f}) en survente (seuil: {rsi_low})'
            }
        elif rsi >= rsi_high:
            strength = min(1.0, (rsi - rsi_high) / (100 - rsi_high))
            return {
                'signal': 'SELL',
                'strength': strength,
                'reason': f'RSI ({rsi:.2f}) en surachat (seuil: {rsi_high})'
            }
        else:
            return {
                'signal': 'HOLD',
                'strength': 0.0,
                'reason': f'RSI ({rsi:.2f}) dans la zone neutre'
            }
```

### 4. BollingerBandsAlgorithm

**Fichier** : `backend/apps/trading/algorithms/bollinger.py`

**Principe** :
- Calcule une moyenne mobile et deux bandes (supérieure/inférieure)
- Signal BUY quand prix touche la bande basse
- Signal SELL quand prix touche la bande haute

**Paramètres** :
```python
{
    'bb_period': int,         # Période (ex: 20)
    'bb_std': float,          # Écart-type (ex: 2.0)
    'order_size': float,      # Taille ordre
    'stop_loss': float        # Stop Loss en %
}
```

**Implémentation** :

```python
class BollingerBandsAlgorithm(TradingAlgorithm):
    """Algorithme basé sur les Bandes de Bollinger."""
    
    def calculate_signals(self, price_data: List[Dict]) -> Dict:
        if len(price_data) < 20:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données'}
        
        prices = self._get_prices(price_data)
        bb_period = int(self.parameters.get('bb_period', 20))
        bb_std = float(self.parameters.get('bb_std', 2.0))
        
        if len(prices) < bb_period:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données'}
        
        # Calculer les bandes de Bollinger
        sma = self._calculate_sma(prices, bb_period)
        std = float(np.std(prices[-bb_period:]))
        
        upper_band = sma + (bb_std * std)
        lower_band = sma - (bb_std * std)
        
        current_price = prices[-1]
        
        if current_price <= lower_band:
            strength = min(1.0, (lower_band - current_price) / lower_band)
            return {
                'signal': 'BUY',
                'strength': strength,
                'reason': f'Prix ({current_price:.2f}) touche la bande basse ({lower_band:.2f})'
            }
        elif current_price >= upper_band:
            strength = min(1.0, (current_price - upper_band) / upper_band)
            return {
                'signal': 'SELL',
                'strength': strength,
                'reason': f'Prix ({current_price:.2f}) touche la bande haute ({upper_band:.2f})'
            }
        
        return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Prix dans les bandes'}
```

### 5. MACDAlgorithm

**Fichier** : `backend/apps/trading/algorithms/macd.py`

**Principe** :
- Calcule la ligne MACD (différence entre EMA rapide et EMA lente)
- Calcule la ligne de signal (EMA de la ligne MACD)
- Signal BUY quand MACD croise au-dessus du signal
- Signal SELL quand MACD croise en-dessous du signal

**Paramètres** :
```python
{
    'macd_fast': int,         # Période rapide (ex: 12)
    'macd_slow': int,         # Période lente (ex: 26)
    'macd_signal': int,       # Période signal (ex: 9)
    'order_size': float,      # Taille ordre
    'stop_loss': float        # Stop Loss en %
}
```

### 6. GridTradingAlgorithm

**Fichier** : `backend/apps/trading/algorithms/grid.py`

**Principe** :
- Définit une grille de prix entre min et max
- Place des ordres d'achat aux niveaux bas
- Place des ordres de vente aux niveaux hauts
- Stratégie de trading de range

**Paramètres** :
```python
{
    'grid_min': float,        # Prix minimum (ex: 100.0)
    'grid_max': float,        # Prix maximum (ex: 200.0)
    'grid_levels': int,       # Nombre de niveaux (ex: 10)
    'order_size': float,      # Taille ordre
    'stop_loss': float        # Stop Loss en %
}
```

## AlgorithmFactory

**Fichier** : `backend/apps/trading/algorithms/factory.py`

### Code

```python
"""
Factory pour créer des instances d'algorithmes.
"""
from typing import Dict, Optional
from .base import TradingAlgorithm
from .threshold import ThresholdAlgorithm
from .ma_crossover import MovingAverageCrossoverAlgorithm
from .rsi import RSIAlgorithm
from .bollinger import BollingerBandsAlgorithm
from .macd import MACDAlgorithm
from .grid import GridTradingAlgorithm


class AlgorithmFactory:
    """Factory pour créer des instances d'algorithmes."""
    
    ALGORITHMS = {
        'threshold': ThresholdAlgorithm,
        'ma_crossover': MovingAverageCrossoverAlgorithm,
        'rsi': RSIAlgorithm,
        'bollinger': BollingerBandsAlgorithm,
        'macd': MACDAlgorithm,
        'grid': GridTradingAlgorithm,
    }
    
    @classmethod
    def create_algorithm(
        cls,
        algorithm_type: str,
        parameters: Dict,
        strategy=None
    ) -> TradingAlgorithm:
        """
        Crée une instance d'algorithme.
        
        Args:
            algorithm_type: Type d'algorithme ('threshold', 'rsi', etc.)
            parameters: Dict des paramètres
            strategy: Instance de Strategy (optionnel)
        
        Returns:
            Instance de TradingAlgorithm
        
        Raises:
            ValueError: Si le type d'algorithme est inconnu
        """
        if algorithm_type not in cls.ALGORITHMS:
            raise ValueError(f"Algorithme inconnu: {algorithm_type}")
        
        algorithm_class = cls.ALGORITHMS[algorithm_type]
        return algorithm_class(parameters, strategy)
    
    @classmethod
    def get_available_algorithms(cls) -> Dict[str, str]:
        """Retourne la liste des algorithmes disponibles."""
        return {
            'threshold': 'Seuils (Threshold)',
            'ma_crossover': 'Moving Average Crossover',
            'rsi': 'RSI (Relative Strength Index)',
            'bollinger': 'Bollinger Bands',
            'macd': 'MACD',
            'grid': 'Grid Trading',
        }
```

## Utilisation

### Dans le Service

```python
from ..algorithms.factory import AlgorithmFactory

# Créer une instance d'algorithme
algorithm = AlgorithmFactory.create_algorithm(
    algorithm_type='rsi',
    parameters={'rsi_period': 14, 'rsi_low': 30, 'rsi_high': 70},
    strategy=strategy_instance
)

# Calculer les signaux
signal_result = algorithm.calculate_signals(price_data)
```

---

**Voir aussi** :
- [STRATEGIES_SERVICES.md](STRATEGIES_SERVICES.md) : Services utilisant les algorithmes
- [STRATEGIES_EXECUTION.md](STRATEGIES_EXECUTION.md) : Exécution des stratégies








