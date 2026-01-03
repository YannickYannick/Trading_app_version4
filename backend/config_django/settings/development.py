"""
Configuration Django pour le développement.
"""
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]', '*']

# Database - Utilise la config de base.py (PostgreSQL ou SQLite selon USE_SUPABASE)
# Ne pas override ici !

# Debug toolbar (optionnel)
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
# INTERNAL_IPS = ['127.0.0.1']

# Email backend pour le développement (affiche dans la console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ============================================
# CORS pour le développement
# ============================================
# Origines autorisées (frontend React)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",    # Vite dev server (défaut)
    "http://127.0.0.1:5173",    # Vite alternative
    "http://localhost:3000",    # Create React App / Next.js
    "http://127.0.0.1:3000",    # Alternative
    "http://localhost:4200",    # Angular (si besoin)
    "http://localhost:8080",    # Vue.js (si besoin)
]

# Option alternative : autoriser toutes les origines en dev
# ⚠️ Moins sécurisé mais plus simple pour le développement
CORS_ALLOW_ALL_ORIGINS = True

# URLs exposées dans les réponses CORS
CORS_EXPOSE_HEADERS = [
    'Content-Type',
    'X-CSRFToken',
]
