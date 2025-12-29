# Débogage - Conversion Balance Binance en EUR

## Problème identifié

Le solde Binance affiche **0.00 €** alors qu'il devrait afficher une valeur positive.

## Analyse des logs

### Erreur principale
```
[ERROR] [Binance] HTTP error: 400 - Timestamp for this request was 1000ms ahead of the server's time.
[INFO] Binance account 2: Raw balances received: {} (count: 0)
[INFO] Binance account 2: Balance conversion result: eur_balance=0
```

### Cause racine

L'erreur **"Timestamp for this request was 1000ms ahead of the server's time"** indique que :
1. Le timestamp envoyé à Binance est en avance de plus de 1000ms par rapport à l'horloge Binance
2. Binance rejette la requête avant qu'elle n'atteigne le serveur
3. Résultat : Les balances retournées sont vides `{}`
4. La conversion en EUR reçoit donc 0 balance → 0 EUR

## Flux de conversion

```
1. Frontend appelle: GET /api/broker-accounts/{id}/balance-eur/
   ↓
2. Backend (views.py balance_eur):
   - Récupère les balances via service.get_account_balance(account)
   - Pour Binance: appelle broker.get_account_balance()
   ↓
3. Binance Broker (binance.py):
   - _make_request('GET', '/api/v3/account', signed=True)
   - Calcule timestamp: int(time.time() * 1000)
   - Crée signature HMAC avec api_secret
   - Envoie requête à Binance
   ↓
4. Si erreur timestamp → Binance rejette → balances = {}
   ↓
5. Backend reçoit balances vides → conversion → 0 EUR
```

## Solutions appliquées

### Solution 1: Synchronisation avec le serveur Binance (à implémenter)

Au lieu d'utiliser l'horloge locale (`time.time()`), utiliser le serveur time de Binance pour synchroniser.

**Méthode recommandée:**
1. Appeler `/api/v3/time` avant chaque requête signée
2. Calculer l'offset entre l'horloge locale et Binance
3. Appliquer cet offset au timestamp

### Solution 2: Utiliser le serveur time directement

Pour les requêtes signées, utiliser le temps Binance + un petit délai local.

### Solution 3: Réduire le timestamp (fallback)

Si l'horloge locale est en avance, réduire le timestamp de 500-1000ms.

## Fichiers modifiés

### 1. `backend/apps/trading/utils/binance_balance_converter.py`
- **Rôle**: Convertit les balances crypto en EUR
- **Améliorations**:
  - Logging détaillé de chaque conversion
  - Support des stablecoins (USDC, BUSD, DAI, etc.)
  - Gestion des erreurs de conversion de types
  - Fallback vers taux par défaut si API échoue

### 2. `backend/apps/trading/api/views.py` (balance_eur endpoint)
- **Rôle**: Endpoint API pour récupérer le solde EUR
- **Améliorations**:
  - Logging des balances brutes reçues
  - Logging de l'état d'authentification
  - Warning si solde EUR = 0 alors qu'on a des balances non-zéro

### 3. `backend/apps/trading/brokers/binance.py` (à corriger)
- **Problème**: Timestamp calculé avec `time.time()` local
- **Solution**: Synchroniser avec `/api/v3/time` de Binance

## Étapes de débogage

### Étape 1: Vérifier l'horloge système
```bash
# Vérifier que l'horloge système est correcte
date  # Linux/Mac
# ou
w32tm /query /status  # Windows
```

### Étape 2: Tester la synchronisation Binance
```python
# Test manuel dans Django shell
from apps.trading.brokers.binance import BinanceBroker
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()
broker = BinanceBroker(user, {
    'api_key': 'xxx',
    'api_secret': 'xxx',
    'testnet': True
})

# Tester le serveur time
response = broker._make_request('GET', '/api/v3/time', signed=False)
print(f"Binance server time: {response.get('serverTime')}")
print(f"Local time (ms): {int(time.time() * 1000)}")
print(f"Différence: {int(time.time() * 1000) - response.get('serverTime')} ms")
```

### Étape 3: Vérifier les credentials
- Vérifier que `api_key` et `api_secret` sont corrects
- Vérifier que `testnet` est correct (True/False)
- Vérifier les permissions de l'API key (lecture des balances autorisée)

### Étape 4: Tester l'endpoint directement
```bash
# Tester l'endpoint balance-eur
curl -X GET http://localhost:8000/api/broker-accounts/2/balance-eur/ \
  -H "Authorization: Bearer <token>"
```

## Logs attendus (après corrections)

```
[INFO] Getting balance for account 2 (type: BINANCE)
[INFO] Creating broker instance: binance for user 1
[INFO] Binance account 2: Raw balances received: {'BTC': Decimal('0.001'), 'USDT': Decimal('100')} (count: 2)
[INFO] Starting conversion of 2 assets: ['BTC', 'USDT']
[INFO] [BTC] 0.001 → 95.00 EUR (API direct BTCEUR = 95000)
[INFO] [USDT] 100 → 92.00 EUR (API via USDT (USDTUSDT=1, USDTEUR=0.92))
[INFO] Conversion complete: total EUR = 187.00
[INFO] Binance account 2: Balance conversion result: eur_balance=187.00
```

## Code de correction à implémenter

### Dans `binance.py` - Méthode `_make_request`:

```python
def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, signed: bool = False):
    # ... code existant ...
    
    if signed:
        # Synchroniser avec le serveur Binance
        try:
            server_time_response = self._make_request('GET', '/api/v3/time', signed=False)
            server_time = server_time_response.get('serverTime', int(time.time() * 1000))
            params['timestamp'] = server_time
        except Exception as e:
            # Fallback: utiliser time local - 1000ms pour compenser
            logger.warning(f"Could not get Binance server time, using local time - offset: {e}")
            params['timestamp'] = int(time.time() * 1000) - 1000
```

## Tests à effectuer

1. **Test de synchronisation horloge**
   - Vérifier que l'offset entre local et Binance < 1000ms
   - Si > 1000ms, corriger l'horloge système

2. **Test de récupération des balances**
   - Vérifier que `get_account_balance()` retourne des balances non-vides
   - Vérifier que les balances contiennent les assets attendus

3. **Test de conversion**
   - Vérifier que chaque asset est converti correctement
   - Vérifier que le total EUR est correct

4. **Test frontend**
   - Vérifier que le solde s'affiche correctement
   - Vérifier que le refresh fonctionne
   - Vérifier que le solde ne repasse pas à 0 après refresh

## Prochaines étapes

1. ✅ Améliorer le logging (fait)
2. ✅ Support stablecoins (fait)
3. ⏳ Corriger la synchronisation timestamp Binance (à faire)
4. ⏳ Tester avec un compte Binance réel/testnet
5. ⏳ Vérifier que le solde reste stable après refresh

