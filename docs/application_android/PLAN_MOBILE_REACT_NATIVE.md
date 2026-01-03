# Plan : Application Mobile React Native

## Architecture
L'application mobile utilisera **React Native avec Expo**, réutilisera le code existant via un dossier `shared/`, et s'intégrera avec l'API Django REST Framework existante.

### Structure du projet
```
Trading_app_version4/
├── shared/                      # Code partagé (types, services)
│   ├── package.json
│   ├── tsconfig.json
│   └── src/
│       ├── types/
│       │   └── index.ts        # Types TypeScript (depuis frontend/src/types)
│       ├── services/
│       │   ├── brokers.ts      # Services API (adaptés depuis frontend/src/services)
│       │   ├── assets.ts
│       │   ├── trades.ts
│       │   ├── positions.ts
│       │   ├── orders.ts
│       │   └── strategies.ts
│       └── index.ts
├── frontend/                    # Web app (modifications minimales)
│   └── package.json            # Ajouter: "shared": "file:../shared"
└── mobile/                      # App React Native (nouveau)
    ├── package.json            # Ajouter: "shared": "file:../shared"
    ├── app.json
    ├── tsconfig.json
    ├── android/
    ├── ios/
    └── src/
        ├── api/
        │   └── client.ts       # Client HTTP (AsyncStorage au lieu de localStorage)
        ├── screens/
        ├── components/
        ├── navigation/
        ├── hooks/
        └── config/
```

### Flux d'authentification
1. LoginScreen → `authService.loginJWT()` → API `/auth/jwt/login/`
2. Stockage tokens (`SecureStore` pour mobile, `localStorage` pour web)
3. Navigation vers Dashboard
4. Intercepteur axios vérifie token sur chaque requête
5. Si 401 → refresh token automatique

## 💡 Recommandations Critiques & Architecture

### 1. Architecture Shared avec Injection de Dépendances
Pour éviter les problèmes de dépendances Web (`window`, `localStorage`) sur mobile :
- Création d'une interface `StorageInterface` dans `shared`.
- Injection de `StorageAdapter` dans les services (`AuthService`, `ApiClient`).
  - Web: `LocalStorageAdapter`
  - Mobile: `SecureStoreAdapter` (pour tokens) + `AsyncStorageAdapter`

### 2. Sécurité
- Utilisation de **`expo-secure-store`** au lieu de `AsyncStorage` pour les tokens JWT sur mobile.

### 3. Graphiques
- Utilisation de **WebView** intégrant `lightweight-charts` pour la v1 afin de garantir la parité fonctionnelle et visuelle avec le Web.

### 4. Structure de Navigation (Tabs)
On part sur une structure classique à 4 onglets pour commencer :
1. **Dashboard** (Vue d'ensemble PnL, Trades récents)
2. **Positions** (Liste positions ouvertes + Détail)
3. **Trading** (Liste actifs pour passage d'ordre rapide / Graphiques)
4. **Settings** ( Brokers, Profil, Déconnexion)

---

## Implémentation

### Phase 1 : Setup initial et structure partagée
#### 1.1 Créer la branche Git
- Créer branche `feature/mobile-app` depuis `main`
- Vérifier que le projet est à jour

#### 1.2 Créer le dossier shared
- Créer `shared/package.json` avec configuration TypeScript
- Créer `shared/tsconfig.json` pour compilation TypeScript
- Créer structure de dossiers `shared/src/types/` et `shared/src/services/`

#### 1.3 Migrer les types vers shared
- Copier `frontend/src/types/index.ts` vers `shared/src/types/index.ts`
- Copier `frontend/src/types/errors.ts` vers `shared/src/types/errors.ts`
- Créer `shared/src/index.ts` pour exports

#### 1.4 Migrer les services vers shared
- Adapter `frontend/src/services/brokers.ts` → `shared/src/services/brokers.ts`
- Remplacer `apiClient` par paramètre injecté ou factory
- Retirer dépendances spécifiques au web (localStorage, cookies)
- Faire de même pour :
  - `assets.ts`
  - `trades.ts`
  - `positions.ts`
  - `orders.ts`
  - `strategies.ts`
- `api/auth.ts` → `shared/src/services/auth.ts`

#### 1.5 Mettre à jour frontend pour utiliser shared
- Modifier `frontend/package.json` : ajouter `"shared": "file:../shared"`
- Modifier imports dans `frontend/src/services/` pour utiliser `shared/`
- Modifier imports dans `frontend/src/components/` pour utiliser types depuis `shared/`
- Tester que le frontend web fonctionne toujours

### Phase 2 : Setup React Native avec Expo
#### 2.1 Initialiser le projet Expo
- Dans `mobile/`, exécuter `npx create-expo-app@latest . --template expo-template-blank-typescript`
- Configurer `app.json` avec nom de l'app, package, etc.

#### 2.2 Installer les dépendances
- `@react-navigation/native` et `@react-navigation/native-stack`
- `@react-navigation/bottom-tabs`
- `@react-native-async-storage/async-storage`
- `axios`
- `date-fns`
- `react-native-safe-area-context`
- `react-native-screens`
- `expo-secure-store` (optionnel, pour tokens plus sécurisés)

#### 2.3 Configurer TypeScript
- Créer `mobile/tsconfig.json` avec paths vers `shared/`
- Configurer alias `@shared` pour imports

#### 2.4 Configurer le package.json mobile
- Ajouter `"shared": "file:../shared"` dans dependencies
- Configurer scripts (start, android, ios)

### Phase 3 : Client API et authentification mobile
#### 3.1 Créer le client HTTP mobile
- Créer `mobile/src/api/client.ts`
- Utiliser `AsyncStorage` au lieu de `localStorage`
- Intercepteur pour ajouter token JWT (Bearer)
- Intercepteur pour refresh token automatique (401 → refresh)
- Gestion d'erreurs adaptée au mobile

#### 3.2 Créer la configuration
- Créer `mobile/src/config/constants.ts`
- `API_BASE_URL` (dev: localhost, prod: URL serveur)
- Gérer différences Android/iOS pour localhost

#### 3.3 Adapter authService pour mobile
- Créer wrapper dans `mobile/src/services/auth.ts`
- Utiliser client API mobile au lieu de client web
- Utiliser `AsyncStorage` au lieu de `localStorage`

#### 3.4 Créer hook useAuth mobile
- Créer `mobile/src/hooks/useAuth.ts`
- Adapter depuis `frontend/src/hooks/useAuth.ts`
- Utiliser `AsyncStorage` et services mobile

### Phase 4 : Navigation et écrans de base [DONE]
#### 4.1 Créer la navigation principale [DONE]
- Créer `mobile/src/navigation/AppNavigator.tsx`
- Stack navigator : `AuthStack` et `MainStack`
- Bottom tabs pour Dashboard, Trades, Positions, Brokers, Settings

#### 4.2 Écrans d'authentification [DONE]
- `mobile/src/screens/auth/LoginScreen.tsx`
- Formulaire username/password
- Utiliser `useAuth` hook
- Navigation vers Dashboard après login
- `mobile/src/screens/auth/RegisterScreen.tsx` (optionnel)

#### 4.3 Écran Dashboard [DONE]
- `mobile/src/screens/DashboardScreen.tsx`
- Résumé positions (total PnL, nombre positions)
- Liste trades récents
- Graphiques simplifiés (ou placeholder)

### Phase 5 : Écrans principaux
#### 5.1 Écran Positions
- `mobile/src/screens/PositionsScreen.tsx`
  - Liste positions ouvertes
  - Utiliser `shared/src/services/positions.ts`
  - Affichage : symbol, size, entry price, current price, PnL
  - Pull-to-refresh
- `mobile/src/screens/PositionDetailScreen.tsx`
  - Détails d'une position
  - Historique trades liés

#### 5.2 Écran Trades
- `mobile/src/screens/TradesScreen.tsx`
  - Liste trades (utiliser `shared/src/services/trades.ts`)
  - Filtres : date, asset, side
  - Tri : date, PnL
- `mobile/src/screens/TradeDetailScreen.tsx`
  - Détails d'un trade
  - Graphique prix (simplifié ou WebView avec lightweight-charts)

#### 5.3 Écran Assets
- `mobile/src/screens/AssetsScreen.tsx`
  - Liste assets (utiliser `shared/src/services/assets.ts`)
  - Recherche par symbole
- `mobile/src/screens/AssetDetailScreen.tsx`
  - Détails asset
  - Prix actuel
  - Historique prix (graphique)

#### 5.4 Écran Brokers
- `mobile/src/screens/BrokersScreen.tsx`
  - Liste comptes broker (utiliser `shared/src/services/brokers.ts`)
  - Statut connexion
  - Balance EUR
  - Action : sync manuelle

### Phase 6 : Composants réutilisables
#### 6.1 Composants UI de base
- `mobile/src/components/common/Button.tsx`
- `mobile/src/components/common/Input.tsx`
- `mobile/src/components/common/LoadingSpinner.tsx`
- `mobile/src/components/common/ErrorMessage.tsx`
- `mobile/src/components/common/Card.tsx`

#### 6.2 Composants trading
- `mobile/src/components/trading/PositionCard.tsx`
- `mobile/src/components/trading/TradeCard.tsx`
- `mobile/src/components/trading/AssetCard.tsx`
- `mobile/src/components/trading/PnLIndicator.tsx` (vert/rouge)

### Phase 7 : Styling et UX
#### 7.1 Système de thème
- Créer `mobile/src/theme/colors.ts`
- Créer `mobile/src/theme/spacing.ts`
- Créer `mobile/src/theme/typography.ts`

#### 7.2 Styles communs
- Utiliser `StyleSheet.create()` ou styled-components
- Créer composants avec styles cohérents

#### 7.3 Gestion d'état global (optionnel)
- Si nécessaire, ajouter Context API ou Zustand
- Pour cache de données, état global utilisateur, etc.

### Phase 8 : Tests et optimisation
#### 8.1 Tests sur Android
- Tester sur émulateur Android
- Tester sur device physique Android
- Vérifier connexion API (adapter localhost si nécessaire)

#### 8.2 Tests sur iOS (optionnel)
- Si Mac disponible, tester sur simulateur iOS
- Tester sur device iOS

#### 8.3 Optimisations
- Lazy loading des écrans
- Cache des données avec `AsyncStorage`
- Gestion offline (afficher données en cache)

---

## Fichiers clés à créer/modifier

### Nouveaux fichiers
- `shared/package.json`
- `shared/tsconfig.json`
- `shared/src/types/index.ts` (copié depuis frontend)
- `shared/src/services/brokers.ts` (adapté depuis frontend)
- `shared/src/services/assets.ts`
- `shared/src/services/trades.ts`
- `shared/src/services/positions.ts`
- `shared/src/services/orders.ts`
- `shared/src/services/strategies.ts` [DONE]
- `shared/src/services/auth.ts`
- `mobile/package.json`
- `mobile/app.json`
- `mobile/tsconfig.json`
- `mobile/src/api/client.ts`
- `mobile/src/config/constants.ts`
- `mobile/src/navigation/AppNavigator.tsx`
- `mobile/src/screens/auth/LoginScreen.tsx`
- `mobile/src/screens/DashboardScreen.tsx`
- `mobile/src/screens/PositionsScreen.tsx`
- `mobile/src/screens/TradesScreen.tsx`
- `mobile/src/screens/AssetsScreen.tsx`
- `mobile/src/screens/BrokersScreen.tsx`

### Fichiers à modifier
- `frontend/package.json` (ajouter shared dependency)
- `frontend/src/services/*.ts` (adapter imports pour utiliser shared)
- `.gitignore` (ajouter node_modules de shared et mobile)

## Notes importantes
- **Localhost sur mobile** : Android/iOS ne peuvent pas accéder à `localhost:8000` depuis l'app. Solutions :
  - Utiliser l'IP locale du PC : `http://192.168.x.x:8000/api`
  - Utiliser ngrok ou similar pour développement
  - Configurer variable d'environnement pour URL API
- **AsyncStorage vs SecureStore** : Pour production, considérer `expo-secure-store` pour stocker les tokens de manière plus sécurisée.
- **Graphiques** : Pour les graphiques de trading, options :
  - `react-native-chart-kit` (simple)
  - `react-native-gifted-charts` (moderne)
  - WebView avec `lightweight-charts` existant (plus complexe mais réutilise le code web)
- **Navigation** : Utiliser React Navigation v6 (dernière version stable).
- **Testing** : Commencer avec émulateur Android, puis tester sur device réel.
