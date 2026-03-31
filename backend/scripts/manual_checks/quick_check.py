import os
import sys
import django

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)
os.chdir(_BACKEND_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config_django.settings.development')
django.setup()

from apps.trading.models import Strategy
strategy = Strategy.objects.first()
print(f"Stratégie: {strategy.name}")
print(f"is_automated: {strategy.is_automated}")
print(f"is_active: {strategy.is_active}")
