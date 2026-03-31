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

## 3. Test de l'authentification

### Créer un utilisateur de test

1. Accéder à http://localhost:8000/admin
2. Se connecter avec le superutilisateur
3. Créer un utilisateur dans "Users"

### Se connecter depuis le frontend

1. Accéder à http://localhost:3000/login
2. Utiliser les identifiants créés
3. L'authentification JWT devrait fonctionner

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

## ✅ Checklist de Démarrage

- [ ] Backend Django démarré sur le port 8000
- [ ] Frontend React démarré sur le port 3000
- [ ] Base de données PostgreSQL connectée
- [ ] Migrations appliquées
- [ ] Superutilisateur créé
- [ ] Utilisateur de test créé
- [ ] Fichier `.env` configuré dans `frontend/`
- [ ] Authentification fonctionnelle

