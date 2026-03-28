# 📚 Documentation Trading App v4

## Vue d'ensemble

Cette documentation couvre l'ensemble du développement de l'application Trading App v4, une application de trading multi-brokers construite avec Django REST Framework et React.

## 🏗️ Architecture

```
Trading_app_version4/
├── backend/                    # Backend Django
│   ├── config_django/          # Configuration Django
│   │   ├── settings/           # Settings modulaires
│   │   │   ├── base.py         # Configuration commune
│   │   │   ├── development.py  # Dev (DEBUG=True)
│   │   │   └── production.py   # Prod (sécurisé)
│   │   ├── urls.py             # URLs principales
│   │   └── wsgi.py             # WSGI config
│   ├── apps/                   # Applications Django
│   │   ├── trading/            # App principale
│   │   │   ├── models/         # Modèles (modulaires)
│   │   │   ├── api/            # API REST (DRF)
│   │   │   ├── admin.py        # Admin Django
│   │   │   └── tests/          # Tests
│   │   ├── macro_economics/    # App économie macro
│   │   └── ai_assistant/       # App IA
│   ├── docs/                   # Documentation
│   └── requirements.txt        # Dépendances Python
├── frontend/                   # Frontend React (future)
└── venv/                       # Environnement virtuel
```

## 📋 Phases de développement

### [Phase 1 : Backend de base](phase_1/README.md)
- Structure de dossiers
- Configuration Django
- Modèles de données
- Admin Django

### [Phase 2 : API REST](phase_2/README.md)
- Django REST Framework
- Serializers
- ViewSets
- Authentification (Session + JWT)
- Tests API

### Phase 3 : Frontend React (à venir)
- Setup Vite + React + TypeScript
- Composants UI
- État global (Zustand/Redux)
- Intégration API

### Phase 4 : Intégration Brokers (à venir)
- Saxo Bank API
- Binance API
- Synchronisation des données

### [Phase 7 : Système de Stratégies](phase_7/README.md)
- Modèles de stratégies et exécution
- Algorithmes de trading (Threshold, RSI, MA Crossover, etc.)
- API REST pour gestion des stratégies
- Interface React avec React Table
- Exécution automatique et manuelle

## 🔧 Stack technique

| Composant | Technologie |
|-----------|-------------|
| Backend | Django 5.x + DRF |
| Database | PostgreSQL (Supabase) |
| Auth | Session + JWT |
| Frontend | React + TypeScript + Vite |
| API Docs | Swagger (drf-spectacular) |

## 🚀 Démarrage rapide

```bash
# Backend
cd backend
python -m venv ../venv
../venv/Scripts/activate  # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# API disponible sur http://localhost:8000/api/
# Admin sur http://localhost:8000/admin/
# Swagger sur http://localhost:8000/api/docs/
```

## 📊 Base de données

Connecté à **Supabase PostgreSQL** :
- Host: `db.lowncckbivxmiakzmsxq.supabase.co`
- Port: `5432`
- Database: `postgres`

## 📁 Structure des docs

```
docs/
├── INDEX.md                                    # Ce fichier
├── fix-uic-extraction-and-optimization.md      # Correction UIC et optimisations (29/12/2025)
├── debug-binance-balance-conversion.md         # Debug conversion balance Binance
├── debug-yahoo-validation.md                   # Debug validation Yahoo Finance
├── debug-saxo-price-api.md                     # Problème récupération prix Saxo (29/12/2025)
├── phase_1/                                    # Phase 1 - Backend
│   ├── README.md
│   ├── 01_STRUCTURE_DOSSIERS.md
│   ├── 02_SETTINGS_DJANGO.md
│   ├── 03_APP_TRADING.md
│   ├── 04_MODELES.md
│   ├── 05_MIGRATIONS.md
│   ├── 06_ADMIN_DJANGO.md
│   └── 07_TESTS_MODELES.md
└── phase_2/                                    # Phase 2 - API REST
    ├── README.md
    ├── 01_DRF_INSTALLATION.md
    ├── 02_SERIALIZERS.md
    ├── 03_VIEWSETS.md
    ├── 04_URLS_API.md
    ├── 05_CORS.md
    ├── 06_AUTHENTIFICATION.md
    └── 07_TESTS_API.md
└── phase_7/                                    # Phase 7 - Système de Stratégies
    ├── README.md
    ├── STRATEGIES_OVERVIEW.md
    ├── STRATEGIES_MODELS.md
    ├── STRATEGIES_ALGORITHMS.md
    ├── STRATEGIES_API.md
    ├── STRATEGIES_SERVICES.md
    ├── STRATEGIES_FRONTEND.md
    ├── STRATEGIES_EXECUTION.md
    └── STRATEGIES_EXAMPLES.md
```

## 🔧 Corrections et Optimisations

### [Correction UIC Extraction et Optimisations](fix-uic-extraction-and-optimization.md)
**Date :** 29 Décembre 2025

Correction de l'extraction UIC Saxo et optimisations majeures :
- ✅ Correction : utilisation de `'Identifier'` au lieu de `'Uic'` pour l'API `/ref/v1/instruments`
- ✅ UIC sauvegardé à 100% (28 848/28 848 assets)
- ✅ Optimisation : bulk operations au lieu de requêtes individuelles
- ✅ Timeout frontend augmenté à 10 minutes pour synchronisations longues
- ✅ Handler logging sécurisé pour Windows

## 🐛 Débogage et Problèmes

### [Problème récupération prix Saxo pour validation Yahoo](debug-saxo-price-api.md)
**Date :** 29 Décembre 2025

Problème rencontré lors de la récupération des prix Saxo pour la validation Yahoo Finance :
- 🔍 Structure de réponse API variable (avec/sans tableau `Data`)
- 🔍 Accès aux prix refusé (`PriceTypeAsk/Bid: "NoAccess"`, `Amount: 0`)
- ✅ Solutions implémentées : gestion des structures multiples, priorités des champs, logging détaillé
- ⚠️ Limitation : permissions du compte peuvent bloquer l'accès aux prix

## 🔄 Migrations### [Migration Saxo : SIM → LIVE](migration-saxo-sim-to-live.md)
**Date :** 29 Décembre 2025

Migration complète de l'environnement Saxo Bank de SIM vers LIVE :
- ✅ Modification de tous les défauts de configuration (`'simulation'` → `'live'`)
- ✅ Remplacement des URLs SIM hardcodées par LIVE
- ✅ Script de migration Django pour mettre à jour les comptes existants
- ✅ Script de test de validation pour vérifier la migration
- 🎯 Objectif : Éliminer les erreurs `NoAccess` en utilisant l'environnement LIVE