"""
Script pour tester les URLs générées par DRF
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config_django.settings.development')
django.setup()

from django.urls import reverse
from rest_framework.routers import DefaultRouter
from apps.trading.api import views

# Créer un router pour voir les URLs générées
router = DefaultRouter()
router.register(r'all-assets', views.AllAssetsViewSet, basename='all-asset')

print("\n" + "="*70)
print("URLs générées par DRF pour AllAssetsViewSet:")
print("="*70 + "\n")

for url_pattern in router.urls:
    print(f"{url_pattern.pattern}")
    if hasattr(url_pattern, 'name'):
        print(f"  Name: {url_pattern.name}")
    if hasattr(url_pattern, 'callback'):
        print(f"  Callback: {url_pattern.callback}")
    print()

# Tester l'URL reverse
try:
    url = reverse('all-asset-prices', kwargs={'pk': 101173})
    print(f"\n✅ Reverse URL pour all-asset-prices (pk=101173): {url}")
except Exception as e:
    print(f"\n❌ Erreur lors du reverse URL: {e}")
    print("\nTentative avec basename...")
    try:
        url = reverse('all-asset-detail', kwargs={'pk': 101173})
        print(f"✅ Reverse URL pour all-asset-detail (pk=101173): {url}")
    except Exception as e2:
        print(f"❌ Erreur: {e2}")

print("\n" + "="*70)
print("Test de l'URL complète:")
print("="*70)
print("URL attendue: /api/all-assets/101173/prices/")
print("Vérifiez que cette URL est bien dans la liste ci-dessus\n")



