import sys
import os

# Set the project path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# Manually load .env file because Passenger might not pick it up correctly via decouple
env_path = os.path.join(SCRIPT_DIR, '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            os.environ.setdefault(key, value)

# Set the settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config_django.settings.production")

# Import Django application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
