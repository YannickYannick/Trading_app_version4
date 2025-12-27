# 🌐 CORS Configuration

## Qu'est-ce que CORS ?

**CORS** (Cross-Origin Resource Sharing) permet au frontend React (port 5173) d'appeler l'API Django (port 8000).

Sans CORS, le navigateur bloque les requêtes cross-origin.

## Installation

```bash
pip install django-cors-headers
```

## Configuration

### INSTALLED_APPS

```python
INSTALLED_APPS = [
    # ...
    'corsheaders',
    # ...
]
```

### MIDDLEWARE (en premier !)

```python
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # ← EN PREMIER
    'django.middleware.security.SecurityMiddleware',
    # ...
]
```

### Configuration base.py

```python
# Headers autorisés
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

# Autoriser les cookies et headers d'auth
CORS_ALLOW_CREDENTIALS = True

# Cache pour les requêtes preflight (24h)
CORS_PREFLIGHT_MAX_AGE = 86400
```

### Configuration development.py

```python
# Origines autorisées en développement
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",    # Vite
    "http://127.0.0.1:5173",
    "http://localhost:3000",    # CRA / Next.js
    "http://127.0.0.1:3000",
]

# Alternative : autoriser tout (moins sécurisé)
# CORS_ALLOW_ALL_ORIGINS = True
```

### Configuration production.py

```python
import os

# Origines depuis variable d'environnement
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
    if origin.strip()
]
```

## Vérification

```python
# Vérifier la configuration
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config_django.settings.development')
import django
django.setup()
from django.conf import settings
print('CORS_ALLOWED_ORIGINS:', settings.CORS_ALLOWED_ORIGINS)
print('CORS_ALLOW_CREDENTIALS:', settings.CORS_ALLOW_CREDENTIALS)
print('CorsMiddleware position:', settings.MIDDLEWARE.index('corsheaders.middleware.CorsMiddleware'))
"
```

## Frontend (Axios)

```typescript
// frontend/src/services/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  withCredentials: true,  // ← Important pour CORS avec credentials
});

export default api;
```

## Erreurs courantes

### "No 'Access-Control-Allow-Origin' header"

**Solution** : Vérifier que `corsheaders` est dans INSTALLED_APPS et MIDDLEWARE.

### "Credentials flag is true, but Access-Control-Allow-Credentials is not 'true'"

**Solution** : Ajouter `CORS_ALLOW_CREDENTIALS = True`.

### "Request header field authorization is not allowed"

**Solution** : Ajouter `'authorization'` dans `CORS_ALLOW_HEADERS`.

## Test avec curl

```bash
curl -X OPTIONS http://localhost:8000/api/assets/ \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" \
  -v
```

Réponse attendue :
```
< Access-Control-Allow-Origin: http://localhost:5173
< Access-Control-Allow-Credentials: true
```

