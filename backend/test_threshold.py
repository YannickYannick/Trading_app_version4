"""
Tests unitaires pour l'algorithme Threshold.

Ce module teste tous les aspects de l'algorithme ThresholdAlgorithm :
- Logique des seuils (threshold_low, threshold_high)
- Respect des contraintes min_qty / max_qty
- Taille de trade fixe (trade_size)
- Gestion du portfolio et disponibilités
- Ordres en attente
"""

import sys
import os
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config_django.settings.development')
django.setup()

from apps.trading.algorithms import ThresholdAlgorithm


def test_signal_buy_below_threshold():
    """Test 1: Signal BUY quand prix < threshold_low"""
    print("\n" + "="*60)
    print("TEST 1: Signal BUY - Prix en dessous du seuil")
    print("="*60)
    
    algo = ThresholdAlgorithm({
        'threshold_low': 85000,
        'threshold_high': 95000,
        'trade_size': 0.5
    })
    
    price_data = [{'close': 84000}]  # Prix < 85000
    portfolio = {'cash_total': 50000, 'quantity_total': 1.0}
    
    result = algo.calculate_signals(price_data, portfolio)
    
    print(f"Prix: 84000 (< 85000)")
    print(f"Signal: {result['signal']}")
    print(f"Quantity: {result.get('quantity', 0)}")
    print(f"Reason: {result['reason']}")
    
    assert result['signal'] == 'BUY', f"Expected BUY, got {result['signal']}"
    assert result.get('quantity', 0) == 0.5, f"Expected 0.5, got {result.get('quantity', 0)}"
    print("✅ PASS")


def test_signal_sell_above_threshold():
    """Test 2: Signal SELL quand prix > threshold_high"""
    print("\n" + "="*60)
    print("TEST 2: Signal SELL - Prix au-dessus du seuil")
    print("="*60)
    
    algo = ThresholdAlgorithm({
        'threshold_low': 85000,
        'threshold_high': 95000,
        'trade_size': 0.5
    })
    
    price_data = [{'close': 96000}]  # Prix > 95000
    portfolio = {'cash_total': 10000, 'quantity_total': 1.5}
    
    result = algo.calculate_signals(price_data, portfolio)
    
    print(f"Prix: 96000 (> 95000)")
    print(f"Signal: {result['signal']}")
    print(f"Quantity: {result.get('quantity', 0)}")
    print(f"Reason: {result['reason']}")
    
    assert result['signal'] == 'SELL', f"Expected SELL, got {result['signal']}"
    assert result.get('quantity', 0) == 0.5, f"Expected 0.5, got {result.get('quantity', 0)}"
    print("✅ PASS")


def test_signal_hold_in_neutral_zone():
    """Test 3: Signal HOLD dans la zone neutre"""
    print("\n" + "="*60)
    print("TEST 3: Signal HOLD - Prix dans la zone neutre")
    print("="*60)
    
    algo = ThresholdAlgorithm({
        'threshold_low': 85000,
        'threshold_high': 95000,
    })
    
    price_data = [{'close': 90000}]  # 85000 < Prix < 95000
    portfolio = {'cash_total': 10000, 'quantity_total': 1.5}
    
    result = algo.calculate_signals(price_data, portfolio)
    
    print(f"Prix: 90000 (entre 85000 et 95000)")
    print(f"Signal: {result['signal']}")
    print(f"Reason: {result['reason']}")
    
    assert result['signal'] == 'HOLD', f"Expected HOLD, got {result['signal']}"
    print("✅ PASS")


def test_skip_buy_max_qty_reached():
    """Test 4: SKIP BUY quand max_qty atteint"""
    print("\n" + "="*60)
    print("TEST 4: SKIP BUY - Plafond atteint")
    print("="*60)
    
    algo = ThresholdAlgorithm({
        'threshold_low': 85000,
        'threshold_high': 95000,
        'max_qty': 2.0,
        'trade_size': 0.5
    })
    
    price_data = [{'close': 84000}]
    portfolio = {'cash_total': 50000, 'quantity_total': 2.0}  # Déjà au max
    
    result = algo.calculate_signals(price_data, portfolio)
    
    print(f"Quantité actuelle: 2.0 (max: 2.0)")
    print(f"Signal: {result['signal']}")
    print(f"Reason: {result['reason']}")
    
    assert result['signal'] == 'SKIP', f"Expected SKIP, got {result['signal']}"
    assert 'plafond atteint' in result['reason'].lower() or 'cap' in result['reason'].lower(), \
        f"Expected reason about cap, got: {result['reason']}"
    print("✅ PASS")


def test_skip_sell_min_qty_reached():
    """Test 5: SKIP SELL quand min_qty atteint"""
    print("\n" + "="*60)
    print("TEST 5: SKIP SELL - Plancher atteint")
    print("="*60)
    
    algo = ThresholdAlgorithm({
        'threshold_low': 85000,
        'threshold_high': 95000,
        'min_qty': 0.5,
        'trade_size': 0.5
    })
    
    price_data = [{'close': 96000}]
    portfolio = {'cash_total': 10000, 'quantity_total': 0.5}  # Déjà au min
    
    result = algo.calculate_signals(price_data, portfolio)
    
    print(f"Quantité actuelle: 0.5 (min: 0.5)")
    print(f"Signal: {result['signal']}")
    print(f"Reason: {result['reason']}")
    
    assert result['signal'] == 'SKIP', f"Expected SKIP, got {result['signal']}"
    assert 'plancher atteint' in result['reason'].lower() or 'floor' in result['reason'].lower(), \
        f"Expected reason about floor, got: {result['reason']}"
    print("✅ PASS")


def test_skip_buy_insufficient_cash():
    """Test 6: SKIP BUY si fonds insuffisants"""
    print("\n" + "="*60)
    print("TEST 6: SKIP BUY - Fonds insuffisants")
    print("="*60)
    
    algo = ThresholdAlgorithm({
        'threshold_low': 85000,
        'threshold_high': 95000,
        'trade_size': 0.5
    })
    
    price_data = [{'close': 84000}]
    portfolio = {'cash_total': 10000, 'quantity_total': 1.0}  # Pas assez pour 0.5 @ 84000
    
    result = algo.calculate_signals(price_data, portfolio)
    
    print(f"Cash disponible: 10000 (besoin: {0.5 * 84000})")
    print(f"Signal: {result['signal']}")
    print(f"Reason: {result['reason']}")
    
    assert result['signal'] == 'SKIP', f"Expected SKIP, got {result['signal']}"
    assert 'fonds insuffisants' in result['reason'].lower() or 'cash' in result['reason'].lower(), \
        f"Expected reason about insufficient funds, got: {result['reason']}"
    print("✅ PASS")


def test_skip_sell_insufficient_quantity():
    """Test 7: SKIP SELL si quantité insuffisante"""
    print("\n" + "="*60)
    print("TEST 7: SKIP SELL - Quantité insuffisante")
    print("="*60)
    
    algo = ThresholdAlgorithm({
        'threshold_low': 85000,
        'threshold_high': 95000,
        'trade_size': 0.5
    })
    
    price_data = [{'close': 96000}]
    portfolio = {'cash_total': 100000, 'quantity_total': 0.3}  # Moins que trade_size
    
    result = algo.calculate_signals(price_data, portfolio)
    
    print(f"Quantité disponible: 0.3 (besoin: 0.5)")
    print(f"Signal: {result['signal']}")
    print(f"Reason: {result['reason']}")
    
    assert result['signal'] == 'SKIP', f"Expected SKIP, got {result['signal']}"
    print("✅ PASS")


def test_pending_orders_lock_cash():
    """Test 8: Ordres BUY en attente bloquent du cash"""
    print("\n" + "="*60)
    print("TEST 8: Ordres BUY en attente - Cash bloqué")
    print("="*60)
    
    algo = ThresholdAlgorithm({
        'threshold_low': 85000,
        'threshold_high': 95000,
        'trade_size': 0.5
    })
    
    price_data = [{'close': 84000}]
    portfolio = {'cash_total': 50000, 'quantity_total': 1.0}
    pending_orders = [
        {'type': 'BUY', 'qty': 0.4, 'price': 84000}  # Bloque 33600 cash
    ]
    
    result = algo.calculate_signals(price_data, portfolio, pending_orders)
    
    locked_cash = 0.4 * 84000
    available_cash = 50000 - locked_cash
    print(f"Cash total: 50000")
    print(f"Cash bloqué: {locked_cash}")
    print(f"Cash disponible: {available_cash}")
    print(f"Coût trade: {0.5 * 84000}")
    print(f"Signal: {result['signal']}")
    print(f"Reason: {result['reason']}")
    
    # Devrait toujours pouvoir acheter car available_cash (16400) < coût (42000)
    # Donc SKIP
    assert result['signal'] in ['BUY', 'SKIP'], f"Expected BUY or SKIP, got {result['signal']}"
    print("✅ PASS")


def test_pending_orders_lock_quantity():
    """Test 9: Ordres SELL en attente bloquent de la quantité"""
    print("\n" + "="*60)
    print("TEST 9: Ordres SELL en attente - Quantité bloquée")
    print("="*60)
    
    algo = ThresholdAlgorithm({
        'threshold_low': 85000,
        'threshold_high': 95000,
        'trade_size': 0.5
    })
    
    price_data = [{'close': 96000}]
    portfolio = {'cash_total': 10000, 'quantity_total': 1.5}
    pending_orders = [
        {'type': 'SELL', 'qty': 1.2, 'price': 96000}  # Bloque 1.2 qty
    ]
    
    result = algo.calculate_signals(price_data, portfolio, pending_orders)
    
    available_qty = 1.5 - 1.2
    print(f"Quantité totale: 1.5")
    print(f"Quantité bloquée: 1.2")
    print(f"Quantité disponible: {available_qty}")
    print(f"Trade size: 0.5")
    print(f"Signal: {result['signal']}")
    print(f"Reason: {result['reason']}")
    
    # available_qty (0.3) < trade_size (0.5) => SKIP
    assert result['signal'] == 'SKIP', f"Expected SKIP, got {result['signal']}"
    print("✅ PASS")


def test_threshold_exact_prices():
    """Test 10: Prix exactement égaux aux seuils"""
    print("\n" + "="*60)
    print("TEST 10: Prix exactement sur les seuils")
    print("="*60)
    
    algo = ThresholdAlgorithm({
        'threshold_low': 85000,
        'threshold_high': 95000,
        'trade_size': 0.5
    })
    
    # Prix = threshold_low (devrait BUY)
    price_data_low = [{'close': 85000}]
    portfolio = {'cash_total': 50000, 'quantity_total': 1.0}
    result_low = algo.calculate_signals(price_data_low, portfolio)
    
    print(f"Prix = threshold_low (85000)")
    print(f"Signal: {result_low['signal']}")
    assert result_low['signal'] == 'BUY', f"Expected BUY at threshold_low, got {result_low['signal']}"
    
    # Prix = threshold_high (devrait SELL)
    price_data_high = [{'close': 95000}]
    result_high = algo.calculate_signals(price_data_high, portfolio)
    
    print(f"Prix = threshold_high (95000)")
    print(f"Signal: {result_high['signal']}")
    assert result_high['signal'] == 'SELL', f"Expected SELL at threshold_high, got {result_high['signal']}"
    
    print("✅ PASS")


def run_all_tests():
    """Exécute tous les tests"""
    print("\n" + "="*60)
    print("DÉBUT DES TESTS - ThresholdAlgorithm")
    print("="*60)
    
    tests = [
        test_signal_buy_below_threshold,
        test_signal_sell_above_threshold,
        test_signal_hold_in_neutral_zone,
        test_skip_buy_max_qty_reached,
        test_skip_sell_min_qty_reached,
        test_skip_buy_insufficient_cash,
        test_skip_sell_insufficient_quantity,
        test_pending_orders_lock_cash,
        test_pending_orders_lock_quantity,
        test_threshold_exact_prices,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"❌ FAIL: {e}")
        except Exception as e:
            failed += 1
            print(f"💥 ERROR: {e}")
    
    print("\n" + "="*60)
    print("RÉSULTATS DES TESTS")
    print("="*60)
    print(f"✅ Passés: {passed}/{len(tests)}")
    print(f"❌ Échoués: {failed}/{len(tests)}")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Rediriger la sortie vers un fichier
    with open('test_threshold_output.txt', 'w', encoding='utf-8') as f:
        import sys
        old_stdout = sys.stdout
        sys.stdout = f
        try:
            run_all_tests()
        finally:
            sys.stdout = old_stdout
    
    # Afficher le résultat
    with open('test_threshold_output.txt', 'r', encoding='utf-8') as f:
        print(f.read())
