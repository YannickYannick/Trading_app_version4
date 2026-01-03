
import os
import django
import sys

sys.path.append(os.getcwd())
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
