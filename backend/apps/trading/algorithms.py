"""
Algorithmes de trading pour les stratégies.
"""
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class TradingAlgorithm(ABC):
    """Classe de base pour tous les algorithmes de trading"""
    
    def __init__(self, parameters: Dict, strategy=None):
        self.parameters = parameters
        self.strategy = strategy
    
    @abstractmethod
    def calculate_signals(self, price_data: List[Dict]) -> Dict:
        """
        Calcule les signaux d'achat/vente basés sur l'algorithme
        
        Args:
            price_data: Liste de dictionnaires avec 'date', 'open', 'high', 'low', 'close', 'volume'
            
        Returns:
            Dict avec 'signal' ('BUY', 'SELL', 'HOLD'), 'strength' (0-1), 'reason'
        """
        pass
    
    def _get_prices(self, price_data: List[Dict]) -> np.ndarray:
        """Extrait les prix de fermeture des données"""
        return np.array([float(candle['close']) for candle in price_data])
    
    def _get_volumes(self, price_data: List[Dict]) -> np.ndarray:
        """Extrait les volumes des données"""
        return np.array([float(candle.get('volume', 0)) for candle in price_data])


class ThresholdAlgorithm(TradingAlgorithm):
    """
    Algorithme de seuils avec gestion avancée du portfolio.
    
    Achète en dessous de threshold_low, vend au-dessus de threshold_high.
    Gère les contraintes de quantité (min/max), les ordres en attente,
    et la taille de trade fixe.
    """
    
    def calculate_signals(self, price_data: List[Dict], portfolio: Dict = None, pending_orders: List[Dict] = None) -> Dict:
        """
        Calcule les signaux d'achat/vente avec gestion du portfolio.
        
        Args:
            price_data: Liste de dictionnaires avec 'date', 'open', 'high', 'low', 'close', 'volume'
            portfolio: Dict avec 'cash_total' et 'quantity_total' (optionnel)
            pending_orders: Liste d'ordres en attente avec 'type', 'qty', 'price' (optionnel)
            
        Returns:
            Dict avec 'signal' ('BUY', 'SELL', 'HOLD', 'SKIP'), 'strength', 'reason', 'quantity'
        """
        if len(price_data) < 1:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données', 'quantity': 0}
        
        # Prix actuel (arrondi à 8 décimales pour éviter les erreurs de précision)
        current_price = round(float(price_data[-1]['close']), 8)
        
        # Paramètres de configuration
        threshold_low = self.parameters.get('threshold_low', 0)
        threshold_high = self.parameters.get('threshold_high', float('inf'))
        min_qty = self.parameters.get('min_qty', 0)  # Floor (plancher)
        max_qty = self.parameters.get('max_qty', float('inf'))  # Cap (plafond)
        trade_size = self.parameters.get('trade_size', 1.0)  # Quantité fixe par ordre
        
        # Si pas de portfolio fourni, utiliser la logique simple (rétrocompatibilité)
        if portfolio is None:
            return self._simple_signal_logic(current_price, threshold_low, threshold_high)
        
        # Extraction des données du portfolio (arrondies à 8 décimales)
        cash_total = round(float(portfolio.get('cash_total', 0)), 8)
        quantity_total = round(float(portfolio.get('quantity_total', 0)), 8)
        
        # Initialisation des ordres en attente
        if pending_orders is None:
            pending_orders = []
        
        # ========================================
        # CALCUL DES DISPONIBILITÉS RÉELLES
        # ========================================
        locked_cash, locked_qty = self._calculate_locked_resources(pending_orders)
        
        available_cash = round(cash_total - locked_cash, 8)
        available_qty = round(quantity_total - locked_qty, 8)

        # ========================================
        # CONSTRUCTION DES INFORMATIONS DE DEBUG
        # ========================================
        # Helper pour sérialiser JSON (Infinity -> "Infinity")
        def safe_json(val):
            if val == float('inf'): return "Infinity"
            if val == float('-inf'): return "-Infinity"
            return val

        debug_info = {
            'inputs': {
                'current_price': current_price,
                'threshold_low': safe_json(threshold_low),
                'threshold_high': safe_json(threshold_high),
                'min_qty': safe_json(min_qty),
                'max_qty': safe_json(max_qty),
                'trade_size': safe_json(trade_size),
                'portfolio': {
                    'cash_total': cash_total,
                    'quantity_total': quantity_total,
                    'locked_cash': locked_cash,
                    'locked_qty': locked_qty,
                    'available_cash': available_cash,
                    'available_qty': available_qty
                }
            },
            'logic': []
        }

        # ========================================
        # LOGIQUE DE DÉCISION
        # ========================================
        
        # SIGNAL ACHAT : Prix <= threshold_low
        if current_price <= threshold_low:
            debug_info['logic'].append(f"Prix ({current_price}) <= Seuil bas ({threshold_low}) -> Analyse signal ACHAT")
            result = self._evaluate_buy_signal(
                current_price, threshold_low, quantity_total, max_qty,
                trade_size, available_cash, debug_info
            )
        
        # SIGNAL VENTE : Prix >= threshold_high
        elif current_price >= threshold_high:
            debug_info['logic'].append(f"Prix ({current_price}) >= Seuil haut ({threshold_high}) -> Analyse signal VENTE")
            result = self._evaluate_sell_signal(
                current_price, threshold_high, quantity_total, min_qty,
                trade_size, available_qty, debug_info
            )
        
        # ZONE NEUTRE : Pas de signal
        else:
            debug_info['logic'].append(f"Prix ({current_price}) entre seuils [{threshold_low} - {threshold_high}] -> Zone NEUTRE")
            result = {
                'signal': 'HOLD',
                'strength': 0.0,
                'reason': f'Prix ({current_price}) dans la zone neutre [{threshold_low} - {threshold_high}]',
                'quantity': 0
            }
        
        # Fusionner les infos de debug
        result['debug_info'] = debug_info
        return result
    
    def _calculate_locked_resources(self, pending_orders: List[Dict]) -> tuple:
        """
        Calcule les ressources bloquées par les ordres en attente.
        
        Args:
            pending_orders: Liste d'ordres avec 'type', 'qty', 'price'
            
        Returns:
            Tuple (locked_cash, locked_qty) arrondis à 8 décimales
        """
        locked_cash = 0.0
        locked_qty = 0.0
        
        for order in pending_orders:
            order_type = order.get('type', '').upper()
            qty = float(order.get('qty', 0))
            price = float(order.get('price', 0))
            
            if order_type == 'BUY':
                # Les ordres d'achat bloquent du cash
                locked_cash += qty * price
            elif order_type == 'SELL':
                # Les ordres de vente bloquent de la quantité
                locked_qty += qty
        
        return round(locked_cash, 8), round(locked_qty, 8)
    
    def _evaluate_buy_signal(self, current_price: float, threshold_low: float,
                            quantity_total: float, max_qty: float,
                            trade_size: float, available_cash: float, debug_info: Dict) -> Dict:
        """
        Évalue si un signal d'achat peut être généré.
        """
        # Calcul de l'espace restant avant le plafond
        space_to_max = round(max_qty - quantity_total, 8)
        debug_info['logic'].append(f"Espace avant max: {space_to_max} (Max {max_qty} - Actuel {quantity_total})")
        
        # CONDITION D'ARRÊT 1 : Plafond atteint
        if space_to_max <= 0:
            debug_info['logic'].append("❌ Plafond atteint")
            return {
                'signal': 'SKIP',
                'strength': 0.0,
                'reason': f'Max Cap atteint : quantité actuelle ({quantity_total}) >= max autorisé ({max_qty})',
                'quantity': 0
            }
        
        # Quantité théorique (limitée par l'espace disponible)
        desired_qty = min(trade_size, space_to_max)
        debug_info['logic'].append(f"Quantité cible: {desired_qty} (min(TradeSize {trade_size}, Espace {space_to_max}))")
        
        # Vérification et ajustement selon les fonds disponibles
        max_affordable_qty = available_cash / current_price if current_price > 0 else 0
        
        if max_affordable_qty < desired_qty:
            qty_to_buy = round(max_affordable_qty, 8)
            debug_info['logic'].append(f"⚠️ Fonds limités ({available_cash}€): ajustement Qté {desired_qty} -> {qty_to_buy}")
        else:
            qty_to_buy = round(desired_qty, 8)
            
        # Coût de l'ordre
        order_cost = round(qty_to_buy * current_price, 8)
        debug_info['logic'].append(f"Coût estimé: {order_cost}€ ({qty_to_buy} * {current_price}€)")
        
        # CONDITION D'ARRÊT 2 : Quantité nulle ou insignifiante
        if qty_to_buy <= 0:
            debug_info['logic'].append(f"❌ Quantité nulle (Fonds insuffisants ou prix trop élevé)")
            return {
                'signal': 'SKIP',
                'strength': 0.0,
                'reason': f'Quantité calculée nulle (Dispo: {available_cash}€)',
                'quantity': 0
            }
        
        # SIGNAL VALIDE : Générer l'ordre d'achat
        strength = min(1.0, (threshold_low - current_price) / threshold_low * 2) if threshold_low > 0 else 0.5
        debug_info['logic'].append("✅ Conditions remplies -> Signal BUY généré")
        
        return {
            'signal': 'BUY',
            'strength': round(strength, 4),
            'reason': f'Prix ({current_price}) en dessous du seuil bas ({threshold_low})',
            'quantity': qty_to_buy,
            'order_cost': order_cost,
            'space_to_max': space_to_max
        }
    
    def _evaluate_sell_signal(self, current_price: float, threshold_high: float,
                             quantity_total: float, min_qty: float,
                             trade_size: float, available_qty: float, debug_info: Dict) -> Dict:
        """
        Évalue si un signal de vente peut être généré.
        """
        debug_info['logic'].append(f"Vérification plancher: {min_qty} (Actuel {quantity_total})")
        
        # CONDITION D'ARRÊT 1 : Plancher atteint
        if quantity_total <= min_qty:
            debug_info['logic'].append("❌ Plancher atteint")
            return {
                'signal': 'SKIP',
                'strength': 0.0,
                'reason': f'Min Floor atteint : quantité actuelle ({quantity_total}) <= min requis ({min_qty})',
                'quantity': 0
            }
        
        # CONDITION D'ARRÊT 2 : Quantité disponible insuffisante pour le trade_size
        if available_qty < trade_size:
            debug_info['logic'].append(f"❌ Quantité disponible insuffisante ({available_qty} < {trade_size})")
            return {
                'signal': 'SKIP',
                'strength': 0.0,
                'reason': f'Quantité disponible insuffisante : {available_qty} < trade_size ({trade_size})',
                'quantity': 0
            }
        
        # Calcul du stock vendable au-dessus du plancher
        sellable_cap = round(quantity_total - min_qty, 8)
        debug_info['logic'].append(f"Stock vendable: {sellable_cap} (Actuel {quantity_total} - Min {min_qty})")
        
        # CONDITION D'ARRÊT 3 : Espace vendable insuffisant
        if sellable_cap < trade_size:
            debug_info['logic'].append(f"❌ Stock vendable insuffisant ({sellable_cap} < {trade_size})")
            return {
                'signal': 'SKIP',
                'strength': 0.0,
                'reason': f'Espace vendable insuffisant : {sellable_cap} (après min_qty) < trade_size ({trade_size})',
                'quantity': 0
            }
        
        # Quantité à vendre (trade_size, car toutes les conditions sont remplies)
        qty_to_sell = trade_size
        debug_info['logic'].append(f"Quantité validée: {qty_to_sell}")
        
        # SIGNAL VALIDE : Générer l'ordre de vente
        strength = min(1.0, (current_price - threshold_high) / threshold_high * 2) if threshold_high > 0 else 0.5
        debug_info['logic'].append("✅ Conditions remplies -> Signal SELL généré")
        
        return {
            'signal': 'SELL',
            'strength': round(strength, 4),
            'reason': f'Prix ({current_price}) au-dessus du seuil haut ({threshold_high})',
            'quantity': qty_to_sell,
            'order_value': round(qty_to_sell * current_price, 8),
            'sellable_cap': sellable_cap
        }
    
    def _simple_signal_logic(self, current_price: float, threshold_low: float, threshold_high: float) -> Dict:
        """
        Logique simple sans gestion de portfolio (rétrocompatibilité).
        
        Utilisée quand aucun portfolio n'est fourni.
        """
        if current_price <= threshold_low:
            strength = min(1.0, (threshold_low - current_price) / threshold_low * 2) if threshold_low > 0 else 0.5
            return {
                'signal': 'BUY',
                'strength': strength,
                'reason': f'Prix ({current_price}) en dessous du seuil bas ({threshold_low})',
                'quantity': 0  # Quantité non définie en mode simple
            }
        elif current_price >= threshold_high:
            strength = min(1.0, (current_price - threshold_high) / threshold_high * 2) if threshold_high > 0 else 0.5
            return {
                'signal': 'SELL',
                'strength': strength,
                'reason': f'Prix ({current_price}) au-dessus du seuil haut ({threshold_high})',
                'quantity': 0
            }
        else:
            return {
                'signal': 'HOLD',
                'strength': 0.0,
                'reason': f'Prix ({current_price}) dans la zone neutre',
                'quantity': 0
            }



class MovingAverageCrossoverAlgorithm(TradingAlgorithm):
    """Algorithme de croisement de moyennes mobiles"""
    
    def calculate_signals(self, price_data: List[Dict]) -> Dict:
        if len(price_data) < 50:  # Besoin d'au moins 50 points pour les MA
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données'}
        
        prices = self._get_prices(price_data)
        ma1_period = self.parameters.get('ma1_period', 20)
        ma2_period = self.parameters.get('ma2_period', 50)
        
        if len(prices) < max(ma1_period, ma2_period):
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données pour les MA'}
        
        # Calculer les moyennes mobiles
        ma1 = np.mean(prices[-ma1_period:])
        ma2 = np.mean(prices[-ma2_period:])
        
        # Calculer les MA précédentes pour détecter le croisement
        if len(prices) >= max(ma1_period, ma2_period) + 1:
            ma1_prev = np.mean(prices[-ma1_period-1:-1])
            ma2_prev = np.mean(prices[-ma2_period-1:-1])
            
            # Détecter le croisement
            if ma1 > ma2 and ma1_prev <= ma2_prev:
                return {
                    'signal': 'BUY',
                    'strength': min(1.0, abs(ma1 - ma2) / ma2) if ma2 > 0 else 0.5,
                    'reason': f'Croisement haussier: MA{ma1_period} ({ma1:.2f}) > MA{ma2_period} ({ma2:.2f})'
                }
            elif ma1 < ma2 and ma1_prev >= ma2_prev:
                return {
                    'signal': 'SELL',
                    'strength': min(1.0, abs(ma2 - ma1) / ma2) if ma2 > 0 else 0.5,
                    'reason': f'Croisement baissier: MA{ma1_period} ({ma1:.2f}) < MA{ma2_period} ({ma2:.2f})'
                }
        
        # Pas de croisement, signal basé sur la position relative
        if ma1 > ma2:
            strength = min(1.0, abs(ma1 - ma2) / ma2) if ma2 > 0 else 0.5
            return {
                'signal': 'HOLD',
                'strength': strength * 0.5,
                'reason': f'MA{ma1_period} ({ma1:.2f}) > MA{ma2_period} ({ma2:.2f}) - tendance haussière'
            }
        else:
            strength = min(1.0, abs(ma2 - ma1) / ma2) if ma2 > 0 else 0.5
            return {
                'signal': 'HOLD',
                'strength': strength * 0.5,
                'reason': f'MA{ma1_period} ({ma1:.2f}) < MA{ma2_period} ({ma2:.2f}) - tendance baissière'
            }


class RSIAlgorithm(TradingAlgorithm):
    """Algorithme RSI (Relative Strength Index)"""
    
    def calculate_signals(self, price_data: List[Dict]) -> Dict:
        if len(price_data) < 30:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données'}
        
        prices = self._get_prices(price_data)
        rsi_period = self.parameters.get('rsi_period', 14)
        rsi_low = self.parameters.get('rsi_low', 30)
        rsi_high = self.parameters.get('rsi_high', 70)
        
        if len(prices) < rsi_period + 1:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données pour RSI'}
        
        # Calculer le RSI
        rsi = self._calculate_rsi(prices, rsi_period)
        
        if rsi <= rsi_low:
            strength = min(1.0, (rsi_low - rsi) / rsi_low) if rsi_low > 0 else 0.5
            return {
                'signal': 'BUY',
                'strength': strength,
                'reason': f'RSI ({rsi:.2f}) en survente (seuil: {rsi_low})'
            }
        elif rsi >= rsi_high:
            strength = min(1.0, (rsi - rsi_high) / (100 - rsi_high)) if rsi_high < 100 else 0.5
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
    
    def _calculate_rsi(self, prices: np.ndarray, period: int) -> float:
        """Calcule le RSI"""
        if len(prices) < period + 1:
            return 50.0
        
        # Calculer les variations
        deltas = np.diff(prices)
        
        # Séparer les gains et pertes
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Moyennes mobiles des gains et pertes
        avg_gains = np.mean(gains[-period:])
        avg_losses = np.mean(losses[-period:])
        
        if avg_losses == 0:
            return 100.0
        
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi


class BollingerBandsAlgorithm(TradingAlgorithm):
    """Algorithme des bandes de Bollinger"""
    
    def calculate_signals(self, price_data: List[Dict]) -> Dict:
        if len(price_data) < 20:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données'}
        
        prices = self._get_prices(price_data)
        bb_period = self.parameters.get('bb_period', 20)
        bb_std = self.parameters.get('bb_std', 2.0)
        
        if len(prices) < bb_period:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données pour Bollinger'}
        
        # Calculer les bandes de Bollinger
        sma = np.mean(prices[-bb_period:])
        std = np.std(prices[-bb_period:])
        
        upper_band = sma + (bb_std * std)
        lower_band = sma - (bb_std * std)
        
        current_price = prices[-1]
        
        # Calculer la position relative dans les bandes
        band_width = upper_band - lower_band
        if band_width == 0:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Bandes de Bollinger trop étroites'}
        
        position = (current_price - lower_band) / band_width
        
        if current_price <= lower_band:
            strength = min(1.0, (lower_band - current_price) / lower_band) if lower_band > 0 else 0.5
            return {
                'signal': 'BUY',
                'strength': strength,
                'reason': f'Prix ({current_price:.2f}) touche la bande basse ({lower_band:.2f})'
            }
        elif current_price >= upper_band:
            strength = min(1.0, (current_price - upper_band) / upper_band) if upper_band > 0 else 0.5
            return {
                'signal': 'SELL',
                'strength': strength,
                'reason': f'Prix ({current_price:.2f}) touche la bande haute ({upper_band:.2f})'
            }
        else:
            # Signal basé sur la position dans les bandes
            if position < 0.2:  # Proche de la bande basse
                return {
                    'signal': 'HOLD',
                    'strength': 0.3,
                    'reason': f'Prix ({current_price:.2f}) proche de la bande basse'
                }
            elif position > 0.8:  # Proche de la bande haute
                return {
                    'signal': 'HOLD',
                    'strength': 0.3,
                    'reason': f'Prix ({current_price:.2f}) proche de la bande haute'
                }
            else:
                return {
                    'signal': 'HOLD',
                    'strength': 0.0,
                    'reason': f'Prix ({current_price:.2f}) dans la zone centrale'
                }


class MACDAlgorithm(TradingAlgorithm):
    """Algorithme MACD (Moving Average Convergence Divergence)"""
    
    def calculate_signals(self, price_data: List[Dict]) -> Dict:
        if len(price_data) < 50:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données'}
        
        prices = self._get_prices(price_data)
        macd_fast = self.parameters.get('macd_fast', 12)
        macd_slow = self.parameters.get('macd_slow', 26)
        macd_signal = self.parameters.get('macd_signal', 9)
        
        if len(prices) < macd_slow + macd_signal:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données pour MACD'}
        
        # Calculer MACD
        ema_fast = self._calculate_ema(prices, macd_fast)
        ema_slow = self._calculate_ema(prices, macd_slow)
        macd_line = ema_fast - ema_slow
        
        # Calculer la ligne de signal (EMA du MACD)
        macd_values = []
        for i in range(macd_slow, len(prices)):
            ema_fast_i = self._calculate_ema(prices[:i+1], macd_fast)
            ema_slow_i = self._calculate_ema(prices[:i+1], macd_slow)
            macd_values.append(ema_fast_i - ema_slow_i)
        
        if len(macd_values) < macd_signal:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données pour signal MACD'}
        
        signal_line = self._calculate_ema(np.array(macd_values), macd_signal)
        histogram = macd_line - signal_line
        
        # Détecter les croisements
        if len(macd_values) >= 2:
            prev_macd = macd_values[-2]
            prev_signal = self._calculate_ema(np.array(macd_values[:-1]), macd_signal)
            
            if macd_line > signal_line and prev_macd <= prev_signal:
                strength = min(1.0, abs(macd_line - signal_line) / abs(signal_line)) if signal_line != 0 else 0.5
                return {
                    'signal': 'BUY',
                    'strength': strength,
                    'reason': f'MACD ({macd_line:.4f}) croise au-dessus du signal ({signal_line:.4f})'
                }
            elif macd_line < signal_line and prev_macd >= prev_signal:
                strength = min(1.0, abs(signal_line - macd_line) / abs(signal_line)) if signal_line != 0 else 0.5
                return {
                    'signal': 'SELL',
                    'strength': strength,
                    'reason': f'MACD ({macd_line:.4f}) croise en-dessous du signal ({signal_line:.4f})'
                }
        
        # Signal basé sur la position relative
        if macd_line > signal_line:
            strength = min(1.0, abs(macd_line - signal_line) / abs(signal_line)) if signal_line != 0 else 0.5
            return {
                'signal': 'HOLD',
                'strength': strength * 0.5,
                'reason': f'MACD ({macd_line:.4f}) > Signal ({signal_line:.4f}) - tendance haussière'
            }
        else:
            strength = min(1.0, abs(signal_line - macd_line) / abs(signal_line)) if signal_line != 0 else 0.5
            return {
                'signal': 'HOLD',
                'strength': strength * 0.5,
                'reason': f'MACD ({macd_line:.4f}) < Signal ({signal_line:.4f}) - tendance baissière'
            }
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calcule l'EMA (Exponential Moving Average)"""
        if len(prices) < period:
            return float(np.mean(prices))
        
        alpha = 2 / (period + 1)
        ema = float(prices[0])
        
        for price in prices[1:]:
            ema = alpha * float(price) + (1 - alpha) * ema
        
        return ema


class GridTradingAlgorithm(TradingAlgorithm):
    """Algorithme de Grid Trading"""
    
    def calculate_signals(self, price_data: List[Dict]) -> Dict:
        if len(price_data) < 1:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données'}
        
        current_price = float(price_data[-1]['close'])
        grid_min = self.parameters.get('grid_min', 0)
        grid_max = self.parameters.get('grid_max', float('inf'))
        grid_levels = self.parameters.get('grid_levels', 10)
        
        if grid_max <= grid_min or grid_max == float('inf'):
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Paramètres de grille invalides'}
        
        # Calculer les niveaux de la grille
        grid_step = (grid_max - grid_min) / grid_levels
        grid_levels_list = [grid_min + i * grid_step for i in range(grid_levels + 1)]
        
        # Trouver le niveau le plus proche
        closest_level = min(grid_levels_list, key=lambda x: abs(x - current_price))
        
        # Déterminer le signal basé sur la position par rapport au niveau
        if current_price <= closest_level + grid_step * 0.1:  # Proche du niveau inférieur
            strength = min(1.0, abs(closest_level - current_price) / grid_step) if grid_step > 0 else 0.5
            return {
                'signal': 'BUY',
                'strength': strength,
                'reason': f'Prix ({current_price:.2f}) proche du niveau d\'achat ({closest_level:.2f})'
            }
        elif current_price >= closest_level - grid_step * 0.1:  # Proche du niveau supérieur
            strength = min(1.0, abs(current_price - closest_level) / grid_step) if grid_step > 0 else 0.5
            return {
                'signal': 'SELL',
                'strength': strength,
                'reason': f'Prix ({current_price:.2f}) proche du niveau de vente ({closest_level:.2f})'
            }
        else:
            return {
                'signal': 'HOLD',
                'strength': 0.0,
                'reason': f'Prix ({current_price:.2f}) entre les niveaux de la grille'
            }


class AlgorithmFactory:
    """Factory pour créer les instances d'algorithmes"""
    
    _algorithms = {
        'threshold': ThresholdAlgorithm,
        'ma_crossover': MovingAverageCrossoverAlgorithm,
        'rsi': RSIAlgorithm,
        'bollinger': BollingerBandsAlgorithm,
        'macd': MACDAlgorithm,
        'grid': GridTradingAlgorithm,
    }
    
    @classmethod
    def create_algorithm(cls, algorithm_type: str, parameters: Dict, strategy=None) -> TradingAlgorithm:
        """Crée une instance de l'algorithme spécifié"""
        if algorithm_type not in cls._algorithms:
            raise ValueError(f'Algorithme non supporté: {algorithm_type}')
        
        algorithm_class = cls._algorithms[algorithm_type]
        return algorithm_class(parameters, strategy)
    
    @classmethod
    def get_supported_algorithms(cls):
        """Retourne la liste des algorithmes supportés"""
        return list(cls._algorithms.keys())



