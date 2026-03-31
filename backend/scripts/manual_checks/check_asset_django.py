import os
import django
import sys

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)
os.chdir(_BACKEND_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config_django.settings.development")

try:
    django.setup()
    from apps.trading.models import AllAssets
    
    # Check for asset 101173
    try:
        asset = AllAssets.objects.get(pk=101173)
        print(f"Asset FOUND: {asset.symbol} (ID: {asset.id})")
        print(f"Platform: {asset.platform}")
        print(f"Has price history: {asset.has_price_history}")
        
        # Check price history count
        history = asset.get_price_history_dates()
        print(f"Price history dates count: {len(history)}")
        if len(history) > 0:
            print(f"Latest date: {history[0]}")
            
    except AllAssets.DoesNotExist:
        print("Asset 101173 NOT FOUND in database")

except Exception as e:
    print(f"Error during setup or query: {e}")
