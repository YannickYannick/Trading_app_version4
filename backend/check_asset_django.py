
import os
import django
import sys

# Add project root to path
sys.path.append(os.getcwd())

# Use the correct settings module as seen in manage.py
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
