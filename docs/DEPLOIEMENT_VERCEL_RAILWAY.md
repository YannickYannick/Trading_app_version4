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

**HTTPS derrière le proxy Railway :** `production.py` définit `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` avant `SECURE_SSL_REDIRECT`. Sans cela, Django croit que la requête est en HTTP et renvoie une **301 en boucle** vers la même URL. HostArmada / Passenger envoie en général aussi `X-Forwarded-Proto` : ce réglage reste adapté aux deux hébergeurs.

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

**Nom d’utilisateur admin :** préférer un identifiant en **minuscules** (ex. `le-baff`) pour éviter les erreurs de casse à la connexion. Pour renommer un compte existant (`Le-baff` → `le-baff`) sur la base liée au service :

```powershell
# Windows (PowerShell), depuis backend/ — remplacer les IDs par ceux de ton projet Railway
$env:DJANGO_SETTINGS_MODULE='config_django.settings.production'
railway run -p <PROJECT_ID> -e <ENV_ID> -s <SERVICE_ID> -- python manage.py shell -c "from django.contrib.auth import get_user_model; U=get_user_model(); u=U.objects.get(username='Le-baff'); u.username='le-baff'; u.save(); print('OK')"
```

Vérifier avant qu’aucun autre utilisateur n’utilise déjà le nom `le-baff`.

Santé API : `GET https://<ton-backend>.up.railway.app/api/health/`

---

## 2. Frontend — Vercel

### 2.1 Projet

1. [vercel.com](https://vercel.com) → **Add New** → **Project** → importer le repo GitHub.

### 2.2 Root Directory

- **Root Directory** : `frontend`

### 2.3 Framework

- **Framework Preset** : **Vite** (ou « Other » avec les commandes ci-dessous).

### 2.3.1 Version Node (Vercel)

Dans **Settings → General → Node.js Version**, privilégier **20.x LTS** (évite npm très strict sur des versions « edge » type 24.x). Le `package.json` du front déclare `"engines": { "node": ">=20 <25" }`.

### 2.4 Build

- **Install** : `npm install`
- **Build** : `npm run build` → exécute Vite via **`node ./node_modules/vite/bin/vite.js build`** (évite l’erreur Vercel *Permission denied* sur `node_modules/.bin/vite`).
- **Output** : `dist`

Le fichier `frontend/vercel.json` définit des **rewrites** SPA (toutes les routes → `index.html`) pour React Router.

### 2.5 Indiquer l’URL du backend (variables Vercel)

C’est **l’étape qui connecte le front Vercel à l’API Railway** (ou HostArmada).

1. Dans le projet Vercel, ouvre l’onglet **Settings** (barre du haut du projet — pas seulement « Deployment Settings » sur une carte de déploiement).
2. Menu de gauche : **Environment Variables**.
3. Ajoute ou modifie :
   - **Name :** `VITE_API_BASE_URL`
   - **Value :** l’URL HTTPS du backend **avec** `/api` à la fin, ex. `https://trading-production-xxxx.up.railway.app/api`
4. Coche les environnements concernés (**Production**, et **Preview** si tu veux le même backend pour les previews).
5. **Save**, puis **Deployments** → menu **⋯** sur le dernier build → **Redeploy** (les `VITE_*` sont injectées **au moment du build** ; sans redéploiement, l’ancienne valeur reste).

### 2.6 Tableau récap des variables

Les variables **`VITE_*`** sont figées **au build** : toute modification impose un **Redeploy**.

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

## 4. Dépannage

| Symptôme | Piste |
|----------|--------|
| **301 en boucle** (navigateur ou `curl -L` : trop de redirections ; `Location` = même URL) | Vérifier `SECURE_PROXY_SSL_HEADER` dans `production.py` (déjà en place sur la branche `deploiement`) et redéployer. |
| **502 / « Application failed to respond »** | Port public Railway = port d’écoute Gunicorn (`$PORT` dans le `Procfile`) ; lire les **logs** (crash DB, import, etc.). |
| **La page “charge dans le vide” + logs Railway qui répètent** `"[WSGI] wsgi.py imported"` / `Calling get_wsgi_application()...` | Souvent un **boot Django trop long** qui fait **redémarrer Gunicorn** (timeout par défaut), ou trop de **workers** qui saturent la DB/pool. Fix appliqué : forcer `--workers 2` et `--timeout 120` dans le `Procfile`, et envoyer `--access-logfile - --error-logfile -` sur stdout pour confirmer que les requêtes atteignent bien le service. |
| **CORS** | Regex `*.vercel.app` ; ajouter `CORS_ALLOWED_ORIGINS` pour un domaine perso. |
| **Front sans données** | `VITE_API_BASE_URL` avec `/api`, **redéployer Vercel** après changement des `VITE_*`. |
| **`npm install` ERESOLVE (@testing-library/react vs React 19)** | Utiliser `@testing-library/react` **^16** + `@testing-library/dom` **^10** (déjà dans le repo) ; Node **20.x** sur Vercel. |
| **Build 126 : `Permission denied` sur `.bin/vite`** | Le script `build` appelle `node ./node_modules/vite/bin/vite.js build` (déjà dans le repo). |
| **`gunicorn: command not found`** | `python -m gunicorn …` ou vérifier `pip install -r requirements.txt` dans les build logs. |

---

## 5. Checklist

- [ ] Railway : Root = `backend`, variables `SECRET_KEY`, `ALLOWED_HOSTS`, DB, secrets métier
- [ ] Railway : domaine public + port aligné sur `$PORT` / networking
- [ ] `GET /api/health/` OK sur l’URL Railway
- [ ] Vercel : **Settings → Environment Variables** : `VITE_API_BASE_URL` = `https://…railway.app/api`, optionnel `VITE_ENV=production`
- [ ] Vercel : **Redeploy** après toute modification des `VITE_*`
- [ ] Test : login / dashboard / appels API sans erreur CORS

---

## 6. Référence projet Bachata (même principe)

- [hebergement.md (Capital_Of_Fusion V5)](https://github.com/YannickYannick/Capital_Of_Fusion_version5/blob/main/docs/explication/hebergement.md)  
- [deploiement.md (Capital_Of_Fusion V5)](https://github.com/YannickYannick/Capital_Of_Fusion_version5/blob/main/docs/explication/deploiement.md)  

Différences Trading : **WSGI** `config_django.wsgi`, **settings** `config_django.settings.production`, front **Vite** + `VITE_API_BASE_URL` au lieu de `NEXT_PUBLIC_API_URL`.

---

Documentation voisine : **`GUIDE_MODES_ENVIRONNEMENT.md`** (modes dev / prod), **`deployment_config/README.md`** (HostArmada), **`RAPPORT_DEPLOIEMENT_HOSTARMADA.md`**.

*Dernière mise à jour : 2026-04-25*
