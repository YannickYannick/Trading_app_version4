# 🔐 Authentification API

## Vue d'ensemble

L'API supporte deux types d'authentification :
1. **Session** : Pour les navigateurs (cookies)
2. **JWT** : Pour les apps mobiles/API

## Configuration

### settings/base.py

```python
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

## Endpoints d'authentification

### Session Authentication (Navigateur)

```python
# apps/trading/api/auth_views.py

@api_view(['POST'])
@permission_classes([AllowAny])
def login_session(request):
    """POST /api/auth/login/"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(request, username=username, password=password)
    if user:
        login(request, user)
        return Response({
            'status': 'success',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            }
        })
    return Response({'error': 'Invalid credentials'}, status=401)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_session(request):
    """POST /api/auth/logout/"""
    logout(request)
    return Response({'status': 'success'})
```

### JWT Authentication (Apps/API)

```python
@api_view(['POST'])
@permission_classes([AllowAny])
def login_jwt(request):
    """POST /api/auth/jwt/login/"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(request, username=username, password=password)
    if user:
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
            }
        })
    return Response({'error': 'Invalid credentials'}, status=401)
```

### Inscription

```python
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """POST /api/auth/register/"""
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    password2 = request.data.get('password2')
    
    if password != password2:
        return Response({'error': 'Passwords do not match'}, status=400)
    
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=400)
    
    user = User.objects.create_user(username=username, email=email, password=password)
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'status': 'success',
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {'id': user.id, 'username': user.username}
    }, status=201)
```

## Utilisation

### Session (Navigateur)

```javascript
// Login
const response = await fetch('/api/auth/login/', {
  method: 'POST',
  credentials: 'include',  // Envoie les cookies
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username, password })
});

// Appels API (le cookie de session est envoyé automatiquement)
const assets = await fetch('/api/assets/', {
  credentials: 'include'
});
```

### JWT (Apps)

```javascript
// Login
const { access, refresh } = await fetch('/api/auth/jwt/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username, password })
}).then(r => r.json());

// Stocker les tokens
localStorage.setItem('access_token', access);
localStorage.setItem('refresh_token', refresh);

// Appels API avec token
const assets = await fetch('/api/assets/', {
  headers: { 'Authorization': `Bearer ${access}` }
});

// Refresh le token quand il expire
const newAccess = await fetch('/api/auth/jwt/refresh/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ refresh })
}).then(r => r.json());
```

## Frontend React (Axios)

```typescript
// services/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
});

// Intercepteur pour ajouter le token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Intercepteur pour refresh automatique
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const refresh = localStorage.getItem('refresh_token');
      if (refresh) {
        const response = await axios.post('/api/auth/jwt/refresh/', { refresh });
        localStorage.setItem('access_token', response.data.access);
        error.config.headers.Authorization = `Bearer ${response.data.access}`;
        return axios.request(error.config);
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

## Endpoints

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/auth/login/` | POST | Login session |
| `/api/auth/logout/` | POST | Logout session |
| `/api/auth/jwt/login/` | POST | Login JWT |
| `/api/auth/jwt/logout/` | POST | Logout JWT (blacklist) |
| `/api/auth/jwt/refresh/` | POST | Refresh token |
| `/api/auth/jwt/verify/` | POST | Vérifier token |
| `/api/auth/user/` | GET | Info utilisateur |
| `/api/auth/register/` | POST | Inscription |

## Comparaison

| Méthode | Utilisation | Avantages | Inconvénients |
|---------|-------------|-----------|---------------|
| Session | Navigateur | Simple, sécurisé | Pas pour mobile |
| JWT | Apps/API | Flexible, mobile | Plus complexe |

