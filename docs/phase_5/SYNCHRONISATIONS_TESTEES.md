# 🔄 Synchronisations Testées

Ce guide explique comment tester et valider toutes les synchronisations de données entre les brokers et la base de données locale.

---

## 📋 Vue d'ensemble

Les synchronisations permettent de :
1. **Récupérer les données** depuis les brokers (Saxo, Binance)
2. **Sauvegarder dans la base** de données locale
3. **Maintenir la cohérence** entre les données broker et locales
4. **Logger les opérations** pour le suivi

---

## 🔧 Types de Synchronisations

### 1. Synchronisation des Assets

Synchronise le catalogue d'assets disponibles depuis les brokers.

### 2. Synchronisation des Positions

Synchronise les positions ouvertes et fermées.

### 3. Synchronisation des Trades

Synchronise l'historique des trades.

### 4. Synchronisation des Prix

Synchronise les prix actuels des assets.

### 5. Synchronisation des Ordres

Synchronise les ordres en cours et exécutés.

---

## 🧪 Test 1 : Synchronisation des Assets

### 1.1 Endpoint API

**Backend** : `backend/apps/trading/api/views.py`

```python
@action(detail=True, methods=['post'], url_path='sync-assets')
def sync_assets(self, request, pk=None):
    """Synchroniser les assets depuis le broker"""
    account = self.get_object()
    service = BrokerService(request.user)
    
    try:
        result = service.sync_assets_to_db(account)
        return Response({
            'success': result.get('success', False),
            'count': result.get('count', 0),
            'created': result.get('created', 0),
            'updated': result.get('updated', 0),
            'message': result.get('message', ''),
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
        }, status=500)
```

### 1.2 Test Frontend

**Frontend** : `frontend/src/services/brokers.ts`

```typescript
export const syncAssets = async (accountId: number) => {
  try {
    const response = await apiClient.post(`/broker-accounts/${accountId}/sync-assets/`);
    return {
      success: response.data.success,
      count: response.data.count,
      created: response.data.created,
      updated: response.data.updated,
      message: response.data.message,
    };
  } catch (error: any) {
    return {
      success: false,
      error: error.response?.data?.error || 'Sync failed',
    };
  }
};
```

### 1.3 Test Manuel

```typescript
// Tester la synchronisation des assets
const testSyncAssets = async () => {
  const accountId = 1; // ID du compte broker
  
  console.log('🔄 Starting asset sync...');
  const result = await syncAssets(accountId);
  
  if (result.success) {
    console.log(`✅ Sync successful:`);
    console.log(`   - Total: ${result.count}`);
    console.log(`   - Created: ${result.created}`);
    console.log(`   - Updated: ${result.updated}`);
  } else {
    console.error('❌ Sync failed:', result.error);
  }
};
```

### 1.4 Vérification dans la Base

**Backend** : Vérifier que les assets sont bien sauvegardés

```python
from apps.trading.models import AllAssets, Asset

# Vérifier les assets synchronisés
assets = AllAssets.objects.filter(broker_type='SAXO')
print(f"Total assets Saxo: {assets.count()}")

# Vérifier les assets enrichis
enriched = Asset.objects.filter(broker_type='SAXO')
print(f"Enriched assets: {enriched.count()}")
```

---

## 🧪 Test 2 : Synchronisation des Positions

### 2.1 Endpoint API

```python
@action(detail=True, methods=['post'], url_path='sync-positions')
def sync_positions(self, request, pk=None):
    """Synchroniser les positions depuis le broker"""
    account = self.get_object()
    service = BrokerService(request.user)
    
    try:
        result = service.sync_positions_to_db(account)
        return Response({
            'success': result.get('success', False),
            'count': result.get('count', 0),
            'created': result.get('created', 0),
            'updated': result.get('updated', 0),
            'closed': result.get('closed', 0),
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
        }, status=500)
```

### 2.2 Test Frontend

```typescript
export const syncPositions = async (accountId: number) => {
  try {
    const response = await apiClient.post(`/broker-accounts/${accountId}/sync-positions/`);
    return {
      success: response.data.success,
      count: response.data.count,
      created: response.data.created,
      updated: response.data.updated,
      closed: response.data.closed,
    };
  } catch (error: any) {
    return {
      success: false,
      error: error.response?.data?.error || 'Sync failed',
    };
  }
};
```

### 2.3 Test Manuel

```typescript
const testSyncPositions = async () => {
  console.log('🔄 Starting position sync...');
  const result = await syncPositions(1);
  
  if (result.success) {
    console.log(`✅ Sync successful:`);
    console.log(`   - Total: ${result.count}`);
    console.log(`   - Created: ${result.created}`);
    console.log(`   - Updated: ${result.updated}`);
    console.log(`   - Closed: ${result.closed}`);
  }
};
```

---

## 🧪 Test 3 : Synchronisation des Trades

### 3.1 Endpoint API

```python
@action(detail=True, methods=['post'], url_path='sync-trades')
def sync_trades(self, request, pk=None):
    """Synchroniser les trades depuis le broker"""
    account = self.get_object()
    service = BrokerService(request.user)
    
    start_date = request.data.get('start_date')
    end_date = request.data.get('end_date')
    
    try:
        result = service.sync_trades_to_db(
            account,
            start_date=start_date,
            end_date=end_date,
        )
        return Response({
            'success': result.get('success', False),
            'count': result.get('count', 0),
            'created': result.get('created', 0),
            'updated': result.get('updated', 0),
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
        }, status=500)
```

### 3.2 Test Frontend

```typescript
export const syncTrades = async (
  accountId: number,
  startDate?: string,
  endDate?: string
) => {
  try {
    const response = await apiClient.post(`/broker-accounts/${accountId}/sync-trades/`, {
      start_date: startDate,
      end_date: endDate,
    });
    return {
      success: response.data.success,
      count: response.data.count,
      created: response.data.created,
      updated: response.data.updated,
    };
  } catch (error: any) {
    return {
      success: false,
      error: error.response?.data?.error || 'Sync failed',
    };
  }
};
```

### 3.3 Test Manuel

```typescript
const testSyncTrades = async () => {
  const startDate = '2024-01-01';
  const endDate = '2024-01-31';
  
  console.log('🔄 Starting trade sync...');
  const result = await syncTrades(1, startDate, endDate);
  
  if (result.success) {
    console.log(`✅ Sync successful:`);
    console.log(`   - Total: ${result.count}`);
    console.log(`   - Created: ${result.created}`);
    console.log(`   - Updated: ${result.updated}`);
  }
};
```

---

## 🧪 Test 4 : Synchronisation des Prix

### 4.1 Endpoint API

```python
@action(detail=True, methods=['post'], url_path='sync-prices')
def sync_prices(self, request, pk=None):
    """Synchroniser les prix depuis le broker"""
    account = self.get_object()
    service = BrokerService(request.user)
    
    symbols = request.data.get('symbols', [])
    
    try:
        result = service.sync_prices_to_db(account, symbols=symbols)
        return Response({
            'success': result.get('success', False),
            'count': result.get('count', 0),
            'updated': result.get('updated', 0),
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
        }, status=500)
```

### 4.2 Test Frontend

```typescript
export const syncPrices = async (accountId: number, symbols?: string[]) => {
  try {
    const response = await apiClient.post(`/broker-accounts/${accountId}/sync-prices/`, {
      symbols: symbols || [],
    });
    return {
      success: response.data.success,
      count: response.data.count,
      updated: response.data.updated,
    };
  } catch (error: any) {
    return {
      success: false,
      error: error.response?.data?.error || 'Sync failed',
    };
  }
};
```

---

## 🧪 Test 5 : Synchronisation Complète

### 5.1 Endpoint API

```python
@action(detail=True, methods=['post'], url_path='sync-all')
def sync_all(self, request, pk=None):
    """Synchroniser toutes les données depuis le broker"""
    account = self.get_object()
    service = BrokerService(request.user)
    
    results = {}
    
    # Synchroniser les assets
    try:
        results['assets'] = service.sync_assets_to_db(account)
    except Exception as e:
        results['assets'] = {'success': False, 'error': str(e)}
    
    # Synchroniser les positions
    try:
        results['positions'] = service.sync_positions_to_db(account)
    except Exception as e:
        results['positions'] = {'success': False, 'error': str(e)}
    
    # Synchroniser les trades
    try:
        results['trades'] = service.sync_trades_to_db(account)
    except Exception as e:
        results['trades'] = {'success': False, 'error': str(e)}
    
    # Synchroniser les prix
    try:
        results['prices'] = service.sync_prices_to_db(account)
    except Exception as e:
        results['prices'] = {'success': False, 'error': str(e)}
    
    return Response({
        'success': True,
        'results': results,
    })
```

### 5.2 Test Frontend

```typescript
export const syncAll = async (accountId: number) => {
  try {
    const response = await apiClient.post(`/broker-accounts/${accountId}/sync-all/`);
    return {
      success: true,
      results: response.data.results,
    };
  } catch (error: any) {
    return {
      success: false,
      error: error.response?.data?.error || 'Sync failed',
    };
  }
};
```

### 5.3 Test Manuel

```typescript
const testSyncAll = async () => {
  console.log('🔄 Starting full sync...');
  const result = await syncAll(1);
  
  if (result.success) {
    console.log('✅ Full sync completed:');
    Object.entries(result.results).forEach(([type, data]: [string, any]) => {
      if (data.success) {
        console.log(`   ✅ ${type}: ${data.count || 0} items`);
      } else {
        console.log(`   ❌ ${type}: ${data.error}`);
      }
    });
  }
};
```

---

## 📊 Vérification des Logs

### 6.1 Vérifier les Logs de Synchronisation

**Backend** : Les logs sont stockés dans `BrokerSyncLog`

```python
from apps.trading.models.brokers import BrokerSyncLog

# Vérifier les logs récents
logs = BrokerSyncLog.objects.filter(
    broker_account_id=1
).order_by('-started_at')[:10]

for log in logs:
    print(f"{log.sync_type}: {log.status} - {log.records_synced} records")
    if log.error_message:
        print(f"  Error: {log.error_message}")
```

### 6.2 Endpoint API pour les Logs

```python
@action(detail=True, methods=['get'], url_path='sync-logs')
def sync_logs(self, request, pk=None):
    """Récupérer les logs de synchronisation"""
    account = self.get_object()
    
    logs = BrokerSyncLog.objects.filter(
        broker_account=account
    ).order_by('-started_at')[:50]
    
    return Response({
        'count': logs.count(),
        'logs': [
            {
                'sync_type': log.sync_type,
                'status': log.status,
                'records_synced': log.records_synced,
                'started_at': log.started_at,
                'completed_at': log.completed_at,
                'error_message': log.error_message,
            }
            for log in logs
        ],
    })
```

---

## ✅ Checklist de Validation

### Synchronisation des Assets

- [ ] Assets récupérés depuis le broker
- [ ] Assets sauvegardés dans `AllAssets`
- [ ] Assets enrichis dans `Asset` (si applicable)
- [ ] Logs de synchronisation créés
- [ ] Erreurs gérées correctement

### Synchronisation des Positions

- [ ] Positions récupérées depuis le broker
- [ ] Positions sauvegardées dans `Position`
- [ ] Positions fermées mises à jour
- [ ] Logs de synchronisation créés

### Synchronisation des Trades

- [ ] Trades récupérés depuis le broker
- [ ] Trades sauvegardés dans `Trade`
- [ ] Filtrage par date fonctionne
- [ ] Logs de synchronisation créés

### Synchronisation des Prix

- [ ] Prix récupérés depuis le broker
- [ ] Prix sauvegardés dans `AssetPrice`
- [ ] Mise à jour des prix existants
- [ ] Logs de synchronisation créés

### Synchronisation Complète

- [ ] Toutes les synchronisations fonctionnent
- [ ] Les erreurs partielles sont gérées
- [ ] Les résultats sont retournés correctement
- [ ] L'interface utilisateur affiche les résultats

---

## 🧪 Tests Automatisés

### Test avec Jest/Vitest

**Fichier** : `frontend/src/services/__tests__/sync.test.ts`

```typescript
import { describe, it, expect } from 'vitest';
import { syncAssets, syncPositions, syncTrades, syncAll } from '../brokers';

describe('Synchronizations', () => {
  it('should sync assets', async () => {
    const result = await syncAssets(1);
    expect(result).toHaveProperty('success');
  });

  it('should sync positions', async () => {
    const result = await syncPositions(1);
    expect(result).toHaveProperty('success');
  });

  it('should sync trades', async () => {
    const result = await syncTrades(1, '2024-01-01', '2024-01-31');
    expect(result).toHaveProperty('success');
  });

  it('should sync all', async () => {
    const result = await syncAll(1);
    expect(result.success).toBe(true);
    expect(result.results).toHaveProperty('assets');
    expect(result.results).toHaveProperty('positions');
  });
});
```

---

## 🐛 Dépannage

### Problème : "Sync failed - Authentication error"

**Solutions** :
1. Vérifier que le broker est authentifié
2. Vérifier que les tokens sont valides
3. Relancer l'authentification si nécessaire

### Problème : "No data returned"

**Solutions** :
1. Vérifier que le compte broker a des données
2. Vérifier les paramètres de requête
3. Vérifier les logs du broker

### Problème : "Database error"

**Solutions** :
1. Vérifier les migrations Django
2. Vérifier les contraintes de la base de données
3. Vérifier les logs Django

---

## 📚 Ressources

- **Guide de Synchronisation** : `docs/SYNC_MANAGEMENT_GUIDE.md`
- **Services de Sync** : `docs/phase_3/SERVICES_SYNC_EXPLANATION.md`
- **Gestion d'Erreurs** : `docs/phase_3/GESTION_ERREURS_EXPLANATION.md`

---

## 🎯 Résultat Attendu

Après validation :
- ✅ Toutes les synchronisations fonctionnent
- ✅ Les données sont sauvegardées correctement
- ✅ Les logs sont créés pour chaque synchronisation
- ✅ Les erreurs sont gérées et affichées
- ✅ L'interface utilisateur montre les résultats

