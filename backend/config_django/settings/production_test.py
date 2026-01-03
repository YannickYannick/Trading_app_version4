"""
Configuration Production Test.
Similaire à la production (PostgreSQL) mais avec DEBUG=True.
"""
from .production import *

# Surcharger pour le mode test
DEBUG = True

# En test, on veut voir les erreurs détaillées
LOGGING['handlers']['console']['level'] = 'DEBUG'

# Hôtes autorisés spécifiques au test
ALLOWED_HOSTS = [
    'le-baff.com',
    'www.le-baff.com',
    'localhost',
    '127.0.0.1',
    '192.168.1.143',  # IP locale souvent utilisée
]

# CORS pour le développement/test
CORS_ALLOW_ALL_ORIGINS = True  # Plus permissif pour les tests

# Options supplémentaires pour Supabase (SSL requis)
if 'default' in DATABASES:
    DATABASES['default']['OPTIONS'] = {'sslmode': 'require', 'connect_timeout': 10}

# Surcharger pour le mode test
DEBUG = True
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
