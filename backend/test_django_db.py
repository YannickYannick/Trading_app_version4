import os
import django
from django.conf import settings

# Configurer l'environnement Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config_django.settings.production_test")
django.setup()

print("Django Configured!")
print(f"DB HOST: {settings.DATABASES['default']['HOST']}")
print(f"DB NAME: {settings.DATABASES['default']['NAME']}")

# Test connection
from django.db import connections
from django.db.utils import OperationalError
db_conn = connections['default']
try:
    c = db_conn.cursor()
    print("Cursor obtained!")
except OperationalError as e:
    print(f"OperationalError: {e}")
except Exception as e:
    print(f"Error: {e}")
