# 🏦 Saxo Bank : OAuth2 et Affichage du Solde EUR

## 📋 Vue d'ensemble

Ce guide explique :
1. **Comment obtenir des tokens OAuth2** pour se connecter à Saxo Bank
2. **Comment afficher le solde EUR** sur la page des brokers
3. **Le processus complet d'authentification** OAuth2 avec Saxo

---

## 🔐 Partie 1 : Obtention des Tokens OAuth2

### Étape 1 : Créer une Application OAuth2 sur Saxo Bank

#### 1.1 Accéder au Portail Développeur Saxo

1. **Aller sur le portail développeur** :
   - **Simulation** : https://www.developer.saxo/openapi/sim
   - **Live** : https://www.developer.saxo/openapi/trade

2. **Se connecter** avec votre compte Saxo Bank

3. **Créer une nouvelle application** :
   - Cliquer sur "My Apps" ou "Applications"
   - Cliquer sur "Create New App" ou "Nouvelle Application"

#### 1.2 Configurer l'Application

**Informations à fournir** :

- **App Name** : Nom de votre application (ex: "Mon Trading App")
- **Redirect URI** : URL de callback après authentification
  - Exemple pour développement local : `http://localhost:8080/callback`
  - Exemple pour production : `https://votre-domaine.com/brokers/saxo/callback`
- **Scopes** : Permissions demandées
  - `openid` : Authentification de base (obligatoire)
  - `trading` : Trading (si vous voulez passer des ordres)
  - `read` : Lecture des données (recommandé)

**⚠️ Important** :
- La Redirect URI doit correspondre **exactement** à celle configurée dans votre application
- Pour la simulation, utilisez `https://sim.logonvalidation.net`
- Pour le live, utilisez `https://live.logonvalidation.net`

#### 1.3 Récupérer les Credentials

Après création, vous obtiendrez :

- **Client ID** : Identifiant unique de votre application
- **Client Secret** : Secret pour authentifier votre application
- **Redirect URI** : L'URI que vous avez configurée

**Exemple** :
```
Client ID: abc123xyz789
Client Secret: secret_key_here_123456
Redirect URI: http://localhost:8080/callback
```

---

### Étape 2 : Configurer l'Application dans votre Site

#### 2.1 Créer un BrokerAccount pour Saxo

**Via l'interface web** :

1. Aller sur la page de configuration des brokers
2. Cliquer sur "Ajouter un nouveau courtier"
3. Sélectionner "Saxo Bank"
4. Remplir les champs :
   - **Nom** : "Mon compte Saxo" (ou autre nom)
   - **Client ID** : Le Client ID récupéré
   - **Client Secret** : Le Client Secret récupéré
   - **Redirect URI** : L'URI configurée (ex: `http://localhost:8080/callback`)
   - **Environnement** : Simulation ou Live

**Via le shell Django** :
```python
from apps.trading.models.brokers import BrokerAccount, Broker
from django.contrib.auth.models import User

user = User.objects.get(username='votre_username')
broker = Broker.objects.get(broker_type='SAXO')

account = BrokerAccount.objects.create(
    user=user,
    broker=broker,
    name="Mon compte Saxo",
    broker_type='SAXO',
    environment='simulation',
    saxo_client_id='votre_client_id',
    saxo_client_secret='votre_client_secret',
    saxo_redirect_uri='http://localhost:8080/callback'
)
```

---

### Étape 3 : Obtenir l'URL d'Authentification

#### 3.1 Via l'Interface Web

1. Aller sur la page des brokers (`/brokers/`)
2. Trouver votre compte Saxo
3. Cliquer sur "Obtenir URL d'authentification" ou "Connecter à Saxo"
4. Vous serez redirigé vers la page de connexion Saxo Bank

#### 3.2 Via l'API

**Endpoint** : `GET /api/broker-accounts/{id}/saxo-auth-url/`

**Exemple de requête** :
```bash
curl -X GET "http://localhost:8000/api/broker-accounts/1/saxo-auth-url/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Réponse** :
```json
{
  "auth_url": "https://sim.logonvalidation.net/authorize?response_type=code&client_id=abc123&redirect_uri=http://localhost:8080/callback&state=xyz123"
}
```

#### 3.3 Code Python

**Fichier** : `backend/apps/trading/brokers/saxo.py`

```python
def get_authorization_url(self, state: str = None) -> str:
    """
    Obtenir l'URL d'autorisation OAuth2
    
    Args:
        state: État pour CSRF protection
        
    Returns:
        URL d'autorisation
    """
    params = {
        'response_type': 'code',
        'client_id': self.client_id,
        'redirect_uri': self.redirect_uri,
    }
    if state:
        params['state'] = state
    
    return f"{self.auth_url}/authorize?{urlencode(params)}"
```

**Utilisation** :
```python
from apps.trading.models.brokers import BrokerAccount
from apps.trading.services.broker_service import BrokerService

account = BrokerAccount.objects.get(id=1)
service = BrokerService(request.user)
broker = service.get_broker_instance(account)

auth_url = broker.get_authorization_url(state='unique_state_123')
print(f"URL d'authentification: {auth_url}")
```

---

### Étape 4 : Autoriser l'Application

1. **Ouvrir l'URL d'authentification** dans votre navigateur
2. **Se connecter** avec vos identifiants Saxo Bank
3. **Autoriser l'application** à accéder à votre compte
4. **Redirection automatique** vers votre Redirect URI avec un code

**Exemple d'URL de callback** :
```
http://localhost:8080/callback?code=AUTHORIZATION_CODE_HERE&state=xyz123
```

**Paramètres dans l'URL** :
- `code` : Code d'autorisation (valide 10 minutes)
- `state` : État que vous avez passé (pour vérifier la requête)

---

### Étape 5 : Échanger le Code contre des Tokens

#### 5.1 Via l'Interface Web

Si vous avez configuré le callback dans votre application, le code sera automatiquement échangé contre des tokens.

#### 5.2 Via l'API

**Endpoint** : `POST /api/broker-accounts/{id}/exchange-code/`

**Body** :
```json
{
  "code": "AUTHORIZATION_CODE_HERE"
}
```

**Réponse** :
```json
{
  "success": true,
  "message": "Tokens obtenus avec succès",
  "token_expires_at": "2024-01-15T12:00:00Z"
}
```

#### 5.3 Code Python

**Fichier** : `backend/apps/trading/brokers/saxo.py`

```python
def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
    """
    Échanger le code d'autorisation contre des tokens
    
    Args:
        code: Code d'autorisation OAuth2
        
    Returns:
        Dictionnaire avec access_token, refresh_token, etc.
    """
    try:
        url = f"{self.auth_url}/token"
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
        }
        
        response = self._session.post(url, data=data, timeout=30)
        response.raise_for_status()
        
        token_data = response.json()
        
        # Mettre à jour les tokens
        self.access_token = token_data['access_token']
        self.refresh_token = token_data.get('refresh_token')
        
        expires_in = token_data.get('expires_in', 3600)
        self.token_expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
        
        self._authenticated = True
        
        return {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'token_expires_at': self.token_expires_at,
            'expires_in': expires_in,
        }
        
    except Exception as e:
        logger.error(f"Saxo code exchange error: {e}")
        raise BrokerAuthenticationError(f"Code exchange failed: {e}")
```

**Utilisation** :
```python
from apps.trading.models.brokers import BrokerAccount
from apps.trading.services.broker_service import BrokerService

account = BrokerAccount.objects.get(id=1)
service = BrokerService(request.user)
broker = service.get_broker_instance(account)

# Échanger le code
token_data = broker.exchange_code_for_token('AUTHORIZATION_CODE_HERE')

# Sauvegarder les tokens dans la base de données
account.saxo_access_token = token_data['access_token']
account.saxo_refresh_token = token_data['refresh_token']
account.saxo_token_expires_at = token_data['token_expires_at']
account.save()
```

---

### Étape 6 : Rafraîchir les Tokens (Automatique)

Les tokens d'accès expirent après 1 heure. Le système rafraîchit automatiquement les tokens en utilisant le `refresh_token`.

**Code de rafraîchissement** :

```python
def _refresh_token(self) -> bool:
    """
    Rafraîchir le token d'accès
    
    Returns:
        True si le rafraîchissement a réussi
    """
    try:
        url = f"{self.auth_url}/token"
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        
        response = self._session.post(url, data=data, timeout=30)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data['access_token']
        self.refresh_token = token_data.get('refresh_token', self.refresh_token)
        
        expires_in = token_data.get('expires_in', 3600)
        self.token_expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
        
        self._authenticated = True
        logger.info("Saxo: Token refreshed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Saxo token refresh error: {e}")
        raise BrokerAuthenticationError(f"Token refresh failed: {e}")
```

**⚠️ Tokens 24h** :

Saxo propose aussi des tokens 24h (non rafraîchissables). Si vous utilisez un token 24h :
- Mettez le même token dans `access_token` et `refresh_token`
- Le système détectera automatiquement qu'il s'agit d'un token 24h
- Aucun rafraîchissement ne sera tenté

---

## 💶 Partie 2 : Affichage du Solde EUR

### Fonction pour Récupérer le Solde

#### Méthode 1 : Via `get_account_info()`

**Fichier** : `backend/apps/trading/brokers/saxo.py`

```python
def get_account_info(self) -> Dict[str, Any]:
    """
    Récupérer les informations du compte
    
    Returns:
        Dictionnaire avec les infos du compte, incluant le solde
    """
    try:
        params = {}
        if self.client_key:
            params['ClientKey'] = self.client_key
        
        # Récupérer les balances
        balance_data = self._make_request('GET', '/port/v1/balances', params=params)
        
        # Récupérer les infos du compte
        account_data = self._make_request('GET', '/port/v1/accounts', params=params)
        
        accounts = account_data.get('Data', [])
        primary_account = accounts[0] if accounts else {}
        
        return {
            'account_id': primary_account.get('AccountId'),
            'account_key': primary_account.get('AccountKey'),
            'currency': primary_account.get('Currency', 'EUR'),
            'balance': balance_data.get('TotalValue', 0),
            'cash_balance': balance_data.get('CashBalance', 0),
            'margin_available': balance_data.get('MarginAvailableForTrading', 0),
            'margin_used': balance_data.get('MarginUsedByCurrentPositions', 0),
            'unrealized_pnl': balance_data.get('UnrealizedProfitLoss', 0),
            'account_type': primary_account.get('AccountType'),
            'is_active': primary_account.get('Active', False),
        }
        
    except Exception as e:
        logger.error(f"Saxo get_account_info error: {e}")
        return {}
```

#### Méthode 2 : Implémenter `get_account_balance()`

**Fichier** : `backend/apps/trading/brokers/saxo.py`

**Code à ajouter** :

```python
def get_account_balance(self) -> Dict[str, Decimal]:
    """
    Get account balances.
    
    Returns:
        Dictionary mapping currency to balance
    """
    try:
        # Récupérer les informations du compte
        account_info = self.get_account_info()
        
        if not account_info:
            return {}
        
        # Extraire la devise et le solde
        currency = account_info.get('currency', 'EUR')
        cash_balance = account_info.get('cash_balance', 0)
        total_balance = account_info.get('balance', 0)
        
        # Formater les balances
        balances = {}
        
        # Solde en cash (devise principale)
        if cash_balance:
            balances[currency] = Decimal(str(cash_balance))
        
        # Solde total (si différent)
        if total_balance and total_balance != cash_balance:
            balances[f'{currency}_total'] = Decimal(str(total_balance))
        
        # Autres informations
        if account_info.get('margin_available'):
            balances[f'{currency}_margin_available'] = Decimal(str(account_info['margin_available']))
        
        return balances
        
    except Exception as e:
        logger.error(f"Saxo get_account_balance error: {e}")
        self._set_error(f"Get account balance error: {str(e)}")
        return {}
```

---

### Solution 1 : API REST (Recommandé pour React/TypeScript)

#### Étape 1 : Compléter l'endpoint API `refresh_balance`

**Fichier** : `backend/apps/trading/api/views.py`

**Dans la classe `BrokerAccountViewSet`** :

```python
@action(detail=True, methods=['post'], url_path='refresh-balance')
def refresh_balance(self, request, pk=None):
    """
    POST /api/broker-accounts/1/refresh_balance/
    Rafraîchit la balance du compte et retourne le solde EUR.
    """
    from django.utils import timezone
    from decimal import Decimal
    from ..services.broker_service import BrokerService
    import logging
    
    logger = logging.getLogger('trading.api.brokers')
    
    account = self.get_object()
    
    # Vérifier que c'est un compte Saxo
    if account.broker_type != 'SAXO':
        return Response({
            'success': False,
            'error': 'Cette méthode est uniquement pour Saxo Bank'
        }, status=400)
    
    service = BrokerService(request.user)
    
    try:
        # Récupérer toutes les balances
        balances = service.get_account_balance(account)
        
        # Extraire le solde EUR (ou la devise principale)
        # Saxo retourne généralement la devise du compte
        currency = account.currency or 'EUR'
        eur_balance = balances.get(currency, balances.get('EUR', Decimal('0')))
        
        # Si pas de EUR, prendre la première balance disponible
        if eur_balance == 0 and balances:
            currency = list(balances.keys())[0]
            eur_balance = balances[currency]
        
        # Mettre à jour le modèle
        account.balance = eur_balance
        account.currency = currency
        account.balance_updated_at = timezone.now()
        account.save(update_fields=['balance', 'currency', 'balance_updated_at'])
        
        # Formater les balances
        all_balances = {
            k: float(v) 
            for k, v in balances.items() 
            if not k.endswith('_free') and not k.endswith('_locked') and not k.endswith('_margin_available')
        }
        
        return Response({
            'success': True,
            'balance_eur': float(eur_balance),
            'currency': currency,
            'all_balances': all_balances,
            'account': BrokerAccountSerializer(account).data
        })
    except Exception as e:
        logger.error(f"Error refreshing balance for account {account.id}: {e}")
        return Response({
            'success': False,
            'error': str(e),
            'balance_eur': 0.0
        }, status=500)
```

#### Étape 2 : Ajouter une action pour récupérer le solde EUR

```python
@action(detail=True, methods=['get'], url_path='balance-eur')
def balance_eur(self, request, pk=None):
    """
    GET /api/broker-accounts/1/balance_eur/
    Récupère le solde EUR actuel du compte sans mettre à jour la base de données.
    """
    from decimal import Decimal
    from ..services.broker_service import BrokerService
    from django.utils import timezone
    import logging
    
    logger = logging.getLogger('trading.api.brokers')
    
    account = self.get_object()
    
    # Vérifier que c'est un compte Saxo
    if account.broker_type != 'SAXO':
        return Response({
            'success': False,
            'error': 'Cette méthode est uniquement pour Saxo Bank'
        }, status=400)
    
    service = BrokerService(request.user)
    
    try:
        # Récupérer toutes les balances
        balances = service.get_account_balance(account)
        
        # Extraire le solde EUR (ou la devise principale)
        currency = account.currency or 'EUR'
        eur_balance = balances.get(currency, balances.get('EUR', Decimal('0')))
        
        # Si pas de EUR, prendre la première balance disponible
        if eur_balance == 0 and balances:
            currency = list(balances.keys())[0]
            eur_balance = balances[currency]
        
        # Formater les balances
        all_balances = {
            k: float(v) 
            for k, v in balances.items() 
            if not k.endswith('_free') and not k.endswith('_locked') and not k.endswith('_margin_available')
        }
        
        return Response({
            'success': True,
            'balance_eur': float(eur_balance),
            'currency': currency,
            'all_balances': all_balances,
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting EUR balance for account {account.id}: {e}")
        return Response({
            'success': False,
            'error': str(e),
            'balance_eur': 0.0
        }, status=500)
```

#### Étape 3 : Utiliser depuis React/TypeScript

Le même hook `useBrokerBalance` que pour Binance fonctionne aussi pour Saxo :

```typescript
// frontend/src/components/brokers/BrokerCard.tsx
import { useBrokerBalance } from '../../hooks/useBrokerBalance';

const BrokerCard = ({ account }: { account: BrokerAccount }) => {
  const { balanceEur, allBalances, loading, error, refresh } = useBrokerBalance(account.id);

  return (
    <div className="card">
      <div className="card-header">
        <h5>{account.name} ({account.broker.name})</h5>
      </div>
      <div className="card-body">
        <p>
          <strong>Solde EUR :</strong>
          {loading ? (
            <span className="text-muted">Chargement...</span>
          ) : error ? (
            <span className="text-danger">{error}</span>
          ) : (
            <span className="badge bg-success fs-5">
              {balanceEur !== null ? `${balanceEur.toFixed(2)} €` : 'N/A'}
            </span>
          )}
        </p>
        <button onClick={refresh} className="btn btn-sm btn-outline-primary">
          <i className="fas fa-sync-alt"></i> Rafraîchir
        </button>
      </div>
    </div>
  );
};
```

---

### Solution 2 : Vue Django classique (Templates HTML)

**Fichier** : `backend/apps/trading/views/brokers.py`

```python
@login_required
def broker_dashboard(request):
    """Tableau de bord des courtiers avec solde EUR"""
    from decimal import Decimal
    from ..models.brokers import BrokerAccount
    from ..services.broker_service import BrokerService
    import logging
    
    logger = logging.getLogger('trading.views.brokers')
    
    service = BrokerService(request.user)
    
    # Récupérer tous les comptes brokers de l'utilisateur
    broker_accounts = BrokerAccount.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('broker').order_by('name')
    
    # Récupérer les balances EUR pour chaque compte
    broker_balances_eur = {}
    for account in broker_accounts:
        try:
            # Récupérer toutes les balances
            balances = service.get_account_balance(account)
            
            # Pour Saxo, extraire le solde de la devise principale
            if account.broker_type == 'SAXO':
                currency = account.currency or 'EUR'
                eur_balance = balances.get(currency, balances.get('EUR', Decimal('0')))
                
                # Si pas de EUR, prendre la première balance disponible
                if eur_balance == 0 and balances:
                    currency = list(balances.keys())[0]
                    eur_balance = balances[currency]
            else:
                # Pour Binance, utiliser directement EUR
                eur_balance = balances.get('EUR', Decimal('0'))
                currency = 'EUR'
            
            # Formater les balances
            all_balances = {
                k: float(v) 
                for k, v in balances.items() 
                if not k.endswith('_free') and not k.endswith('_locked')
            }
            
            broker_balances_eur[account.id] = {
                'eur': float(eur_balance),
                'currency': currency,
                'all': all_balances
            }
            
            # Mettre à jour le modèle si nécessaire
            if account.balance != eur_balance:
                account.balance = eur_balance
                account.currency = currency
                account.save(update_fields=['balance', 'currency'])
                
        except Exception as e:
            logger.error(f"Error getting balance for account {account.id}: {e}")
            broker_balances_eur[account.id] = {
                'eur': 0.0,
                'currency': 'EUR',
                'all': {},
                'error': str(e)
            }
    
    return render(request, 'trading/broker_dashboard.html', {
        'broker_accounts': broker_accounts,
        'broker_balances_eur': broker_balances_eur,
    })
```

---

## 📊 Résumé du Flux OAuth2

```
1. Créer une application OAuth2 sur Saxo Developer Portal
   ↓
2. Configurer Client ID, Client Secret, Redirect URI
   ↓
3. Obtenir l'URL d'authentification (get_authorization_url)
   ↓
4. Rediriger l'utilisateur vers Saxo pour se connecter
   ↓
5. Utilisateur autorise l'application
   ↓
6. Saxo redirige vers Redirect URI avec un code
   ↓
7. Échanger le code contre des tokens (exchange_code_for_token)
   ↓
8. Sauvegarder access_token et refresh_token
   ↓
9. Utiliser access_token pour les requêtes API
   ↓
10. Rafraîchir automatiquement avec refresh_token quand nécessaire
```

---

## ✅ Checklist d'Implémentation

### Pour OAuth2

- [ ] Créer une application sur Saxo Developer Portal
- [ ] Configurer Client ID, Client Secret, Redirect URI
- [ ] Créer un BrokerAccount avec les credentials
- [ ] Implémenter la vue pour obtenir l'URL d'authentification
- [ ] Implémenter le callback pour échanger le code
- [ ] Sauvegarder les tokens dans BrokerAccount
- [ ] Tester le rafraîchissement automatique des tokens

### Pour l'Affichage du Solde

- [ ] Implémenter `get_account_balance()` dans SaxoBroker
- [ ] Compléter l'endpoint API `refresh_balance`
- [ ] Ajouter l'endpoint `balance_eur`
- [ ] Tester la récupération du solde
- [ ] Afficher le solde sur la page brokers (React ou Template)

---

## 🐛 Dépannage

### Problème : "Invalid redirect_uri"

**Cause** : La Redirect URI ne correspond pas exactement à celle configurée.

**Solution** : Vérifier que l'URI dans votre code correspond exactement à celle du portail développeur (y compris http/https, port, trailing slash).

### Problème : "Code expired"

**Cause** : Le code d'autorisation expire après 10 minutes.

**Solution** : Échanger le code immédiatement après l'obtention.

### Problème : "Refresh token expired"

**Cause** : Le refresh token a expiré ou a été révoqué.

**Solution** : Relancer le processus OAuth2 pour obtenir de nouveaux tokens.

### Problème : "Authentication failed"

**Causes possibles** :
1. Tokens invalides
2. Client ID/Secret incorrects
3. Environnement incorrect (simulation vs live)

**Solutions** :
1. Vérifier les tokens dans la base de données
2. Vérifier les credentials
3. Vérifier que l'environnement correspond (simulation/live)

---

## 📚 Ressources

- **Portail Développeur Saxo** :
  - Simulation : https://www.developer.saxo/openapi/sim
  - Live : https://www.developer.saxo/openapi/trade
- **Documentation API Saxo** : https://www.developer.saxo/openapi/learn
- **Modèle BrokerAccount** : `backend/apps/trading/models/brokers.py`
- **Service Broker** : `backend/apps/trading/services/broker_service.py`
- **Broker Saxo** : `backend/apps/trading/brokers/saxo.py`

---

## 🎯 Résultat Attendu

Après implémentation :
- ✅ Création d'une application OAuth2 sur Saxo
- ✅ Configuration des credentials dans BrokerAccount
- ✅ Obtention de l'URL d'authentification
- ✅ Échange du code contre des tokens
- ✅ Sauvegarde automatique des tokens
- ✅ Rafraîchissement automatique des tokens
- ✅ Affichage du solde EUR sur la page brokers
- ✅ Récupération et mise à jour du solde en temps réel

