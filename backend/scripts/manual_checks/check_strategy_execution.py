"""
Script pour vérifier l'état de l'exécution automatique des stratégies.
"""
import os
import sys
import django

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)
os.chdir(_BACKEND_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config_django.settings.development')
django.setup()

from apps.trading.models import Strategy, Order, Trade, Position, StrategyExecution
from django.contrib.auth import get_user_model

User = get_user_model()

# Récupérer l'utilisateur (adapter selon votre cas)
user = User.objects.first()
if not user:
    print("❌ Aucun utilisateur trouvé")
    exit()

print(f"👤 Utilisateur: {user.username}\n")

# Vérifier les stratégies
strategies = Strategy.objects.filter(user=user)
print(f"📊 Stratégies trouvées: {strategies.count()}\n")

for strategy in strategies:
    print(f"{'='*60}")
    print(f"📈 Stratégie: {strategy.name}")
    print(f"   Asset: {strategy.all_asset}")
    print(f"   Active: {'✅' if strategy.is_active else '❌'}")
    print(f"   Automated: {'✅' if strategy.is_automated else '❌ NON AUTOMATISÉE'}")
    print(f"   Budget: {strategy.budget}€")
    if strategy.broker_account:
        print(f"   Broker: {strategy.broker_account.broker.name}")
        print(f"   Balance: {strategy.broker_account.balance}€")
    
    # Dernières exécutions
    executions = StrategyExecution.objects.filter(strategy=strategy).order_by('-started_at')[:3]
    print(f"\n   📝 Dernières exécutions ({executions.count()}):")
    for exe in executions:
        print(f"      - {exe.started_at.strftime('%H:%M:%S')} | {exe.signal} | Status: {exe.status}")
    
    # Ordres créés
    orders = Order.objects.filter(strategy=strategy).order_by('-created_at')[:5]
    print(f"\n   📦 Ordres créés ({orders.count()}):")
    for order in orders:
        print(f"      - {order.created_at.strftime('%H:%M:%S')} | {order.side} | {order.quantity} @ {order.price}€ | {order.status}")
    
    # Positions
    positions = Position.objects.filter(strategy=strategy, is_open=True)
    print(f"\n   💼 Positions ouvertes ({positions.count()}):")
    for pos in positions:
        print(f"      - {pos.quantity} @ {pos.entry_price}€ | P&L: {pos.unrealized_pnl}€")
    
    print()

print(f"{'='*60}")
print("\n✅ Vérification terminée")
