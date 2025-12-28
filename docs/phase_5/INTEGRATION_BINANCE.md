# 🪙 Intégration Binance Testée

Ce guide explique comment tester et valider l'intégration complète avec Binance, de l'authentification API à la récupération des données.

---

## 📋 Vue d'ensemble

L'intégration Binance comprend :
1. **Authentification API** : Utilisation d'API Key et Secret
2. **Récupération de données** : Balances, positions, trades, ordres
3. **Placement d'ordres** : Passer des ordres via l'API
4. **Synchronisation** : Synchroniser les données avec la base locale

---

## 🔐 Test 1 : Authentification API

### 1.1 Configuration des Credentials

**Backend** : Les credentials sont stockés dans `BrokerAccount` :
- `binance_api_key` : Clé API Binance
- `binance_api_secret` : Secret API Binance
- `binance_testnet` : Utiliser le testnet (booléen)

### 1.2 Vérifier l'Authentification

**Backend** : `backend/apps/trading/api/views.py`

```python
@action(detail=True, methods=['post'], url_path='test-connection')
def test_connection(self, request, pk=None):
    """Tester la connexion à un broker"""
    account = self.get_object()
    service = BrokerService(request.user)
    
    try:
        result = service.test_connection(account)
        return Response(result)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
        }, status=500)
```

**Frontend** : `frontend/src/services/brokers.ts`

```typescript
export const testBinanceConnection = async (accountId: number) => {
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

**Test** :
```typescript
// Tester la connexion Binance
const testConnection = async () => {
  const accountId = 2; // ID du compte Binance
  const result = await testBinanceConnection(accountId);
  
  if (result.success) {
    console.log('✅ Binance connection successful');
  } else {
    console.error('❌ Connection failed:', result.error);
  }
};
```

---

## 📊 Test 2 : Récupération de Données

### 2.1 Récupérer le Solde

**Test** :
```typescript
export const getBinanceBalance = async (accountId: number) => {
  try {
    const response = await apiClient.post(`/broker-accounts/${accountId}/refresh-balance/`);
    return {
      success: response.data.success,
      balance_eur: response.data.balance_eur,
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
  const result = await getBinanceBalance(2);
  if (result.success) {
    console.log(`Balance EUR: ${result.balance_eur} €`);
    console.log('All balances:', result.all_balances);
  }
};
```

### 2.2 Récupérer les Balances (Toutes les Devises)

**Backend** : `backend/apps/trading/brokers/binance.py`

La méthode `get_account_balance()` retourne toutes les balances :

```python
def get_account_balance(self) -> Dict[str, Decimal]:
    """Get account balances."""
    try:
        response = self._make_request('GET', '/api/v3/account', signed=True)
        
        if not response:
            return {}
        
        balances = {}
        for balance in response.get('balances', []):
            asset = balance.get('asset', '')
            free = Decimal(balance.get('free', '0'))
            locked = Decimal(balance.get('locked', '0'))
            total = free + locked
            
            if total > 0:
                balances[asset] = total
                balances[f'{asset}_free'] = free
                balances[f'{asset}_locked'] = locked
        
        return balances
```

**Test** :
```typescript
const testAllBalances = async () => {
  const result = await getBinanceBalance(2);
  if (result.success && result.all_balances) {
    Object.entries(result.all_balances).forEach(([currency, amount]) => {
      if (amount > 0) {
        console.log(`${currency}: ${amount}`);
      }
    });
  }
};
```

### 2.3 Récupérer les Positions

**Backend** : Endpoint à créer si nécessaire

```python
@action(detail=True, methods=['get'], url_path='binance-positions')
def binance_positions(self, request, pk=None):
    """Récupérer les positions depuis Binance"""
    account = self.get_object()
    service = BrokerService(request.user)
    
    try:
        broker = service.get_broker_instance(account)
        positions = broker.get_positions()
        
        return Response({
            'success': True,
            'count': len(positions),
            'positions': positions,
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
        }, status=500)
```

**Test** :
```typescript
const testPositions = async () => {
  try {
    const response = await apiClient.get(`/broker-accounts/2/binance-positions/`);
    console.log(`Found ${response.data.count} positions`);
    console.log('Positions:', response.data.positions);
  } catch (error) {
    console.error('Error fetching positions:', error);
  }
};
```

### 2.4 Récupérer les Trades

**Test** :
```typescript
const testTrades = async () => {
  try {
    const response = await apiClient.get(`/broker-accounts/2/binance-trades/`);
    console.log('Trades:', response.data);
  } catch (error) {
    console.error('Error fetching trades:', error);
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
    """Synchroniser les assets depuis Binance"""
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
    const response = await apiClient.post(`/broker-accounts/2/sync-assets/`);
    if (response.data.success) {
      console.log(`✅ Synced ${response.data.count} assets`);
    } else {
      console.error('❌ Sync failed:', response.data.error);
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
    const response = await apiClient.post(`/broker-accounts/2/sync-positions/`);
    console.log('Sync result:', response.data);
  } catch (error) {
    console.error('Sync error:', error);
  }
};
```

### 3.3 Synchroniser les Trades

**Test** :
```typescript
const testSyncTrades = async () => {
  try {
    const response = await apiClient.post(`/broker-accounts/2/sync-trades/`);
    console.log('Trades synced:', response.data);
  } catch (error) {
    console.error('Sync error:', error);
  }
};
```

---

## 📝 Test 4 : Placement d'Ordres

### 4.1 Passer un Ordre Market

**Backend** : Endpoint à créer

```python
@action(detail=True, methods=['post'], url_path='place-order')
def place_order(self, request, pk=None):
    """Placer un ordre via Binance"""
    account = self.get_object()
    service = BrokerService(request.user)
    
    symbol = request.data.get('symbol')
    quantity = request.data.get('quantity')
    side = request.data.get('side', 'BUY')
    order_type = request.data.get('order_type', 'MARKET')
    
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
const testPlaceMarketOrder = async () => {
  try {
    const response = await apiClient.post(`/broker-accounts/2/place-order/`, {
      symbol: 'BTCUSDT',
      quantity: 0.001,
      side: 'BUY',
      order_type: 'MARKET',
    });
    
    if (response.data.success) {
      console.log(`✅ Order placed: ${response.data.order_id}`);
    }
  } catch (error) {
    console.error('❌ Order error:', error);
  }
};
```

### 4.2 Passer un Ordre Limit

**Test** :
```typescript
const testPlaceLimitOrder = async () => {
  try {
    const response = await apiClient.post(`/broker-accounts/2/place-order/`, {
      symbol: 'BTCUSDT',
      quantity: 0.001,
      side: 'BUY',
      order_type: 'LIMIT',
      price: 50000,
    });
    
    if (response.data.success) {
      console.log(`✅ Limit order placed: ${response.data.order_id}`);
    }
  } catch (error) {
    console.error('❌ Order error:', error);
  }
};
```

### 4.3 Annuler un Ordre

**Test** :
```typescript
const testCancelOrder = async () => {
  try {
    const response = await apiClient.post(`/broker-accounts/2/cancel-order/`, {
      order_id: '123456',
    });
    
    if (response.data.success) {
      console.log('✅ Order cancelled');
    }
  } catch (error) {
    console.error('❌ Cancel error:', error);
  }
};
```

---

## ✅ Checklist de Validation

### Authentification

- [ ] API Key et Secret configurés correctement
- [ ] Test de connexion réussi
- [ ] Testnet fonctionne (si utilisé)
- [ ] Permissions API correctes (lecture, trading)

### Récupération de Données

- [ ] Solde EUR récupéré avec succès
- [ ] Toutes les balances récupérées
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
- [ ] Erreurs API Binance gérées
- [ ] Rate limiting géré
- [ ] Messages d'erreur clairs pour l'utilisateur

---

## 🧪 Tests Automatisés

### Test avec Jest/Vitest

**Fichier** : `frontend/src/services/__tests__/binance.test.ts`

```typescript
import { describe, it, expect } from 'vitest';
import { testBinanceConnection, getBinanceBalance } from '../brokers';

describe('Binance Integration', () => {
  it('should test connection', async () => {
    const result = await testBinanceConnection(2);
    expect(result).toHaveProperty('success');
  });

  it('should get balance', async () => {
    const result = await getBinanceBalance(2);
    if (result.success) {
      expect(result.balance_eur).toBeGreaterThanOrEqual(0);
    }
  });
});
```

---

## 🐛 Dépannage

### Problème : "Invalid API Key"

**Solutions** :
1. Vérifier que l'API Key est correcte
2. Vérifier que l'API Secret est correct
3. Vérifier que l'API Key n'est pas expirée
4. Vérifier les permissions de l'API Key

### Problème : "Signature for this request is not valid"

**Solutions** :
1. Vérifier que l'API Secret est correct
2. Vérifier le timestamp de la requête
3. Vérifier le format de la signature

### Problème : "Rate limit exceeded"

**Solutions** :
1. Implémenter un système de rate limiting
2. Réduire la fréquence des requêtes
3. Utiliser les poids de requête Binance correctement

### Problème : "Insufficient balance"

**Solutions** :
1. Vérifier le solde disponible
2. Vérifier que la quantité est correcte
3. Vérifier les frais de trading

---

## 📚 Ressources

- **Guide Binance API** : `docs/BINANCE_API_GUIDE.md`
- **Affichage du Solde** : `docs/BINANCE_EUR_BALANCE_DISPLAY.md`
- **Documentation Binance API** : https://binance-docs.github.io/apidocs/spot/en/
- **Testnet Binance** : https://testnet.binance.vision/

---

## 🎯 Résultat Attendu

Après validation :
- ✅ L'authentification API fonctionne
- ✅ Les données sont récupérées depuis Binance
- ✅ Les synchronisations fonctionnent
- ✅ Les ordres peuvent être passés
- ✅ Les erreurs sont gérées correctement

