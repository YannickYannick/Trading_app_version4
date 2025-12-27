# 🔧 Guide de Dépannage - Trading App v4

## Erreur : ERR_CONNECTION_REFUSED

### Problème
```
Failed to load resource: net::ERR_CONNECTION_REFUSED
POST http://localhost:8000/api/auth/jwt/login/
```

### Solution

**Le serveur Django n'est pas démarré.**

1. Ouvrir un terminal PowerShell
2. Naviguer vers le dossier backend :
   ```powershell
   cd "C:\Users\yannb\1. Programmation\2. projet - site trading\Trading_app_version4\backend"
   ```
3. Activer l'environnement virtuel :
   ```powershell
   ..\venv\Scripts\Activate.ps1
   ```
4. Démarrer le serveur Django :
   ```powershell
   python manage.py runserver
   ```

Vous devriez voir :
```
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

---

## Erreur : 401 Unauthorized

### Problème
```
POST http://localhost:8000/api/auth/jwt/login/ 401 (Unauthorized)
```

### Solutions

#### 1. Vérifier que l'utilisateur existe

1. Accéder à http://localhost:8000/admin
2. Se connecter avec le superutilisateur
3. Vérifier dans "Users" que l'utilisateur existe

#### 2. Créer un utilisateur de test

**Via Django Admin** :
1. Aller dans "Users" → "Add user"
2. Remplir username, email, password
3. Cocher "Active" et "Staff status" si nécessaire
4. Enregistrer

**Via Django Shell** :
```powershell
cd backend
..\venv\Scripts\Activate.ps1
python manage.py shell
```

```python
from django.contrib.auth.models import User
user = User.objects.create_user('testuser', 'test@example.com', 'testpass123')
user.is_active = True
user.save()
```

#### 3. Vérifier les identifiants

Assurez-vous d'utiliser :
- **Username** : Le nom d'utilisateur (pas l'email)
- **Password** : Le mot de passe correct

#### 4. Vérifier la configuration JWT

Vérifier que `rest_framework_simplejwt` est bien installé :
```powershell
pip list | findstr simplejwt
```

Si absent, installer :
```powershell
pip install djangorestframework-simplejwt
```

---

## Erreur : CORS Error

### Problème
```
Access to XMLHttpRequest at 'http://localhost:8000/api/...' from origin 'http://localhost:3000' has been blocked by CORS policy
```

### Solution

1. Vérifier que `django-cors-headers` est installé :
   ```powershell
   pip list | findstr cors
   ```

2. Si absent, installer :
   ```powershell
   pip install django-cors-headers
   ```

3. Vérifier la configuration dans `backend/config_django/settings/base.py` :
   - `corsheaders` dans `INSTALLED_APPS`
   - `corsheaders.middleware.CorsMiddleware` en premier dans `MIDDLEWARE`
   - `CORS_ALLOWED_ORIGINS` ou `CORS_ALLOW_ALL_ORIGINS = True` en développement

---

## Erreur : Module not found

### Problème
```
ModuleNotFoundError: No module named 'django'
```

### Solution

Activer l'environnement virtuel :
```powershell
cd backend
..\venv\Scripts\Activate.ps1
```

Si le module est toujours absent :
```powershell
pip install -r requirements.txt
```

---

## Erreur : Database connection failed

### Problème
```
django.db.utils.OperationalError: could not connect to server
```

### Solution

1. Vérifier le fichier `.env` dans `backend/`
2. Vérifier les identifiants Supabase
3. Vérifier que la base de données est accessible

---

## Vérification Rapide

### Backend
```powershell
# 1. Activer l'environnement
cd backend
..\venv\Scripts\Activate.ps1

# 2. Vérifier les migrations
python manage.py showmigrations

# 3. Démarrer le serveur
python manage.py runserver
```

### Frontend
```powershell
# 1. Aller dans le dossier frontend
cd frontend

# 2. Vérifier les dépendances
npm list

# 3. Démarrer le serveur
npm run dev
```

---

## URLs de Test

- **Backend API** : http://localhost:8000/api/
- **Django Admin** : http://localhost:8000/admin/
- **API Docs** : http://localhost:8000/api/schema/swagger-ui/
- **Frontend** : http://localhost:3000/
- **Login** : http://localhost:3000/login

---

## Test de l'API avec curl

### Test de connexion JWT

```powershell
curl -X POST http://localhost:8000/api/auth/jwt/login/ `
  -H "Content-Type: application/json" `
  -d '{"username":"testuser","password":"testpass123"}'
```

### Test avec token

```powershell
curl -X GET http://localhost:8000/api/assets/ `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

