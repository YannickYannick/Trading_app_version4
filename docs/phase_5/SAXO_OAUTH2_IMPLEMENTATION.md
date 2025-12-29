# 🔐 Implémentation OAuth2 Saxo Bank et Affichage du Solde

## 📋 Vue d'ensemble

Cette documentation décrit l'implémentation complète de l'authentification OAuth2 avec Saxo Bank et l'affichage du solde EUR dans l'application.

**Date d'implémentation** : 27 décembre 2024

---

## 🎯 Fonctionnalités Implémentées

- ✅ Authentification OAuth2 complète avec Saxo Bank
- ✅ Obtention de l'URL d'authentification
- ✅ Échange du code d'autorisation contre des tokens
- ✅ Rafraîchissement automatique des tokens
- ✅ Affichage du solde EUR pour les comptes Saxo
- ✅ Normalisation automatique du redirect_uri
- ✅ Interface utilisateur pour gérer l'OAuth2
- ✅ Gestion des erreurs et logging amélioré

---

## 🔧 Architecture

### Backend (Django)

#### 1. Modèle `BrokerAccount`

**Fichier** : `backend/apps/trading/models/brokers.py`

**Champs Saxo** :
- `saxo_client_id` : ID client OAuth2
- `saxo_client_secret` : Secret client OAuth2
- `saxo_redirect_uri` : URI de redirection (normalisée automatiquement)
- `saxo_access_token` : Token d'accès
- `saxo_refresh_token` : Token de rafraîchissement
- `saxo_token_expires_at` : Date d'expiration du token
- `saxo_environment` : Environnement (live/simulation)

**Méthode `get_credentials_dict()`** :
```python
def get_credentials_dict(self) -> dict:
    """Retourne les credentials sous forme de dictionnaire."""
    if broker_type == 'SAXO':
        return {
            'client_id': self.saxo_client_id,
            'client_secret': self.saxo_client_secret,
            'redirect_uri': self.saxo_redirect_uri,
            'access_token': self.saxo_access_token,
            'refresh_token': self.saxo_refresh_token,
            'token_expires_at': self.saxo_token_expires_at,
            'environment': self.environment,
        }
```

#### 2. Broker `SaxoBroker`

**Fichier** : `backend/apps/trading/brokers/saxo.py`

**Méthodes principales** :

##### `get_authorization_url(state: str = None) -> str`
Génère l'URL d'authentification OAuth2 avec normalisation automatique du `redirect_uri`.

**Normalisation du redirect_uri** :
- Conversion du domaine en minuscules (Saxo est sensible à la casse)
- Préservation du schéma (http/https) et du chemin

##### `exchange_code_for_token(code: str) -> Dict[str, Any]`
Échange le code d'autorisation OAuth2 contre des tokens (access_token, refresh_token).

##### `refresh_authentication() -> bool`
Implémente l'interface abstraite `BrokerBase` pour rafraîchir l'authentification.

##### `get_account_info() -> Dict[str, Any]`
Récupère les informations du compte depuis l'API Saxo :
1. Appelle `/port/v1/accounts` pour obtenir `AccountKey` et `ClientKey`
2. Utilise ces deux paramètres pour appeler `/port/v1/balances`
3. Retourne les informations formatées

**Format de retour** :
```python
{
    'account_id': '20376954',
    'account_key': 'yFb5EAMRwy0HDb7xaHVR9A==',
    'currency': 'EUR',
    'balance': 1500.00,  # TotalValue
    'cash_balance': 1250.75,  # CashBalance
    'margin_available': 500.00,
    'margin_used': 250.00,
    'unrealized_pnl': 50.00,
    'account_type': 'Normal',
    'is_active': True,
}
```

##### `get_account_balance() -> Dict[str, Decimal]`
Formate les balances pour retourner un dictionnaire simple :
```python
{
    'EUR': Decimal('1250.75'),
    'EUR_total': Decimal('1500.00'),
    'EUR_margin_available': Decimal('500.00')
}
```

#### 3. Endpoints API REST

**Fichier** : `backend/apps/trading/api/views.py`

##### `GET /api/broker-accounts/{id}/saxo-auth-url/`
Obtient l'URL d'authentification OAuth2.

**Réponse** :
```json
{
  "success": true,
  "auth_url": "https://live.logonvalidation.net/authorize?response_type=code&client_id=...&redirect_uri=https%3A%2F%2Fle-baff.com&state=...",
  "state": "l6yVvt4fwAU-jC_aK-95Zm6FGBoDC2qmnTnzZMbLbFQ"
}
```

##### `POST /api/broker-accounts/{id}/saxo-exchange-code/`
Échange le code d'autorisation contre des tokens.

**Body** :
```json
{
  "code": "438323e9-82a2-4568-ae06-6801378b4427",
  "state": "abc123"
}
```

**Réponse** :
```json
{
  "success": true,
  "message": "Tokens obtenus avec succès",
  "token_expires_at": "2024-12-27T19:00:00Z",
  "account": { ... }
}
```

##### `POST /api/broker-accounts/{id}/saxo-refresh-token/`
Rafraîchit le token d'accès.

##### `GET /api/broker-accounts/{id}/balance-eur/`
Récupère le solde EUR actuel (fonctionne pour Saxo et Binance).

**Réponse** :
```json
{
  "success": true,
  "balance_eur": 1250.75,
  "currency": "EUR",
  "all_balances": {
    "EUR": 1250.75
  },
  "timestamp": "2024-12-27T18:36:15Z"
}
```

---

### Frontend (React/TypeScript)

#### 1. Composant `SaxoOAuthModal`

**Fichier** : `frontend/src/components/brokers/SaxoOAuthModal.tsx`

**Fonctionnalités** :
- Étape 1 : Obtenir l'URL d'authentification
- Étape 2 : Échanger le code contre des tokens
- Affichage du statut des tokens existants
- Gestion des erreurs

**Utilisation** :
```typescript
<SaxoOAuthModal
  account={selectedAccount}
  onSuccess={() => refetch()}
  onClose={() => setIsModalOpen(false)}
/>
```

#### 2. Composant `BrokerForm`

**Fichier** : `frontend/src/components/brokers/BrokerForm.tsx`

**Améliorations** :
- Section dédiée pour les tokens OAuth2 avec badge de statut
- Champs pour Access Token et Refresh Token (saisie manuelle)
- Indicateur visuel si les tokens sont présents
- Hint pour utiliser le bouton OAuth2

#### 3. Page `Brokers`

**Fichier** : `frontend/src/pages/Brokers.tsx`

**Fonctionnalités** :
- Bouton "🔐 OAuth2" pour chaque compte Saxo
- Affichage du solde EUR via `BrokerBalance` (compatible Saxo et Binance)
- Modal OAuth2 intégré

#### 4. Service API

**Fichier** : `frontend/src/services/brokers.ts`

**Nouvelles méthodes** :
- `getSaxoAuthUrl(accountId)` : Obtient l'URL d'authentification
- `exchangeSaxoAuthCode(accountId, code, state)` : Échange le code
- `refreshSaxoToken(accountId)` : Rafraîchit le token
- `getBalanceEur(accountId)` : Récupère le solde EUR (Saxo et Binance)

---

## 🔍 Corrections Techniques

### 1. Logger manquant dans les endpoints OAuth2

**Problème** : `NameError: name 'logger' is not defined`

**Solution** : Ajout de l'import et de la définition du logger dans :
- `saxo_auth_url()`
- `saxo_exchange_code()`
- `saxo_refresh_token()`

### 2. Méthode abstraite `refresh_authentication()` manquante

**Problème** : `TypeError: Can't instantiate abstract class SaxoBroker without an implementation for abstract method 'refresh_authentication'`

**Solution** : Ajout de la méthode `refresh_authentication()` qui appelle `_refresh_token()`.

### 3. Normalisation du redirect_uri

**Problème** : `redirect_uri` avec majuscules (`http://Le-baff.com`) causait des erreurs.

**Solution** : Normalisation automatique en minuscules pour le domaine dans `SaxoBroker.__init__()`.

### 4. Paramètres manquants pour `/port/v1/balances`

**Problème** : `NoValidInput` ou `ClientKey field is required`

**Solution** :
1. Récupération d'abord de `/port/v1/accounts` pour obtenir `AccountKey` et `ClientKey`
2. Utilisation des deux paramètres pour `/port/v1/balances`
3. Gestion des différents formats de réponse (liste, dict avec 'Data', etc.)

---

## 📝 Flux OAuth2 Complet

```
1. Utilisateur clique sur "🔐 OAuth2"
   ↓
2. Frontend appelle GET /api/broker-accounts/{id}/saxo-auth-url/
   ↓
3. Backend génère l'URL avec state (CSRF protection)
   ↓
4. Utilisateur est redirigé vers Saxo Bank
   ↓
5. Utilisateur se connecte et autorise l'application
   ↓
6. Saxo redirige vers https://le-baff.com/?code=...&state=...
   ↓
7. Utilisateur copie le code et le colle dans le modal
   ↓
8. Frontend appelle POST /api/broker-accounts/{id}/saxo-exchange-code/
   ↓
9. Backend échange le code contre des tokens
   ↓
10. Tokens sont sauvegardés dans BrokerAccount
   ↓
11. Le solde peut maintenant être récupéré
```

---

## 💶 Flux de Récupération du Solde

```
1. Frontend appelle GET /api/broker-accounts/{id}/balance-eur/
   ↓
2. BrokerService.get_account_balance(account)
   ↓
3. SaxoBroker.authenticate() (vérifie/rafraîchit le token)
   ↓
4. SaxoBroker.get_account_balance()
   ↓
5. SaxoBroker.get_account_info()
   ↓
6. GET /port/v1/accounts → AccountKey, ClientKey
   ↓
7. GET /port/v1/balances?AccountKey=...&ClientKey=... → Balances
   ↓
8. Formatage et retour au frontend
   ↓
9. Affichage du solde EUR
```

---

## ⚠️ Points Importants

### Redirect URI

- **Doit correspondre exactement** entre :
  - Le portail développeur Saxo
  - La base de données Django
- **Format requis** : `https://le-baff.com` (HTTPS, minuscules, sans slash final)
- **Normalisation automatique** : Le code normalise automatiquement en minuscules

### Tokens

- **Access Token** : Expire après 1 heure
- **Refresh Token** : Utilisé pour obtenir un nouveau access token
- **Rafraîchissement automatique** : Le système rafraîchit automatiquement si nécessaire

### AccountKey et ClientKey

- **AccountKey** : Obtenu depuis `/port/v1/accounts`
- **ClientKey** : Obtenu depuis `/port/v1/accounts` (champ `ClientKey` de chaque compte)
- **Les deux sont requis** pour `/port/v1/balances`

---

## 🐛 Dépannage

### Erreur : "Value of redirect_uri parameter is not registered"

**Cause** : Le `redirect_uri` ne correspond pas exactement à celui enregistré dans Saxo.

**Solution** :
1. Vérifier dans le portail développeur Saxo que le `redirect_uri` est exactement `https://le-baff.com`
2. Vérifier dans la base de données que `saxo_redirect_uri` est `https://le-baff.com`
3. La normalisation automatique devrait corriger les problèmes de casse

### Erreur : "ClientKey field is required"

**Cause** : Le `ClientKey` n'est pas passé dans les paramètres de `/port/v1/balances`.

**Solution** : Le code récupère maintenant automatiquement le `ClientKey` depuis `/port/v1/accounts`.

### Erreur : "NoValidInput"

**Cause** : Paramètres manquants ou invalides pour l'API Saxo.

**Solution** : Vérifier que `AccountKey` et `ClientKey` sont tous les deux présents.

### Le solde ne s'affiche pas

**Causes possibles** :
1. Tokens expirés ou invalides
2. Authentification échouée
3. Compte sans solde

**Solutions** :
1. Vérifier les tokens via le bouton "🔑 Creds"
2. Tester la connexion via le bouton "Tester"
3. Vérifier les logs Django pour plus de détails

---

## 📚 Ressources

- **Documentation Saxo OpenAPI** : https://www.developer.saxo/openapi/learn
- **Portail Développeur Saxo** :
  - Simulation : https://www.developer.saxo/openapi/sim
  - Live : https://www.developer.saxo/openapi/trade
- **Guide OAuth2** : `docs/SAXO_OAUTH2_AND_BALANCE.md`
- **Guide Affichage Solde** : `docs/SAXO_BALANCE_DISPLAY.md`
- **Fichiers de Connexion** : `docs/SAXO_CONNECTION_FILES.md`

---

## ✅ Checklist d'Implémentation

### Backend
- [x] Méthode `refresh_authentication()` ajoutée à `SaxoBroker`
- [x] Normalisation du `redirect_uri` dans `SaxoBroker.__init__()`
- [x] Correction de `get_account_info()` pour utiliser `AccountKey` et `ClientKey`
- [x] Logger ajouté dans tous les endpoints OAuth2
- [x] Endpoints API créés (`saxo-auth-url`, `saxo-exchange-code`, `saxo-refresh-token`)
- [x] Endpoint `balance-eur` compatible Saxo et Binance

### Frontend
- [x] Composant `SaxoOAuthModal` créé
- [x] Section tokens améliorée dans `BrokerForm`
- [x] Bouton "🔐 OAuth2" ajouté dans la page Brokers
- [x] Support de l'affichage du solde pour Saxo dans `BrokerBalance`
- [x] Services API mis à jour

### Documentation
- [x] Documentation complète créée
- [x] Guide de dépannage inclus
- [x] Exemples de code fournis

---

## 🎯 Résultat

Après implémentation :
- ✅ Authentification OAuth2 fonctionnelle avec Saxo Bank
- ✅ Obtention et échange du code d'autorisation
- ✅ Sauvegarde automatique des tokens
- ✅ Rafraîchissement automatique des tokens
- ✅ Affichage du solde EUR pour les comptes Saxo
- ✅ Interface utilisateur intuitive pour gérer l'OAuth2
- ✅ Gestion des erreurs complète
- ✅ Logging amélioré pour le débogage

