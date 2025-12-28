# 🏦 Intégration Saxo Testée

Ce guide explique comment tester et valider l'intégration complète avec Saxo Bank, de l'authentification OAuth2 à la récupération des données.

---

## 📋 Vue d'ensemble

L'intégration Saxo comprend :
1. **Authentification OAuth2** : Obtenir et rafraîchir les tokens
2. **Récupération de données** : Assets, positions, trades, balances
3. **Placement d'ordres** : Passer des ordres via l'API
4. **Synchronisation** : Synchroniser les données avec la base locale

---

## 🔐 Test 1 : Authentification OAuth2

### 1.1 Obtenir l'URL d'Authentification

**Backend** : `backend/apps/trading/api/views.py`

```python
@action(detail=True, methods=['get'], url_path='saxo-auth-url')
def saxo_auth_url(self, request, pk=None):
    """Obtenir l'URL d'authentification Saxo"""
    account = self.get_object()
    
    if account.broker_type != 'SAXO':
        return Response({'error': 'Not a Saxo account'}, status=400)
    
    from ..services.broker_service import BrokerService
    service = BrokerService(request.user)
    broker = service.get_broker_instance(account)
    
    auth_url = broker.get_authorization_url(state='test_state')
    
    return Response({'auth_url': auth_url})
```

**Frontend** : `frontend/src/services/brokers.ts`

```typescript
export const getSaxoAuthUrl = async (accountId: number): Promise<string | null> => {
  try {
    const response = await apiClient.get(`/broker-accounts/${accountId}/saxo-auth-url/`);
    return response.data.auth_url;
  } catch (error: any) {
    console.error('Error getting Saxo auth URL:', error);
    return null;
  }
};
```

**Test** :
```typescript
// Tester l'obtention de l'URL
const testAuthUrl = async () => {
  const accountId = 1; // ID du compte Saxo
  const authUrl = await getSaxoAuthUrl(accountId);
  
  if (authUrl) {
    console.log('Auth URL:', authUrl);
    // Ouvrir dans une nouvelle fenêtre pour tester
    window.open(authUrl, '_blank');
  } else {
    console.error('Failed to get auth URL');
  }
};
```

### 1.2 Échanger le Code contre des Tokens

**Frontend** : `frontend/src/services/brokers.ts`

```typescript
export const exchangeSaxoCode = async (
  accountId: number,
  code: string
): Promise<{ success: boolean; error?: string }> => {
  try {
    const response = await apiClient.post(`/broker-accounts/${accountId}/exchange-code/`, {
      code,
    });
    
    return { success: true };
  } catch (error: any) {
    return {
      success: false,
      error: error.response?.data?.error || 'Failed to exchange code',
    };
  }
};
```

**Test** :
```typescript
// Après redirection depuis Saxo avec le code
const testCodeExchange = async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get('code');
  const accountId = 1;
  
  if (code) {
    const result = await exchangeSaxoCode(accountId, code);
    if (result.success) {
      console.log('Tokens obtained successfully');
    } else {
      console.error('Error:', result.error);
    }
  }
};
```

### 1.3 Vérifier l'Authentification

**Test** :
```typescript
export const testSaxoConnection = async (accountId: number) => {
  try {
    const response = await apiClient.post(`/broker-accounts/${accountId}/test-connection/`);
    return {
      success: response.data.success || false,
      message: response.data.message,
      error: response.data.error,
    };
  } catch (error: any) {
    return {
      success: false,
      error: error.response?.data?.error || 'Connection test failed',
    };
  }
};
```

---

## 📊 Test 2 : Récupération de Données

### 2.1 Récupérer le Solde

**Test** :
```typescript
export const getSaxoBalance = async (accountId: number) => {
  try {
    const response = await apiClient.post(`/broker-accounts/${accountId}/refresh-balance/`);
    return {
      success: response.data.success,
      balance_eur: response.data.balance_eur,
      currency: response.data.currency,
      all_balances: response.data.all_balances,
    };
  } catch (error: any) {
    return {
      success: false,
      error: error.response?.data?.error || 'Failed to get balance',
    };
  }
};

// Utilisation
const testBalance = async () => {
  const result = await getSaxoBalance(1);
  if (result.success) {
    console.log(`Balance: ${result.balance_eur} ${result.currency}`);
  }
};
```

### 2.2 Récupérer les Assets

**Backend** : Endpoint à créer si nécessaire

```python
@action(detail=True, methods=['get'], url_path='saxo-assets')
def saxo_assets(self, request, pk=None):
    """Récupérer les assets depuis Saxo"""
    account = self.get_object()
    service = BrokerService(request.user)
    
    try:
        broker = service.get_broker_instance(account)
        assets = broker.get_assets(asset_type='Stock', limit=100)
        
        return Response({
            'success': True,
            'count': len(assets),
            'assets': [asset.__dict__ for asset in assets],
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
        }, status=500)
```

**Test** :
```typescript
const testAssets = async () => {
  try {
    const response = await apiClient.get(`/broker-accounts/1/saxo-assets/`);
    console.log(`Found ${response.data.count} assets`);
  } catch (error) {
    console.error('Error fetching assets:', error);
  }
};
```

### 2.3 Récupérer les Positions

**Test** :
```typescript
const testPositions = async () => {
  try {
    const response = await apiClient.get(`/broker-accounts/1/saxo-positions/`);
    console.log('Positions:', response.data);
  } catch (error) {
    console.error('Error fetching positions:', error);
  }
};
```

---

## 🔄 Test 3 : Synchronisation

### 3.1 Synchroniser les Assets

**Backend** : `backend/apps/trading/api/views.py`

```python
@action(detail=True, methods=['post'], url_path='sync-assets')
def sync_assets(self, request, pk=None):
    """Synchroniser les assets depuis Saxo"""
    account = self.get_object()
    service = BrokerService(request.user)
    
    try:
        result = service.sync_assets_to_db(account)
        return Response({
            'success': result.get('success', False),
            'count': result.get('count', 0),
            'message': result.get('message', ''),
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
        }, status=500)
```

**Test** :
```typescript
const testSyncAssets = async () => {
  try {
    const response = await apiClient.post(`/broker-accounts/1/sync-assets/`);
    if (response.data.success) {
      console.log(`Synced ${response.data.count} assets`);
    }
  } catch (error) {
    console.error('Sync error:', error);
  }
};
```

### 3.2 Synchroniser les Positions

**Test** :
```typescript
const testSyncPositions = async () => {
  try {
    const response = await apiClient.post(`/broker-accounts/1/sync-positions/`);
    console.log('Sync result:', response.data);
  } catch (error) {
    console.error('Sync error:', error);
  }
};
```

---

## 📝 Test 4 : Placement d'Ordres

### 4.1 Passer un Ordre

**Backend** : Endpoint à créer

```python
@action(detail=True, methods=['post'], url_path='place-order')
def place_order(self, request, pk=None):
    """Placer un ordre via Saxo"""
    account = self.get_object()
    service = BrokerService(request.user)
    
    symbol = request.data.get('symbol')
    quantity = request.data.get('quantity')
    side = request.data.get('side', 'Buy')
    order_type = request.data.get('order_type', 'Market')
    
    try:
        broker = service.get_broker_instance(account)
        result = broker.place_order(
            symbol=symbol,
            quantity=Decimal(str(quantity)),
            side=side,
            order_type=order_type,
        )
        
        return Response({
            'success': result.success,
            'order_id': result.order_id,
            'status': result.status,
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
        }, status=500)
```

**Test** :
```typescript
const testPlaceOrder = async () => {
  try {
    const response = await apiClient.post(`/broker-accounts/1/place-order/`, {
      symbol: 'AAPL',
      quantity: 10,
      side: 'Buy',
      order_type: 'Market',
    });
    
    if (response.data.success) {
      console.log(`Order placed: ${response.data.order_id}`);
    }
  } catch (error) {
    console.error('Order error:', error);
  }
};
```

---

## ✅ Checklist de Validation

### Authentification

- [ ] URL d'authentification obtenue avec succès
- [ ] Redirection vers Saxo fonctionne
- [ ] Code OAuth2 échangé contre tokens
- [ ] Tokens sauvegardés dans `BrokerAccount`
- [ ] Test de connexion réussi
- [ ] Refresh token automatique fonctionne

### Récupération de Données

- [ ] Solde récupéré avec succès
- [ ] Assets récupérés depuis Saxo
- [ ] Positions récupérées
- [ ] Trades récupérés
- [ ] Ordres en cours récupérés

### Synchronisation

- [ ] Synchronisation des assets fonctionne
- [ ] Synchronisation des positions fonctionne
- [ ] Synchronisation des trades fonctionne
- [ ] Logs de synchronisation créés
- [ ] Erreurs de synchronisation gérées

### Placement d'Ordres

- [ ] Ordre marché passé avec succès
- [ ] Ordre limite passé avec succès
- [ ] Annulation d'ordre fonctionne
- [ ] Statut d'ordre récupéré

### Gestion d'Erreurs

- [ ] Erreurs d'authentification gérées
- [ ] Erreurs API Saxo gérées
- [ ] Timeout gérés
- [ ] Messages d'erreur clairs pour l'utilisateur

---

## 🧪 Tests Automatisés

### Test avec Jest/Vitest

**Fichier** : `frontend/src/services/__tests__/saxo.test.ts`

```typescript
import { describe, it, expect, vi } from 'vitest';
import { getSaxoAuthUrl, testSaxoConnection, getSaxoBalance } from '../brokers';

describe('Saxo Integration', () => {
  it('should get auth URL', async () => {
    const authUrl = await getSaxoAuthUrl(1);
    expect(authUrl).toContain('logonvalidation.net');
  });

  it('should test connection', async () => {
    const result = await testSaxoConnection(1);
    expect(result).toHaveProperty('success');
  });

  it('should get balance', async () => {
    const result = await getSaxoBalance(1);
    if (result.success) {
      expect(result.balance_eur).toBeGreaterThanOrEqual(0);
    }
  });
});
```

---

## 🐛 Dépannage

### Problème : "Authentication failed"

**Solutions** :
1. Vérifier que les tokens sont valides
2. Vérifier que le refresh token fonctionne
3. Relancer le processus OAuth2 si nécessaire

### Problème : "API Error"

**Solutions** :
1. Vérifier les logs : `logs/brokers.log`
2. Vérifier que l'environnement est correct (simulation/live)
3. Vérifier les permissions de l'application OAuth2

### Problème : "No data returned"

**Solutions** :
1. Vérifier que le compte Saxo a des données
2. Vérifier les paramètres de requête
3. Vérifier les logs de l'API Saxo

---

## 📚 Ressources

- **Guide OAuth2** : `docs/SAXO_OAUTH2_AND_BALANCE.md`
- **Fichiers de Connexion** : `docs/SAXO_CONNECTION_FILES.md`
- **Affichage du Solde** : `docs/SAXO_BALANCE_DISPLAY.md`
- **Documentation Saxo** : https://www.developer.saxo/openapi/learn

---

## 🎯 Résultat Attendu

Après validation :
- ✅ L'authentification OAuth2 fonctionne
- ✅ Les données sont récupérées depuis Saxo
- ✅ Les synchronisations fonctionnent
- ✅ Les ordres peuvent être passés
- ✅ Les erreurs sont gérées correctement

