# 🚀 Guide de Démarrage - Trading App v4

> Emplacement : `docs/guides/README_DEMARRAGE.md` (lien depuis la racine : voir le [README principal](../../README.md)).

## Prérequis

- Python 3.10+
- Node.js 18+
- PostgreSQL (Supabase)

## 1. Backend Django

### Activer l'environnement virtuel

```powershell
cd backend
..\venv\Scripts\Activate.ps1
```

### Installer les dépendances (si nécessaire)

```powershell
pip install -r requirements.txt
```

### Configurer la base de données

Assurez-vous que le fichier `.env` dans `backend/` contient :

```env
DB_HOST=aws-1-eu-west-1.pooler.supabase.com
DB_PORT=6543
DB_NAME=postgres
DB_USER=postgres.lowncckbivxmiakzmsxq
DB_PASSWORD=votre_mot_de_passe
SECRET_KEY=votre_secret_key
DEBUG=True
```

### Appliquer les migrations

```powershell
python manage.py migrate
```

### Créer un superutilisateur (si nécessaire)

```powershell
python manage.py createsuperuser
```

### Démarrer le serveur Django

```powershell
python manage.py runserver
```

Le serveur sera accessible sur : **http://localhost:8000**

---

## 2. Frontend React

### Installer les dépendances (si nécessaire)

```powershell
cd frontend
npm install
```

### Configurer les variables d'environnement

Créer un fichier `.env` dans `frontend/` :

```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_ENV=development
```

### Démarrer le serveur de développement

```powershell
npm run dev
```

Le frontend sera accessible sur : **http://localhost:3000**

---

## 3. Application mobile (Expo / React Native)

L’app dans `mobile/` est **opérationnelle** : authentification JWT, dashboard, données brokers (ex. Binance, Saxo) et navigation, en s’appuyant sur la même API que le web (`/api`).

### Prérequis

- Backend Django démarré sur le port **8000** (voir section 1).
- Compte utilisateur valide sur la base utilisée par le backend (Supabase ou autre).

### Installer et lancer

```powershell
cd mobile
npm install
npm start
```

Puis ouvrir avec **Expo Go** (QR code) ou l’émulateur Android / iOS.

### URL de l’API en développement

Le fichier `mobile/src/config/constants.ts` résout automatiquement la base URL :

| Contexte | Comportement |
|----------|----------------|
| **Émulateur Android** | Hôte API par défaut **`10.0.2.2`** (alias vers la machine hôte). Un `python manage.py runserver` classique sur le PC suffit. Surcharge possible : `EXPO_PUBLIC_ANDROID_EMU_HOST`. |
| **Téléphone Android (réseau Wi‑Fi)** | IP LAN du PC (`DEV_API_HOST_LAN`, à ajuster avec `ipconfig`). Lancer **`python manage.py runserver 0.0.0.0:8000`** pour que le port 8000 soit joignable sur le LAN ; vérifier le pare-feu Windows si besoin. |
| **Simulateur iOS** | `http://127.0.0.1:8000/api` |
| **Forcer la prod en dev** | `EXPO_PUBLIC_USE_PROD_API_IN_DEV=1` |

URL complète de prod utilisée en build release : voir `PROD_API_URL` dans `constants.ts`.

### Dépannage mobile

- **`AxiosError: Network Error` au login** : backend arrêté, mauvaise IP, ou Django qui n’écoute pas sur toutes les interfaces (`0.0.0.0`) quand on utilise l’IP LAN. Vérifier les logs Metro (`[API] DEV base URL → …`).

---

## 4. Test de l'authentification

### Créer un utilisateur de test

1. Accéder à http://localhost:8000/admin
2. Se connecter avec le superutilisateur
3. Créer un utilisateur dans "Users"

### Se connecter depuis le frontend web

1. Accéder à http://localhost:3000/login
2. Utiliser les identifiants créés
3. L'authentification JWT devrait fonctionner

### Se connecter depuis l’app mobile

1. Démarrer le backend et l’app Expo (`npm start` dans `mobile/`).
2. S’assurer que l’URL d’API affichée dans la console correspond à votre contexte (émulateur / appareil réel).
3. S’identifier avec le même couple username / mot de passe que sur l’API.

---

## 🔧 Dépannage

### ERR_CONNECTION_REFUSED

**Problème** : Le serveur Django n'est pas démarré.

**Solution** :
```powershell
cd backend
..\venv\Scripts\Activate.ps1
python manage.py runserver
```

### 401 Unauthorized

**Problème** : Identifiants incorrects ou utilisateur inexistant.

**Solution** :
1. Vérifier que l'utilisateur existe dans Django Admin
2. Vérifier les identifiants
3. Créer un nouvel utilisateur si nécessaire

### CORS Error

**Problème** : CORS non configuré correctement.

**Solution** : Vérifier que `django-cors-headers` est installé et configuré dans `settings/base.py`

---

## 📝 Commandes Utiles

### Backend

```powershell
# Activer l'environnement virtuel
..\venv\Scripts\Activate.ps1

# Migrations
python manage.py makemigrations
python manage.py migrate

# Créer un superutilisateur
python manage.py createsuperuser

# Démarrer le serveur
python manage.py runserver

# Shell Django
python manage.py shell
```

### Frontend

```powershell
# Installer les dépendances
npm install

# Démarrer le serveur de développement
npm run dev

# Build pour production
npm run build

# Preview du build
npm run preview
```

---

## 🌐 URLs Importantes

- **Frontend** : http://localhost:3000
- **Backend API** : http://localhost:8000/api
- **Django Admin** : http://localhost:8000/admin
- **API Documentation** : http://localhost:8000/api/schema/swagger-ui/

---

## 🔧 Scripts manuels (diagnostic / smoke tests)

Les scripts ponctuels (`test_*.py`, `check_*.py`, `quick_check.py`, `debug_env.py`) sont regroupés dans **`backend/scripts/manual_checks/`**. Ils fixent eux-mêmes le répertoire de travail sur `backend/`.

Exemples (à lancer depuis n’importe quel dossier, en adaptant le chemin vers `backend/`) :

```powershell
cd backend
python scripts/manual_checks/check_api.py
python scripts/manual_checks/quick_check.py
```

Les **tests unitaires Django** restent sous `backend/apps/trading/tests/` (`python manage.py test` ou `pytest` avec `backend/pytest.ini`).

---

## ✅ Checklist de Démarrage

- [ ] Backend Django démarré sur le port 8000
- [ ] Frontend React démarré sur le port 3000
- [ ] (Optionnel) App mobile Expo : `npm start` dans `mobile/`, URL API correcte (émulateur / LAN)
- [ ] Base de données PostgreSQL connectée
- [ ] Migrations appliquées
- [ ] Superutilisateur créé
- [ ] Utilisateur de test créé
- [ ] Fichier `.env` configuré dans `frontend/`
- [ ] Authentification fonctionnelle (web et/ou mobile)

