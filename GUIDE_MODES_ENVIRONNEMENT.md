# Guide : Basculer entre Production et Développement

**Trading App v4 - Modes d'Environnement**

Ce guide explique comment basculer entre les modes **Production** et **Développement** pour le backend Django et le frontend React.

Pour un déploiement **Vercel (frontend) + Railway (backend)**, voir **`docs/DEPLOIEMENT_VERCEL_RAILWAY.md`** (Procfile, variables, CORS `*.vercel.app`, `SECURE_PROXY_SSL_HEADER`, dépannage).

---

## Table des Matières

1. [Backend Django](#backend-django)
2. [Frontend React](#frontend-react)
3. [Base de Données](#base-de-données)
4. [Vérifications](#vérifications)
5. [Tableau Récapitulatif](#tableau-récapitulatif)

---

## Backend Django

### 🔴 Mode Production

**Configuration :**
- **Settings module :** `config_django.settings.production`
- **DEBUG :** `False`
- **ALLOWED_HOSTS :** `le-baff.com,www.le-baff.com`
- **Base de données :** Supabase PostgreSQL (Connection Pooler)
- **Fichiers statiques :** WhiteNoise
- **CORS :** Restreint aux domaines autorisés

#### Activer le Mode Production

**1. Variables d'environnement (`.env` ou `prod.env`) :**

```env
SECRET_KEY=dev-secret-key-change-in-production
DEBUG=False
ALLOWED_HOSTS=le-baff.com,www.le-baff.com,localhost,127.0.0.1

USE_SUPABASE=True
DB_NAME=postgres
DB_USER=postgres.lowncckbivxmiakzmsxq
DB_PASSWORD=Niveaux22!!
DB_HOST=aws-1-eu-west-1.pooler.supabase.com
DB_PORT=6543

CORS_ALLOWED_ORIGINS=https://le-baff.com,https://www.le-baff.com
```

**2. Lancer le serveur :**

```bash
# Définir le module de settings
export DJANGO_SETTINGS_MODULE=config_django.settings.production

# OU utiliser directement dans la commande
python manage.py runserver --settings=config_django.settings.production

# Ou avec Gunicorn (recommandé)
gunicorn --config gunicorn.conf.py config_django.wsgi:application
```

**3. Sur le serveur HostArmada :**
- Le fichier `passenger_wsgi.py` charge automatiquement `production`
- Pas besoin de configuration supplémentaire

---

### 🟢 Mode Développement

**Configuration :**
- **Settings module :** `config_django.settings.development`
- **DEBUG :** `True`
- **ALLOWED_HOSTS :** `*` (tous les hôtes acceptés)
- **Base de données :** SQLite (local) ou Supabase
- **Fichiers statiques :** Servis par Django dev server
- **CORS :** Permissif

#### Activer le Mode Développement

**1. Variables d'environnement (`.env`) :**

```env
SECRET_KEY=dev-secret-key-for-local-testing
DEBUG=True
ALLOWED_HOSTS=*

# Option 1: SQLite (local)
USE_SUPABASE=False
DB_NAME_SQLITE=db.sqlite3

# Option 2: Supabase (si tu veux tester avec la prod DB)
# USE_SUPABASE=True
# DB_NAME=postgres
# DB_USER=postgres.lowncckbivxmiakzmsxq
# DB_PASSWORD=Niveaux22!!
# DB_HOST=aws-1-eu-west-1.pooler.supabase.com
# DB_PORT=6543

CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

**2. Lancer le serveur :**

```bash
# Par défaut, Django utilise development
python manage.py runserver

# Ou explicitement
export DJANGO_SETTINGS_MODULE=config_django.settings.development
python manage.py runserver

# Ou directement
python manage.py runserver --settings=config_django.settings.development
```

**3. Accès :**
- Backend API : http://localhost:8000/api/
- Admin Django : http://localhost:8000/admin

---

### 🟡 Mode Production Test (Hybride)

**Configuration :**
- **Settings module :** `config_django.settings.production_test`
- **DEBUG :** `True` (pour le debugging)
- **Base de données :** Supabase PostgreSQL
- **Fichiers statiques :** Collectés
- **CORS :** Production settings

**Utilisation :** Tester la configuration de production localement

```bash
export DJANGO_SETTINGS_MODULE=config_django.settings.production_test
python manage.py runserver
```

---

## Frontend React

### 🔴 Mode Production

**Configuration :**
- **API URL :** `https://le-baff.com/api`
- **Build :** Optimisé, minifié
- **Source maps :** Désactivées
- **Vérification TypeScript :** Désactivée (build:fast)

#### Activer le Mode Production

**1. Fichier `.env.production` :**

```env
VITE_API_BASE_URL=https://le-baff.com/api
VITE_ENV=production
```

**2. Build :**

```bash
npm run build:fast
```

**3. Déploiement :**

Upload du dossier `dist/` vers `public_html/` sur le serveur.

**4. Test local du build production :**

```bash
npm run preview
```

Accès : http://localhost:4173

---

### 🟢 Mode Développement

**Configuration :**
- **API URL :** `http://localhost:8000/api`
- **Build :** Dev build, source maps activées
- **Hot reload :** Activé
- **Vérification TypeScript :** En temps réel

#### Activer le Mode Développement

**1. Fichier `.env.development` (ou `.env`) :**

```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_ENV=development
```

**2. Lancer le serveur de dev :**

```bash
npm run dev
```

**3. Accès :**
- Frontend : http://localhost:5173
- API Backend : http://localhost:8000/api

---

## Base de Données

### 🔴 Production : Supabase PostgreSQL

**Configuration dans `.env` :**

```env
USE_SUPABASE=True
DB_NAME=postgres
DB_USER=postgres.lowncckbivxmiakzmsxq
DB_PASSWORD=Niveaux22!!
DB_HOST=aws-1-eu-west-1.pooler.supabase.com
DB_PORT=6543
```

**Avantages :**
- Base de données cloud
- Plusieurs utilisateurs simultanés
- Backup automatique
- Accessible depuis n'importe où

**Commandes :**

```bash
# Migrations
python manage.py migrate

# Accès psql (si configuré)
psql -h aws-1-eu-west-1.pooler.supabase.com -p 6543 -U postgres.lowncckbivxmiakzmsxq -d postgres
```

---

### 🟢 Développement : SQLite (Local)

**Configuration dans `.env` :**

```env
USE_SUPABASE=False
DB_NAME_SQLITE=db.sqlite3
```

**Avantages :**
- Fichier local (pas de connexion internet nécessaire)
- Rapide pour le développement
- Facile à réinitialiser
- Pas de coûts

**Commandes :**

```bash
# Migrations
python manage.py migrate

# Réinitialiser la DB
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser

# Shell Django
python manage.py shell
```

---

## Vérifications

### Vérifier le Mode Actuel

#### Backend Django

```bash
# Dans le shell Django
python manage.py shell

>>> from django.conf import settings
>>> print(f"DEBUG: {settings.DEBUG}")
>>> print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
>>> print(f"DATABASE: {settings.DATABASES['default']['ENGINE']}")
>>> print(f"SETTINGS MODULE: {settings.SETTINGS_MODULE}")
```

**Sortie attendue (Production) :**
```
DEBUG: False
ALLOWED_HOSTS: ['le-baff.com', 'www.le-baff.com', 'localhost', '127.0.0.1']
DATABASE: django.db.backends.postgresql
SETTINGS MODULE: config_django.settings.production
```

**Sortie attendue (Développement) :**
```
DEBUG: True
ALLOWED_HOSTS: ['*']
DATABASE: django.db.backends.sqlite3
SETTINGS MODULE: config_django.settings.development
```

#### Frontend React

```bash
# Vérifier les variables d'environnement en dev
npm run dev
# Ouvrir http://localhost:5173
# Console navigateur > Application > Local Storage
# Vérifier les appels réseau : doivent pointer vers localhost:8000 ou le-baff.com
```

**Dans le code JS (console du navigateur) :**
```javascript
console.log(import.meta.env.VITE_API_BASE_URL)
// Production: https://le-baff.com/api
// Développement: http://localhost:8000/api
```

---

### Tests de Validation

#### Backend

```bash
# Test de connexion DB
python manage.py check

# Test avec déploiement check
python manage.py check --deploy

# Test migration
python manage.py migrate --plan

# Collecter les fichiers statiques (prod)
python manage.py collectstatic --dry-run
```

#### Frontend

```bash
# Test de build
npm run build:fast

# Vérifier la taille des bundles
ls -lh dist/assets/

# Test du build localement
npm run preview
```

---

## Tableau Récapitulatif

| Aspect | 🟢 Développement | 🔴 Production |
|--------|------------------|---------------|
| **Backend Settings** | `development` | `production` |
| **DEBUG** | `True` | `False` |
| **Base de données** | SQLite (local) | PostgreSQL (Supabase) |
| **ALLOWED_HOSTS** | `*` | `le-baff.com, www.le-baff.com` |
| **CORS** | Permissif | Restreint |
| **Fichiers statiques** | Django dev server | WhiteNoise |
| **Backend URL** | `http://localhost:8000` | `https://le-baff.com` |
| **Frontend Dev Server** | `http://localhost:5173` | N/A (build statique) |
| **Frontend Build** | Non requis | Requis (`npm run build:fast`) |
| **API URL (frontend)** | `http://localhost:8000/api` | `https://le-baff.com/api` |
| **Source Maps** | Activées | Désactivées |
| **Minification** | Non | Oui |
| **HTTPS** | Non | Oui |
| **Logs** | Console | Fichiers (`/home/lebaffc1/logs/`) |

---

## Commandes Rapides

### Basculer en Développement

```bash
# Backend
export DJANGO_SETTINGS_MODULE=config_django.settings.development
python manage.py runserver

# Frontend
npm run dev
```

### Basculer en Production (Local)

```bash
# Backend
export DJANGO_SETTINGS_MODULE=config_django.settings.production
python manage.py collectstatic --noinput
gunicorn config_django.wsgi:application

# Frontend
npm run build:fast
npm run preview
```

### Basculer en Production (Serveur)

```bash
# Connexion SSH
ssh -p 19199 -i id_rsa_v2 lebaffc1@fra2.hostarmada.net

# Backend (déjà configuré via passenger_wsgi.py)
source /home/lebaffc1/virtualenv/Trading_app_version4/backend/3.12/bin/activate
cd /home/lebaffc1/Trading_app_version4/backend
./deploy.sh

# Redémarrer via cPanel > Setup Python App > RESTART
```

---

## Pièges à Éviter

### ❌ Erreurs Communes

1. **Oublier de changer `.env` avant le build frontend**
   - Solution : Vérifier `VITE_API_BASE_URL` avant `npm run build`

2. **Utiliser `DEBUG=True` en production**
   - Risque : Exposition des données sensibles
   - Solution : Toujours `DEBUG=False` en prod

3. **CORS mal configuré**
   - Symptôme : Erreurs CORS dans la console navigateur
   - Solution : Vérifier `CORS_ALLOWED_ORIGINS` correspond au domaine frontend

4. **Base de données incorrecte**
   - Symptôme : Données manquantes ou erreurs de connexion
   - Solution : Vérifier `USE_SUPABASE` et les variables `DB_*`

5. **Fichiers statiques non collectés**
   - Symptôme : Admin Django sans CSS
   - Solution : `python manage.py collectstatic --noinput`

6. **Oublier de rebuild le frontend après modification**
   - Symptôme : Modifications non visibles en production
   - Solution : Toujours `npm run build:fast` avant upload

---

## Workflows Recommandés

### Workflow Développement

1. Lancer le backend en mode dev : `python manage.py runserver`
2. Lancer le frontend en mode dev : `npm run dev`
3. Développer et tester localement
4. Commiter les changements sur Git

### Workflow Déploiement

1. **Tests locaux :**
   ```bash
   python manage.py test
   npm run build:fast
   ```

2. **Backend vers production :**
   ```bash
   # Upload des fichiers modifiés
   scp -P 19199 -i id_rsa_v2 [fichiers] lebaffc1@fra2.hostarmada.net:...
   
   # SSH et déploiement
   ssh lebaffc1@fra2.hostarmada.net
   cd Trading_app_version4/backend
   ./deploy.sh
   
   # Redémarrer via cPanel
   ```

3. **Frontend vers production :**
   ```bash
   # Build
   npm run build:fast
   
   # Upload
   scp -r -P 19199 -i ../backend/id_rsa_v2 dist/* lebaffc1@fra2.hostarmada.net:public_html/
   ```

---

## Variables d'Environnement - Référence Complète

### Backend `.env`

```env
# Django Core
SECRET_KEY=dev-secret-key-change-in-production
DEBUG=True|False
ALLOWED_HOSTS=*|le-baff.com,www.le-baff.com

# Database
USE_SUPABASE=True|False
DB_NAME=postgres|nom_de_la_db
DB_NAME_SQLITE=db.sqlite3
DB_USER=postgres.xxxxx
DB_PASSWORD=mot_de_passe
DB_HOST=aws-1-eu-west-1.pooler.supabase.com|localhost
DB_PORT=6543|5432

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000|https://le-baff.com
```

### Frontend `.env`

```env
# API Configuration
VITE_API_BASE_URL=http://localhost:8000/api|https://le-baff.com/api

# Environment
VITE_ENV=development|production
```

---

## Support

**En cas de problème :**

1. Vérifier les logs :
   - Backend : Console ou `/home/lebaffc1/logs/django.log`
   - Frontend : Console navigateur (F12)

2. Vérifier les variables d'environnement :
   ```bash
   # Backend
   python manage.py shell
   >>> from django.conf import settings
   >>> print(settings.DEBUG)
   
   # Frontend
   console.log(import.meta.env)
   ```

3. Consulter les guides :
   - `RAPPORT_DEPLOIEMENT_HOSTARMADA.md`
   - `GUIDE_CRON_SAXO_TOKENS.md`

---

**Dernière mise à jour :** 04/01/2026
