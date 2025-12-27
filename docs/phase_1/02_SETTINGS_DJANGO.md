# ⚙️ Configuration Django (Settings)

## Architecture modulaire

Les settings sont divisés en 3 fichiers :

```
config_django/settings/
├── __init__.py       # Charge le bon settings
├── base.py           # Configuration commune
├── development.py    # Dev (DEBUG=True)
└── production.py     # Prod (sécurisé)
```

## `__init__.py`

```python
import os
from decouple import config

# Charge le settings selon DJANGO_SETTINGS_MODULE
# Par défaut : development
env = config('DJANGO_ENV', default='development')

if env == 'production':
    from .production import *
else:
    from .development import *
```

## `base.py` - Configuration commune

### INSTALLED_APPS

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'drf_spectacular',
    'corsheaders',
    
    # Apps métier
    'apps.trading',
    'apps.macro_economics',
    'apps.ai_assistant',
]
```

### Database (Supabase PostgreSQL)

```python
USE_SUPABASE = config('USE_SUPABASE', default=True, cast=bool)

if USE_SUPABASE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='postgres'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='db.xxx.supabase.co'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
```

### REST Framework

```python
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
```

### JWT Configuration

```python
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

### CORS

```python
CORS_ALLOW_HEADERS = [
    'accept', 'authorization', 'content-type',
    'x-csrftoken', 'x-requested-with',
]

CORS_ALLOW_METHODS = [
    'DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT',
]

CORS_ALLOW_CREDENTIALS = True
CORS_PREFLIGHT_MAX_AGE = 86400
```

## `development.py` - Développement

```python
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# CORS permissif en dev
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
]

# Email dans la console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

## `production.py` - Production

```python
from .base import *
import os

DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Sécurité renforcée
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000

# CORS restrictif
CORS_ALLOWED_ORIGINS = [
    origin for origin in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
    if origin
]
```

## Fichier `.env`

```env
SECRET_KEY=your-secret-key-change-in-production
DEBUG=True
USE_SUPABASE=true
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=db.xxx.supabase.co
DB_PORT=5432
```

## Variables d'environnement requises

| Variable | Description | Défaut |
|----------|-------------|--------|
| `SECRET_KEY` | Clé secrète Django | requis en prod |
| `DEBUG` | Mode debug | `True` |
| `USE_SUPABASE` | Utiliser PostgreSQL | `True` |
| `DB_NAME` | Nom de la base | `postgres` |
| `DB_USER` | Utilisateur DB | `postgres` |
| `DB_PASSWORD` | Mot de passe DB | requis |
| `DB_HOST` | Host PostgreSQL | requis |
| `DB_PORT` | Port PostgreSQL | `5432` |

