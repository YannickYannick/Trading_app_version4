import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config_django.settings.development')
django.setup()

from apps.trading.models import Strategy
strategy = Strategy.objects.first()
print(f"Stratégie: {strategy.name}")
print(f"is_automated: {strategy.is_automated}")
print(f"is_active: {strategy.is_active}")
