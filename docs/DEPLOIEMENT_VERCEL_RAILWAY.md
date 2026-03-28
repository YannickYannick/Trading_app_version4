# Déploiement — Trading App v4 (Vercel + Railway)

Guide aligné sur la méthode documentée pour [Capital_Of_Fusion_version5](https://github.com/YannickYannick/Capital_Of_Fusion_version5) (`docs/explication/hebergement.md`, `docs/explication/deploiement.md`), adapté à **React + Vite** (frontend) et **Django** (`config_django`, pas `config`).

**Ordre recommandé :** déployer le **backend** (Railway), noter l’URL HTTPS, puis le **frontend** (Vercel) avec les variables `VITE_*`.

---

## 1. Backend — Railway

### 1.1 Projet et repo

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub** → repo `Trading_app_version4`.
2. Branche conseillée : `deploiement`, `main` ou `avril-2026` selon ton flux.

### 1.2 Répertoire racine du service

Dans **Settings** du service web :

- **Root Directory** : `backend`

Railway utilisera le **`Procfile`** à cet emplacement.

### 1.3 Base PostgreSQL

- **Option A — Supabase** (comme en local) : pas de plugin PostgreSQL Railway ; renseigne `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` (souvent **pooler** `*.pooler.supabase.com` port **6543** pour éviter les soucis IPv6 depuis Railway).
- **Option B — PostgreSQL Railway** : **New** → **Database** → **PostgreSQL**, puis référence les variables fournies (`PGHOST`, etc.) ou copie-les dans `DB_*`.

### 1.4 Variables d’environnement (service backend)

| Variable | Description |
|----------|-------------|
| `DJANGO_SETTINGS_MODULE` | `config_django.settings.production` (recommandé, même si le `Procfile` l’exporte aussi) |
| `SECRET_KEY` | Clé Django forte (unique prod) |
| `ALLOWED_HOSTS` | Domaine Railway **sans** `https://`, séparés par des virgules : `trading-production-xxxx.up.railway.app`, `le-baff.com` si custom |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Connexion PostgreSQL |
| `USE_SUPABASE` | `true` si tu utilises la config Supabase de `base.py` (sinon adapter) |
| `CORS_ALLOWED_ORIGINS` | Optionnel : domaines **non** Vercel, ex. `https://le-baff.com,https://www.le-baff.com` |

Les origines **`https://*.vercel.app`** sont autorisées par **regex** dans `config_django/settings/production.py` (`CORS_ALLOWED_ORIGIN_REGEXES`).

Autres secrets métier : clés brokers, `GEMINI_*`, etc. — comme sur HostArmada / `.env` local, **sans** commiter le `.env`.

### 1.5 Réseau public (Railway)

**Networking** : génère un domaine `*.up.railway.app` et mappe le port vers celui sur lequel **Gunicorn** écoute. Le `Procfile` utilise **`$PORT`** (injecté par Railway) : **ne force pas** `8000` dans la commande de démarrage.

### 1.6 Commande de démarrage

Le fichier `backend/Procfile` exécute :

1. `collectstatic` + `migrate` avec **`DJANGO_SETTINGS_MODULE=config_django.settings.production`** (nécessaire car `manage.py` défaut = `development`).
2. `gunicorn config_django.wsgi:application --bind 0.0.0.0:$PORT`

Si tu overrides dans le dashboard, garde la même logique (y compris `bash -c 'export DJANGO_SETTINGS_MODULE=...'`).

### 1.7 Ne pas écraser la prod avec un `.env` embarqué

Si un fichier `.env` est copié dans l’image Docker / le build et contient une autre base, il peut prendre le pas sur les variables Railway (comportement `decouple` / `setdefault`). En prod Railway, privilégie les **variables du dashboard** ; évite d’embarquer un `.env` de dev. (Voir l’esprit du correctif décrit dans le projet Bachata : `bug_2026-03-07_railway_db_env_override`.)

### 1.8 Superuser et checks

```bash
railway run python manage.py createsuperuser
```

(avec CLI liée au bon projet / service ; `DJANGO_SETTINGS_MODULE` peut être requis selon le contexte.)

Santé API : `GET https://<ton-backend>.up.railway.app/api/health/`

---

## 2. Frontend — Vercel

### 2.1 Projet

1. [vercel.com](https://vercel.com) → **Add New** → **Project** → importer le repo GitHub.

### 2.2 Root Directory

- **Root Directory** : `frontend`

### 2.3 Framework

- **Framework Preset** : **Vite** (ou « Other » avec les commandes ci-dessous).

### 2.4 Build

- **Install** : `npm install`
- **Build** : `npm run build`
- **Output** : `dist`

Le fichier `frontend/vercel.json` définit des **rewrites** SPA (toutes les routes → `index.html`) pour React Router.

### 2.5 Variables d’environnement (à chaque déploiement / branche)

Les variables **`VITE_*`** sont figées **au build** : après modification, faire un **Redeploy**.

| Variable | Exemple | Rôle |
|----------|---------|------|
| `VITE_API_BASE_URL` | `https://trading-production-xxxx.up.railway.app/api` | URL de base de l’API (**avec** le suffixe `/api`, comme en local) |
| `VITE_ENV` | `production` | Filtre dev / prod côté front si utilisé |

`frontend/src/utils/config.ts` lit `VITE_API_BASE_URL` ; le service IA utilise la même base via `config.apiBaseUrl`.

---

## 3. CORS et cookies

- **Vercel** : couvert par la regex `*.vercel.app` côté Django.
- **Domaine perso** (ex. `le-baff.com` sur Vercel) : ajoute l’URL exacte dans `CORS_ALLOWED_ORIGINS` sur Railway.

JWT en header : pas de cookie cross-site pour l’API en général ; si tu utilises des cookies session pour l’admin, renseigner aussi `CSRF_TRUSTED_ORIGINS` si besoin (non détaillé ici).

---

## 4. Checklist

- [ ] Railway : Root = `backend`, variables `SECRET_KEY`, `ALLOWED_HOSTS`, DB, secrets métier
- [ ] Railway : domaine public + port aligné sur `$PORT` / networking
- [ ] `GET /api/health/` OK sur l’URL Railway
- [ ] Vercel : Root = `frontend`, `VITE_API_BASE_URL` = `https://…railway.app/api`, `VITE_ENV=production`
- [ ] Redéploiement Vercel après toute change de `VITE_*`
- [ ] Test : login / dashboard / appels API sans erreur CORS

---

## 5. Référence projet Bachata (même principe)

- [hebergement.md (Capital_Of_Fusion V5)](https://github.com/YannickYannick/Capital_Of_Fusion_version5/blob/main/docs/explication/hebergement.md)  
- [deploiement.md (Capital_Of_Fusion V5)](https://github.com/YannickYannick/Capital_Of_Fusion_version5/blob/main/docs/explication/deploiement.md)  

Différences Trading : **WSGI** `config_django.wsgi`, **settings** `config_django.settings.production`, front **Vite** + `VITE_API_BASE_URL` au lieu de `NEXT_PUBLIC_API_URL`.

---

*Dernière mise à jour : 2026-03-28*
