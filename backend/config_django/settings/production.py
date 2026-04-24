"""
Configuration Django pour la production.
"""
import json
import os
import time
from .base import *
from urllib.parse import urlsplit

DEBUG = False

# Static files served via WhiteNoise (for Passenger/shared hosting)
# Insert WhiteNoise right after SecurityMiddleware in the MIDDLEWARE from base.py
MIDDLEWARE.insert(
    MIDDLEWARE.index('django.middleware.security.SecurityMiddleware') + 1,
    'whitenoise.middleware.WhiteNoiseMiddleware'
)

# WhiteNoise configuration - using simple storage for reliability
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get('ALLOWED_HOSTS', '').split(',')
    if h.strip()
]

# Database PostgreSQL : Railway/Render fournissent en général DATABASE_URL ;
# DB_* seuls sinon (même principe que Projet bachata V5 docs deploy-verification).
if os.environ.get("DATABASE_URL"):
    import dj_database_url
    # Lit DATABASE_URL dans os.environ (injectée par Railway quand la DB est liée).
    _db = dj_database_url.config(conn_max_age=600)
    DATABASES = {"default": _db}
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"].setdefault("connect_timeout", 10)
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='trading_app'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
            'OPTIONS': {'connect_timeout': 10},
        }
    }

# #region agent log
try:
    _raw = os.environ.get("DATABASE_URL", "")
    _p = urlsplit(_raw) if _raw else None
    _data = {
        "hypothesisId": "A",
        "using_database_url": bool(_raw),
        "db_url_host": getattr(_p, "hostname", None),
        "db_url_port": getattr(_p, "port", None),
        "db_url_user": getattr(_p, "username", None),
        "db_url_dbname": (getattr(_p, "path", "") or "").lstrip("/") or None,
        "db_url_password_set": bool(getattr(_p, "password", None)) if _p else False,
        "db_url_password_len": (len(getattr(_p, "password", "")) if (getattr(_p, "password", None) is not None) else 0)
        if _p
        else 0,
    }

    # Log en stdout pour Railway (sans secrets)
    print(
        "[debug-e5b425] hypothesisD db_url",
        "set=",
        _data["using_database_url"],
        "host=",
        _data["db_url_host"],
        "port=",
        _data["db_url_port"],
        "user=",
        _data["db_url_user"],
        "db=",
        _data["db_url_dbname"],
        "pwd_set=",
        _data["db_url_password_set"],
        "pwd_len=",
        _data["db_url_password_len"],
        flush=True,
    )

    _p = (BASE_DIR.parent / "debug-e5b425.log").resolve()
    with open(_p, "a", encoding="utf-8") as _f:
        _f.write(
            json.dumps(
                {
                    "sessionId": "e5b425",
                    "location": "production.py:DATABASES",
                    "message": "db config selected",
                    "data": {
                        **_data,
                    },
                    "timestamp": int(time.time() * 1000),
                }
            )
            + "\n"
        )
except OSError:
    pass
# #endregion

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
# Railway / reverse proxy : le conteneur voit souvent du HTTP ; sans cela,
# SECURE_SSL_REDIRECT peut renvoyer une 301 en boucle (Location = même URL).
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ============================================
# CORS pour la production
# ============================================
# Définir via variable d'environnement :
# CORS_ALLOWED_ORIGINS=https://ton-site.com,https://www.ton-site.com
def _normalize_cors_origin(raw: str) -> str | None:
    """
    django-cors-headers exige une origine sans path (pas de slash final).
    Ex: 'https://exemple.com/' => 'https://exemple.com'
    """
    value = (raw or "").strip()
    if not value:
        return None

    parts = urlsplit(value)
    if not parts.scheme or not parts.netloc:
        return None

    normalized = f"{parts.scheme}://{parts.netloc}".rstrip("/")
    return normalized or None


_raw_cors_origins = config('CORS_ALLOWED_ORIGINS', default='')
CORS_ALLOWED_ORIGINS = [
    origin
    for origin in (_normalize_cors_origin(v) for v in _raw_cors_origins.split(','))
    if origin
]

# Si aucune origine définie, utiliser une valeur par défaut sécurisée
if not CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS = []
    # En production, NE PAS utiliser CORS_ALLOW_ALL_ORIGINS = True

# Front Vercel (preview + prod) sans lister chaque URL (cf. Capital_Of_Fusion deploiement.md)
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^https://[\w-]+\.vercel\.app$',
]

# URLs exposées dans les réponses CORS
CORS_EXPOSE_HEADERS = [
    'Content-Type',
    'X-CSRFToken',
]

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
