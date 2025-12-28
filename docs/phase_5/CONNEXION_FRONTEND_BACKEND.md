# 🔌 Connexion Frontend ↔ Backend Testée

Ce guide explique comment tester et valider la connexion entre le frontend React/TypeScript et le backend Django REST Framework.

---

## 📋 Vue d'ensemble

La connexion frontend ↔ backend se fait via :
- **API REST** : Endpoints Django REST Framework
- **Authentification** : JWT ou Session Authentication
- **CORS** : Configuration pour permettre les requêtes cross-origin
- **Services API** : Fonctions TypeScript pour appeler l'API

---

## 🔧 Configuration de Base

### 1. Configuration CORS (Backend)

**Fichier** : `backend/config_django/settings/base.py`

```python
# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Frontend React en développement
    "http://localhost:5173",  # Vite dev server
    "https://votre-domaine.com",  # Production
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

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
```

### 2. Configuration API Client (Frontend)

**Fichier** : `frontend/src/services/api.ts`

```typescript
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

// Créer une instance axios avec configuration par défaut
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Pour les cookies de session
});

// Intercepteur pour ajouter le token JWT
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Intercepteur pour gérer les erreurs
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Token expiré, essayer de le rafraîchir
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/jwt/refresh/`, {
            refresh: refreshToken,
          });
          localStorage.setItem('access_token', response.data.access);
          // Réessayer la requête originale
          error.config.headers.Authorization = `Bearer ${response.data.access}`;
          return apiClient.request(error.config);
        } catch (refreshError) {
          // Refresh échoué, rediriger vers login
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);
```

---

## 🧪 Tests de Connexion

### Test 1 : Vérifier que le Backend est Accessible

**Frontend** : `frontend/src/services/api.ts`

```typescript
export const testBackendConnection = async (): Promise<boolean> => {
  try {
    const response = await apiClient.get('/auth/user/');
    return response.status === 200;
  } catch (error) {
    console.error('Backend connection failed:', error);
    return false;
  }
};
```

**Utilisation** :
```typescript
// Dans un composant ou au démarrage de l'app
const isConnected = await testBackendConnection();
if (!isConnected) {
  console.error('Cannot connect to backend');
}
```

### Test 2 : Tester l'Authentification

**Frontend** : `frontend/src/services/auth.ts`

```typescript
export const login = async (username: string, password: string) => {
  try {
    const response = await apiClient.post('/auth/jwt/login/', {
      username,
      password,
    });
    
    if (response.data.access) {
      localStorage.setItem('access_token', response.data.access);
      localStorage.setItem('refresh_token', response.data.refresh);
      return { success: true, user: response.data.user };
    }
    
    return { success: false, error: 'No token received' };
  } catch (error: any) {
    return {
      success: false,
      error: error.response?.data?.detail || 'Login failed',
    };
  }
};

export const logout = async () => {
  try {
    await apiClient.post('/auth/jwt/logout/');
  } catch (error) {
    console.error('Logout error:', error);
  } finally {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }
};
```

### Test 3 : Tester un Endpoint CRUD

**Frontend** : `frontend/src/services/brokers.ts`

```typescript
export const getBrokerAccounts = async () => {
  try {
    const response = await apiClient.get('/broker-accounts/');
    return {
      success: true,
      data: response.data.results || response.data,
    };
  } catch (error: any) {
    return {
      success: false,
      error: error.response?.data?.detail || 'Failed to fetch broker accounts',
    };
  }
};

export const createBrokerAccount = async (data: any) => {
  try {
    const response = await apiClient.post('/broker-accounts/', data);
    return {
      success: true,
      data: response.data,
    };
  } catch (error: any) {
    return {
      success: false,
      error: error.response?.data || 'Failed to create broker account',
    };
  }
};
```

---

## 🔍 Vérifications à Effectuer

### 1. Vérifier CORS

**Test manuel** :
```bash
# Dans la console du navigateur (F12)
fetch('http://localhost:8000/api/auth/user/', {
  credentials: 'include',
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN'
  }
})
.then(r => r.json())
.then(console.log)
.catch(console.error);
```

**Erreurs courantes** :
- `CORS policy: No 'Access-Control-Allow-Origin' header` → Vérifier la configuration CORS
- `CORS policy: Credentials flag is true` → Ajouter `CORS_ALLOW_CREDENTIALS = True`

### 2. Vérifier l'Authentification

**Test** :
```typescript
// Tester la connexion avec token
const testAuth = async () => {
  const token = localStorage.getItem('access_token');
  if (!token) {
    console.error('No token found');
    return;
  }
  
  try {
    const response = await apiClient.get('/auth/user/');
    console.log('User info:', response.data);
  } catch (error) {
    console.error('Auth failed:', error);
  }
};
```

### 3. Vérifier les Erreurs HTTP

**Test** :
```typescript
// Tester différentes erreurs
const testErrors = async () => {
  // 404
  try {
    await apiClient.get('/nonexistent/');
  } catch (error: any) {
    console.log('404 error:', error.response?.status);
  }
  
  // 401
  try {
    await apiClient.get('/broker-accounts/', {
      headers: { Authorization: 'Bearer invalid_token' }
    });
  } catch (error: any) {
    console.log('401 error:', error.response?.status);
  }
  
  // 400
  try {
    await apiClient.post('/broker-accounts/', { invalid: 'data' });
  } catch (error: any) {
    console.log('400 error:', error.response?.status, error.response?.data);
  }
};
```

---

## 📊 Tests Automatisés

### Test avec Jest/Vitest

**Fichier** : `frontend/src/services/__tests__/api.test.ts`

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { apiClient } from '../api';
import { testBackendConnection, login } from '../auth';

describe('API Connection', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should connect to backend', async () => {
    const connected = await testBackendConnection();
    expect(connected).toBe(true);
  });

  it('should handle authentication', async () => {
    const result = await login('testuser', 'testpass');
    expect(result.success).toBe(true);
    expect(localStorage.getItem('access_token')).toBeTruthy();
  });

  it('should handle authentication errors', async () => {
    const result = await login('invalid', 'invalid');
    expect(result.success).toBe(false);
    expect(result.error).toBeTruthy();
  });
});
```

---

## ✅ Checklist de Validation

### Configuration

- [ ] CORS configuré correctement dans `settings.py`
- [ ] `apiClient` configuré avec la bonne URL de base
- [ ] Intercepteurs axios configurés (token, erreurs)
- [ ] Variables d'environnement configurées (`.env`)

### Tests de Base

- [ ] Backend accessible depuis le frontend
- [ ] Authentification fonctionne (login/logout)
- [ ] Token JWT stocké et utilisé correctement
- [ ] Refresh token fonctionne automatiquement

### Tests CRUD

- [ ] GET fonctionne (liste des ressources)
- [ ] POST fonctionne (création)
- [ ] PUT/PATCH fonctionne (mise à jour)
- [ ] DELETE fonctionne (suppression)

### Gestion d'Erreurs

- [ ] Erreurs 400 (Bad Request) gérées
- [ ] Erreurs 401 (Unauthorized) gérées
- [ ] Erreurs 404 (Not Found) gérées
- [ ] Erreurs 500 (Server Error) gérées
- [ ] Messages d'erreur affichés à l'utilisateur

### Performance

- [ ] Requêtes optimisées (pas de requêtes inutiles)
- [ ] Cache utilisé quand approprié
- [ ] Loading states affichés pendant les requêtes
- [ ] Timeout configuré pour les requêtes longues

---

## 🐛 Dépannage

### Problème : CORS Error

**Solution** :
1. Vérifier `CORS_ALLOWED_ORIGINS` dans `settings.py`
2. Vérifier que l'URL du frontend correspond
3. Redémarrer le serveur Django

### Problème : 401 Unauthorized

**Solution** :
1. Vérifier que le token est présent dans `localStorage`
2. Vérifier que le token n'est pas expiré
3. Vérifier le format du header Authorization

### Problème : Network Error

**Solution** :
1. Vérifier que le backend est démarré
2. Vérifier l'URL dans `VITE_API_BASE_URL`
3. Vérifier les logs du backend

---

## 📚 Ressources

- **Django CORS Headers** : https://github.com/adamchainz/django-cors-headers
- **Axios Documentation** : https://axios-http.com/
- **JWT Authentication** : `docs/phase_2/AUTHENTICATION_API_EXPLANATION.md`

---

## 🎯 Résultat Attendu

Après validation :
- ✅ Le frontend peut communiquer avec le backend
- ✅ L'authentification fonctionne
- ✅ Les opérations CRUD fonctionnent
- ✅ Les erreurs sont gérées correctement
- ✅ Les utilisateurs voient des messages clairs

