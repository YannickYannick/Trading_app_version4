"""
Configuration Django de base (commune à tous les environnements).
"""
import os
import logging.handlers
from pathlib import Path
from decouple import config


class SafeRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """
    RotatingFileHandler qui ignore les erreurs de permission sur Windows.
    
    Sur Windows, le fichier peut être verrouillé par un autre processus,
    ce qui empêche la rotation. Cette classe ignore silencieusement ces erreurs.
    """
    def doRollover(self):
        """
        Fait la rotation du fichier, en ignorant les PermissionError.
        """
        try:
            super().doRollover()
        except (PermissionError, OSError) as e:
            # Ignorer les erreurs de permission sur Windows
            # Le fichier continuera à être écrit, seule la rotation échoue
            pass

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='dev-secret-key-change-in-production')

def cast_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).lower() in ('true', '1', 'yes', 'on')

DEBUG = config('DEBUG', default=True, cast=cast_bool)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',           # Django REST Framework
    'rest_framework_simplejwt', # JWT Authentication
    'django_filters',           # Filtres avancés pour DRF
    'drf_spectacular',          # Documentation API OpenAPI/Swagger
    'corsheaders',              # Pour CORS avec React
    
    # Apps métier
    'apps.trading.apps.TradingConfig',
    'apps.macro_economics.apps.MacroEconomicsConfig',
    'apps.ai_assistant.apps.AiAssistantConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # CORS en premier
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'apps.trading.middleware.ErrorHandlerMiddleware',  # Gestion d'erreurs unifiée — désactivé avec apps.trading
]

ROOT_URLCONF = 'config_django.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config_django.wsgi.application'

# Database
# Configuration Supabase PostgreSQL / SQLite
# Pour basculer entre SQLite (dev) et Supabase (prod), utilisez USE_SUPABASE=true/false
USE_SUPABASE = config('USE_SUPABASE', default=True, cast=cast_bool)

# #region agent log
try:
    import json as _json
    import time as _time

    _db_user_env = os.environ.get("DB_USER")
    _db_user_cfg = config("DB_USER", default=None)
    _db_host_cfg = config("DB_HOST", default=None)
    _db_port_cfg = config("DB_PORT", default=None)

    print(
        "[debug-e5b425] hypothesisE base_db_env",
        "DATABASE_URL_set=",
        bool(os.environ.get("DATABASE_URL")),
        "USE_SUPABASE=",
        USE_SUPABASE,
        "DB_USER_env=",
        _db_user_env,
        "DB_USER_cfg=",
        _db_user_cfg,
        "DB_HOST_cfg=",
        _db_host_cfg,
        "DB_PORT_cfg=",
        _db_port_cfg,
        flush=True,
    )

    _p = (BASE_DIR.parent / "debug-e5b425.log").resolve()
    with open(_p, "a", encoding="utf-8") as _f:
        _f.write(
            _json.dumps(
                {
                    "sessionId": "e5b425",
                    "location": "base.py:DATABASES",
                    "message": "db env snapshot",
                    "data": {
                        "hypothesisId": "E",
                        "database_url_set": bool(os.environ.get("DATABASE_URL")),
                        "use_supabase": bool(USE_SUPABASE),
                        "db_user_env": _db_user_env,
                        "db_user_cfg": _db_user_cfg,
                        "db_host_cfg": _db_host_cfg,
                        "db_port_cfg": _db_port_cfg,
                    },
                    "timestamp": int(_time.time() * 1000),
                }
            )
            + "\n"
        )
except OSError:
    pass
# #endregion

if USE_SUPABASE:
    # Configuration Supabase PostgreSQL
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='postgres'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='db.lowncckbivxmiakzmsxq.supabase.co'),
            'PORT': config('DB_PORT', default='5432'),
            'OPTIONS': {
                'connect_timeout': 10,
            }
        }
    }

    # #region agent log
    try:
        _db = DATABASES.get("default", {})
        print(
            "[debug-e5b425] hypothesisF base_db_computed",
            "name=",
            _db.get("NAME"),
            "user=",
            _db.get("USER"),
            "host=",
            _db.get("HOST"),
            "port=",
            _db.get("PORT"),
            "pwd_set=",
            bool(_db.get("PASSWORD")),
            flush=True,
        )
    except Exception:
        pass
    # #endregion
else:
    # Configuration SQLite (développement local sans internet)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Évite staticfiles.W004 en prod si le dossier projet n'existe pas (ex. image Docker /app sans static/)
_project_static = BASE_DIR / 'static'
STATICFILES_DIRS = [_project_static] if _project_static.is_dir() else []

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================
# CORS Configuration (Cross-Origin Resource Sharing)
# ============================================
# Permet au frontend React (port 5173) d'appeler l'API Django (port 8000)
# Sans CORS, le navigateur bloque les requêtes cross-origin

# Headers autorisés dans les requêtes
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Méthodes HTTP autorisées
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Autoriser l'envoi de cookies et headers d'authentification
CORS_ALLOW_CREDENTIALS = True

# Durée de cache pour les requêtes preflight (24h)
CORS_PREFLIGHT_MAX_AGE = 86400

# Les origines autorisées sont définies dans development.py et production.py

# Django REST Framework
REST_FRAMEWORK = {
    # Permissions - Authentification requise par défaut
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    # Authentification - Session (navigateur) + JWT (apps/API)
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # JWT pour apps
        'rest_framework.authentication.SessionAuthentication',         # Session pour navigateur
    ],
    # Pagination
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    # Filtres
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    # Documentation API (Swagger/OpenAPI)
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # Handler d'exceptions personnalisé — désactivé avec apps.trading
    # 'EXCEPTION_HANDLER': 'apps.trading.utils.error_utils.custom_exception_handler',
}

# ============================================
# JWT Configuration (Simple JWT)
# ============================================
from datetime import timedelta

SIMPLE_JWT = {
    # Durée de vie des tokens
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),      # Token d'accès expire en 1h
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),      # Token de refresh expire en 7 jours
    
    # Rotation des tokens
    'ROTATE_REFRESH_TOKENS': True,                    # Nouveau refresh token à chaque refresh
    'BLACKLIST_AFTER_ROTATION': True,                 # Blacklister l'ancien refresh token
    
    # Algorithme de signature
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    
    # Headers
    'AUTH_HEADER_TYPES': ('Bearer',),                 # Format: "Bearer <token>"
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    
    # Token claims
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# Configuration drf-spectacular (documentation API)
SPECTACULAR_SETTINGS = {
    'TITLE': 'Trading App API',
    'DESCRIPTION': 'API REST pour application de trading multi-brokers',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# ============================================
# Logging Configuration
# ============================================
# Créer le dossier logs s'il n'existe pas
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    
    # Formatters - Comment formater les messages
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'detailed': {
            'format': '[{levelname:8}] {asctime} | {name:30} | {funcName}:{lineno} | {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    
    # Filters
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    
    # Handlers - Où écrire les logs
    'handlers': {
        # Console
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'detailed',
        },
        
        # Console debug (seulement en DEBUG)
        'console_debug': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'detailed',
        },
        
        # Fichier principal avec rotation
        'file': {
            'level': 'INFO',
            '()': SafeRotatingFileHandler,  # Utiliser le handler personnalisé
            'filename': LOG_DIR / 'django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'detailed',
            'encoding': 'utf-8',
        },
        
        # Fichier d'erreurs
        'error_file': {
            'level': 'ERROR',
            '()': SafeRotatingFileHandler,  # Utiliser le handler personnalisé
            'filename': LOG_DIR / 'errors.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10,
            'formatter': 'detailed',
            'encoding': 'utf-8',
        },
        
        # Fichier pour les brokers
        'broker_file': {
            'level': 'INFO',
            '()': SafeRotatingFileHandler,  # Utiliser le handler personnalisé
            'filename': LOG_DIR / 'brokers.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'detailed',
            'encoding': 'utf-8',
        },
        
        # Fichier pour la synchronisation
        'sync_file': {
            'level': 'INFO',
            '()': SafeRotatingFileHandler,  # Utiliser le handler personnalisé
            'filename': LOG_DIR / 'sync.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'detailed',
            'encoding': 'utf-8',
        },
    },
    
    # Root logger
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    
    # Loggers spécifiques
    'loggers': {
        # Django
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        
        # Trading App - Logger principal
        'trading': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        
        # Brokers - Logs séparés
        'trading.brokers': {
            'handlers': ['console', 'broker_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'trading.brokers.saxo': {
            'handlers': ['console', 'broker_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'trading.brokers.binance': {
            'handlers': ['console', 'broker_file'],
            'level': 'INFO',
            'propagate': False,
        },
        
        # Services
        'trading.services': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'trading.services.broker': {
            'handlers': ['console', 'broker_file'],
            'level': 'INFO',
            'propagate': False,
        },
        
        # Synchronisation - Logs séparés
        'trading.sync': {
            'handlers': ['console', 'sync_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'trading.services.sync': {
            'handlers': ['console', 'sync_file'],
            'level': 'INFO',
            'propagate': False,
        },
        
        # Exceptions et erreurs
        'trading.exceptions': {
            'handlers': ['console', 'error_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'trading.middleware': {
            'handlers': ['console', 'error_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'trading.middleware.errors': {
            'handlers': ['console', 'error_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        
        # Utilitaires
        'trading.utils': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
