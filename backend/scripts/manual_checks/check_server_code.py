"""
Vérifier que le serveur Django utilise bien le bon code
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

from apps.trading.api.views import AllAssetsViewSet
import inspect

# Vérifier le code source de la méthode prices
method = getattr(AllAssetsViewSet, 'prices', None)
if method:
    source = inspect.getsource(method)
    print("\n" + "="*70)
    print("Code source de la méthode prices:")
    print("="*70)
    print(source[:500])  # Premiers 500 caractères
    
    # Vérifier si le code utilise AllAssets.objects.get
    if 'AllAssets.objects.get' in source:
        print("\n✅ Le code utilise bien AllAssets.objects.get (nouveau code)")
    else:
        print("\n❌ Le code n'utilise pas AllAssets.objects.get (ancien code?)")
        
    # Vérifier si le code gère query_params
    if 'getattr(request, \'query_params\'' in source or 'request.query_params' in source or 'query_params = getattr' in source:
        print("✅ Le code gère bien request.query_params (nouveau code)")
    else:
        print("❌ Le code ne gère pas request.query_params correctement")
else:
    print("❌ Méthode prices non trouvée")



