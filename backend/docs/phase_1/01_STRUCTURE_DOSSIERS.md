# 📁 Structure de dossiers

## Vue d'ensemble

La structure du projet suit les bonnes pratiques Django avec une organisation modulaire.

## Structure complète

```
Trading_app_version4/
├── backend/                        # Backend Django
│   ├── config_django/              # Configuration principale
│   │   ├── __init__.py
│   │   ├── settings/               # Settings modulaires
│   │   │   ├── __init__.py         # Charge le bon settings
│   │   │   ├── base.py             # Settings communs
│   │   │   ├── development.py      # Dev (DEBUG=True)
│   │   │   └── production.py       # Prod (sécurisé)
│   │   ├── urls.py                 # URLs principales
│   │   ├── wsgi.py                 # WSGI pour déploiement
│   │   └── asgi.py                 # ASGI pour WebSockets
│   │
│   ├── apps/                       # Applications Django
│   │   ├── trading/                # App principale
│   │   │   ├── __init__.py
│   │   │   ├── apps.py             # Configuration app
│   │   │   ├── admin.py            # Admin Django
│   │   │   ├── models/             # Modèles (divisés)
│   │   │   │   ├── __init__.py     # Exports
│   │   │   │   ├── base.py         # Modèle de base
│   │   │   │   ├── assets.py       # AllAssets, Asset
│   │   │   │   ├── trading.py      # Position, Trade, Order
│   │   │   │   ├── strategies.py   # Strategy
│   │   │   │   ├── brokers.py      # Broker, BrokerAccount
│   │   │   │   └── automation.py   # ScheduledTask
│   │   │   ├── api/                # API REST (DRF)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── serializers.py
│   │   │   │   ├── views.py
│   │   │   │   ├── urls.py
│   │   │   │   └── auth_views.py
│   │   │   ├── tests/              # Tests
│   │   │   │   ├── __init__.py
│   │   │   │   └── test_api/
│   │   │   └── urls.py             # URLs de l'app
│   │   │
│   │   ├── macro_economics/        # App économie macro
│   │   │   └── __init__.py
│   │   │
│   │   └── ai_assistant/           # App IA
│   │       └── __init__.py
│   │
│   ├── templates/                  # Templates Django
│   ├── static/                     # Fichiers statiques
│   ├── media/                      # Fichiers uploadés
│   ├── logs/                       # Logs applicatifs
│   │
│   ├── docs/                       # Phases détaillées, runbooks (index : docs/backend/INDEX.md)
│   │   ├── phase_1/
│   │   └── phase_2/
│   │
│   ├── manage.py                   # CLI Django
│   ├── requirements.txt            # Dépendances Python
│   ├── .env                        # Variables d'environnement
│   └── .env.example                # Exemple .env
│
├── frontend/                       # Frontend React (future)
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
│
├── venv/                           # Environnement virtuel
└── .gitignore
```

## Pourquoi cette structure ?

### 1. Settings modulaires (`config_django/settings/`)

Au lieu d'un seul `settings.py`, on a :
- `base.py` : Configuration commune (INSTALLED_APPS, MIDDLEWARE, etc.)
- `development.py` : Configuration dev (DEBUG=True, CORS permissif)
- `production.py` : Configuration prod (sécurité renforcée)

**Avantage** : Pas de `if DEBUG:` partout dans le code.

### 2. Modèles divisés (`models/`)

Au lieu d'un gros `models.py`, on a :
- `base.py` : Modèle abstrait `TimeStampedModel`
- `assets.py` : Modèles liés aux assets
- `trading.py` : Modèles liés au trading
- etc.

**Avantage** : Fichiers plus petits, plus faciles à maintenir.

### 3. API séparée (`api/`)

L'API REST est dans son propre dossier :
- `serializers.py` : Sérialisation JSON
- `views.py` : ViewSets
- `urls.py` : Routes API
- `auth_views.py` : Authentification

**Avantage** : Séparation claire entre API et modèles.

## Commandes de création

```bash
# Créer la structure
mkdir -p backend/config_django/settings
mkdir -p backend/apps/trading/models
mkdir -p backend/apps/trading/api
mkdir -p backend/apps/trading/tests/test_api
mkdir -p backend/apps/macro_economics
mkdir -p backend/apps/ai_assistant
mkdir -p backend/templates
mkdir -p backend/static
mkdir -p backend/media
mkdir -p backend/logs
mkdir -p backend/docs/phase_1
mkdir -p backend/docs/phase_2
mkdir -p frontend/src
```

## Fichiers essentiels créés

| Fichier | Description |
|---------|-------------|
| `manage.py` | Point d'entrée CLI Django |
| `config_django/urls.py` | URLs principales |
| `config_django/wsgi.py` | WSGI pour Gunicorn |
| `apps/trading/apps.py` | Configuration de l'app |
| `requirements.txt` | Dépendances Python |
| `.env` | Variables d'environnement |
| `.gitignore` | Fichiers à ignorer |

