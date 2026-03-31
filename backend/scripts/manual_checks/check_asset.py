import os
import django
import sys

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)
os.chdir(_BACKEND_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config_django.settings")
django.setup()

from apps.trading.models import AllAssets

try:
    asset = AllAssets.objects.get(pk=101173)
    print(f"Asset found: {asset.symbol} (ID: {asset.id})")
    print(f"Has price history: {asset.has_price_history}")
    print(f"Price history dates: {len(asset.get_price_history_dates())} dates")
except AllAssets.DoesNotExist:
    print("Asset 101173 NOT FOUND")
except Exception as e:
    print(f"Error: {e}")
