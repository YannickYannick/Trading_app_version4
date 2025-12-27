# 📝 Logging Configuré - Documentation

## Vue d'ensemble

Le système de logging permet de tracer l'exécution de l'application, faciliter le débogage et monitorer les opérations.

## Configuration principale

### Fichier : `config_django/settings/base.py`

La configuration utilise le système de logging de Django/Python avec :

- **Formatters** : Comment formater les messages
- **Handlers** : Où écrire les logs
- **Loggers** : Quels modules logger

### Dossier des logs

```python
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)
```

Les fichiers de log sont stockés dans `/backend/logs/`:
- `django.log` : Logs généraux Django
- `errors.log` : Erreurs uniquement
- `brokers.log` : Logs des brokers (Saxo, Binance)
- `sync.log` : Logs de synchronisation
- `app.json.log` : Logs structurés en JSON

## Formatters

### 1. Verbose
```
INFO 2024-01-15 10:30:00,000 module 12345 67890 Message
```

### 2. Simple
```
INFO Message
```

### 3. Detailed
```
[INFO    ] 2024-01-15 10:30:00 | module.function:123 | Message
```

### 4. Colored (Console)
```
✅ INFO 10:30:00 trading.sync Message
```
Avec couleurs ANSI :
- DEBUG: Cyan
- INFO: Vert  
- WARNING: Jaune
- ERROR: Rouge
- CRITICAL: Magenta

### 5. JSON (Structuré)
```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "logger": "trading.sync",
  "message": "Sync completed",
  "module": "asset_sync_service",
  "function": "sync_all_assets",
  "line": 45
}
```

## Formatters personnalisés

### Fichier : `apps/trading/utils/logging/formatters.py`

#### ColoredFormatter
```python
from apps.trading.utils.logging import ColoredFormatter

# Dans settings
'formatters': {
    'colored': {
        '()': 'apps.trading.utils.logging.ColoredFormatter',
        'format': '{levelname} {asctime} {name} {message}',
        'style': '{',
    },
}
```

#### JSONFormatter
```python
from apps.trading.utils.logging import JSONFormatter

# Dans settings
'formatters': {
    'json': {
        '()': 'apps.trading.utils.logging.JSONFormatter',
    },
}
```

## Handlers

### Console
```python
'console': {
    'level': 'INFO',
    'class': 'logging.StreamHandler',
    'formatter': 'colored',
}
```

### Fichiers avec rotation
```python
'file': {
    'level': 'INFO',
    'class': 'logging.handlers.RotatingFileHandler',
    'filename': LOG_DIR / 'django.log',
    'maxBytes': 1024 * 1024 * 10,  # 10 MB
    'backupCount': 5,
    'formatter': 'detailed',
    'encoding': 'utf-8',
}
```

La rotation crée des fichiers :
- `django.log` (actuel)
- `django.log.1` (précédent)
- `django.log.2`, etc.

## Loggers par module

| Logger | Handlers | Niveau |
|--------|----------|--------|
| `trading` | console, file, json_file | INFO |
| `trading.brokers` | console, broker_file | INFO |
| `trading.brokers.saxo` | console, broker_file | INFO |
| `trading.brokers.binance` | console, broker_file | INFO |
| `trading.sync` | console, sync_file | INFO |
| `trading.exceptions` | console, error_file | WARNING |
| `trading.middleware` | console, error_file | WARNING |

## Utilisation dans le code

### Import du logger
```python
import logging

logger = logging.getLogger('trading.brokers.saxo')
```

### Niveaux de logging
```python
logger.debug("Détails pour débogage")
logger.info("Opération réussie")
logger.warning("Attention, token expire bientôt")
logger.error("Erreur rencontrée", exc_info=True)
logger.critical("Erreur critique, arrêt possible")
```

### Logging avec contexte
```python
logger.info(
    "Sync terminée",
    extra={
        'user_id': user.id,
        'broker_type': 'saxo',
        'assets_count': 150
    }
)
```

### Logger avec adaptateur
```python
from apps.trading.utils.logging.formatters import get_trading_logger

logger = get_trading_logger(
    'trading.sync',
    user_id=1,
    broker_type='saxo'
)

# Tous les logs incluent automatiquement user_id et broker_type
logger.info("Starting sync")
```

## Bonnes pratiques

### ✅ À faire

```python
# Inclure exc_info pour les exceptions
logger.error(f"Erreur: {e}", exc_info=True)

# Utiliser le bon niveau
logger.debug("Valeur intermédiaire")  # Pas en production
logger.info("Opération terminée")      # Infos utiles
logger.error("Échec de l'opération")   # Erreurs

# Masquer les données sensibles
logger.info(f"API Key: {api_key[:4]}...")
```

### ❌ À éviter

```python
# Ne pas logger les secrets
logger.info(f"Password: {password}")
logger.info(f"API Secret: {secret}")

# Ne pas logger trop
logger.debug(f"Variable i = {i}")  # Dans une boucle
```

## Structure des fichiers de log

```
backend/
└── logs/
    ├── django.log        # Logs généraux
    ├── django.log.1      # Backup 1
    ├── errors.log        # Erreurs uniquement
    ├── brokers.log       # Logs des brokers
    ├── sync.log          # Logs de synchronisation
    └── app.json.log      # Logs structurés JSON
```

## Résumé

| Composant | Fichier | Description |
|-----------|---------|-------------|
| Configuration | `settings/base.py` | Config LOGGING Django |
| ColoredFormatter | `utils/logging/formatters.py` | Couleurs console |
| JSONFormatter | `utils/logging/formatters.py` | Logs structurés |
| DetailedFormatter | `utils/logging/formatters.py` | Format verbeux |

Le logging est maintenant configuré pour :
- ✅ Tracer toutes les opérations
- ✅ Séparer les logs par module
- ✅ Rotation automatique des fichiers
- ✅ Format JSON pour l'analyse
- ✅ Couleurs en console pour le développement

