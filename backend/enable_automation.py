"""
Script pour activer l'exécution automatique sur toutes les stratégies.
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config_django.settings.development')
django.setup()

from apps.trading.models import Strategy

strategies = Strategy.objects.all()
print(f"📊 {strategies.count()} stratégies trouvées\n")

for strategy in strategies:
    print(f"{'='*60}")
    print(f"📈 Stratégie: {strategy.name}")
    print(f"   Avant: is_automated = {strategy.is_automated}, is_active = {strategy.is_active}")
    
    # Activer l'automatisation ET l'activation
    strategy.is_automated = True
    strategy.is_active = True
    strategy.save()
    
    print(f"   Après: is_automated = {strategy.is_automated}, is_active = {strategy.is_active}")
    print(f"   ✅ Stratégie activée et automatisée\n")

print(f"{'='*60}")
print("✅ Toutes les stratégies sont maintenant automatisées et actives")
print("\n💡 Relancez l'exécution pour voir les ordres se créer automatiquement !")
