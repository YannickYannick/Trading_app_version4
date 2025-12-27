# 🧭 Phase 4.6 : Routing Configuré

## Vue d'ensemble

Le routing a été configuré avec React Router DOM, incluant la protection des routes, la gestion de l'authentification, et une page 404 personnalisée.

## ✅ Checklist Complétée

- [x] `react-router-dom` installé
- [x] Routes configurées dans `App.tsx`
- [x] Route protégée créée (`ProtectedRoute`)
- [x] Routes pour toutes les pages principales
- [x] Route Login créée
- [x] Route 404 personnalisée
- [x] Navigation fonctionnelle (Link, NavLink, useNavigate)
- [x] Redirection après login
- [x] Déconnexion dans la Sidebar

---

## 🛡️ Route Protégée

### `routes/ProtectedRoute.tsx`

**Fonctionnalités** :
- Vérifie l'authentification avant d'afficher les routes
- Redirige vers `/login` si non authentifié
- Sauvegarde la page d'origine pour y revenir après connexion

**Exemple** :
```typescript
<Route
  path="/"
  element={
    <ProtectedRoute>
      <Layout />
    </ProtectedRoute>
  }
>
  {/* Routes protégées */}
</Route>
```

---

## 🔐 Page Login

### `pages/Login.tsx`

**Fonctionnalités** :
- Formulaire de connexion
- Authentification JWT
- Gestion d'erreurs
- Redirection vers la page d'origine après connexion
- Design moderne avec Card

**Comportement** :
1. L'utilisateur saisit ses identifiants
2. Appel à `authService.loginJWT()`
3. Les tokens sont stockés automatiquement
4. Redirection vers la page d'origine ou `/`

---

## ❌ Page 404

### `pages/NotFound.tsx`

**Fonctionnalités** :
- Page personnalisée pour les routes non trouvées
- Design cohérent avec le reste de l'application
- Boutons de navigation vers Dashboard et Positions

**Utilisation** :
```typescript
<Route path="*" element={<NotFound />} />
```

---

## 🧭 Configuration du Routing

### `App.tsx`

**Structure** :
```typescript
<Routes>
  {/* Route publique */}
  <Route path="/login" element={<Login />} />

  {/* Routes protégées */}
  <Route
    path="/"
    element={
      <ProtectedRoute>
        <Layout />
      </ProtectedRoute>
    }
  >
    <Route index element={<Dashboard />} />
    <Route path="positions" element={<Positions />} />
    <Route path="trades" element={<Trades />} />
    <Route path="assets" element={<Assets />} />
    <Route path="*" element={<NotFound />} />
  </Route>
</Routes>
```

**Routes disponibles** :
- `/` - Dashboard (route par défaut)
- `/login` - Page de connexion (publique)
- `/positions` - Liste des positions (protégée)
- `/trades` - Liste des trades (protégée)
- `/assets` - Liste des assets (protégée)
- `/*` - Page 404 (protégée)

**Routes à venir** :
- `/positions/:id` - Détail d'une position
- `/trades/:id` - Détail d'un trade
- `/assets/:id` - Détail d'un asset
- `/brokers` - Gestion des brokers
- `/settings` - Paramètres

---

## 🧭 Navigation

### Utilisation de `Link`

```typescript
import { Link } from 'react-router-dom'

<Link to="/positions">Voir les positions</Link>
```

### Utilisation de `NavLink` (avec style actif)

```typescript
import { NavLink } from 'react-router-dom'

<NavLink
  to="/positions"
  className={({ isActive }) => (isActive ? 'active' : '')}
>
  Positions
</NavLink>
```

**Dans Sidebar** :
- Utilisation de `NavLink` pour les items de menu
- Style actif automatique
- `end={true}` pour la route `/` (match exact)

### Utilisation de `useNavigate`

```typescript
import { useNavigate } from 'react-router-dom'

const navigate = useNavigate()

// Navigation simple
navigate('/positions')

// Navigation avec remplacement
navigate('/positions', { replace: true })

// Navigation avec état
navigate('/positions', {
  state: { message: 'Position créée' }
})
```

### Utilisation de `useParams`

```typescript
import { useParams } from 'react-router-dom'

// Pour les routes avec paramètres : /positions/:id
const { id } = useParams<{ id: string }>()
```

### Utilisation de `useSearchParams`

```typescript
import { useSearchParams } from 'react-router-dom'

const [searchParams, setSearchParams] = useSearchParams()
const status = searchParams.get('status') || 'OPEN'

// Modifier les query params
setSearchParams({ status: 'CLOSED' })
```

---

## 🔄 Redirection après Login

**Fonctionnement** :
1. L'utilisateur tente d'accéder à une route protégée
2. `ProtectedRoute` détecte qu'il n'est pas authentifié
3. Redirection vers `/login` avec `state.from` contenant la page d'origine
4. Après connexion réussie, redirection vers la page d'origine

**Code** :
```typescript
// Dans ProtectedRoute
if (!isAuthenticated) {
  return <Navigate to="/login" state={{ from: location }} replace />
}

// Dans Login
const from = (location.state as any)?.from?.pathname || '/'
navigate(from, { replace: true })
```

---

## 🚪 Déconnexion

**Dans Sidebar** :
- Bouton de déconnexion dans le footer
- Appel à `authService.logout()`
- Redirection vers `/login`
- Gestion d'erreurs

**Code** :
```typescript
const handleLogout = async () => {
  try {
    await authService.logout()
    navigate('/login')
  } catch (error) {
    console.error('Erreur lors de la déconnexion:', error)
    navigate('/login')
  }
}
```

---

## 📝 Exemples d'Utilisation

### Navigation programmatique

```typescript
import { useNavigate } from 'react-router-dom'

function MyComponent() {
  const navigate = useNavigate()

  const handleCreatePosition = async () => {
    const position = await createPosition()
    navigate(`/positions/${position.id}`)
  }

  return <button onClick={handleCreatePosition}>Créer</button>
}
```

### Navigation avec état

```typescript
navigate('/positions', {
  state: {
    message: 'Position créée avec succès',
    positionId: 123,
  }
})
```

### Récupérer l'état

```typescript
import { useLocation } from 'react-router-dom'

const location = useLocation()
const { message, positionId } = location.state || {}
```

---

## ✅ Prochaines Étapes

1. **Pages de détail** : Créer PositionDetailPage, TradeDetailPage, AssetDetailPage
2. **Routes avec paramètres** : Ajouter `/positions/:id`, `/trades/:id`, `/assets/:id`
3. **Page Brokers** : Créer BrokersPage et route `/brokers`
4. **Page Settings** : Créer SettingsPage et route `/settings`
5. **Lazy loading** : Implémenter le lazy loading pour optimiser les performances

---

## 📚 Ressources

- **React Router DOM** : https://reactrouter.com/
- **Routes** : `src/routes/ProtectedRoute.tsx`
- **Pages** : `src/pages/Login.tsx`, `src/pages/NotFound.tsx`
- **App** : `src/App.tsx`

