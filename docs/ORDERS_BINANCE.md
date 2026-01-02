# Implémentation Binance - Système d'ordres

## Introduction

Ce document décrit l'implémentation du placement d'ordres pour Binance dans le système de trading. Binance est un exchange de cryptomonnaies qui supporte le trading spot via son API REST.

## Architecture

### Méthode place_order

Fichier : `backend/apps/trading/brokers/binance.py` (lignes 719-792)

La méthode `place_order` implémente l'interface `BrokerBase.place_order()` pour Binance.

### Signature

```python
def place_order(
    self,
    symbol: str,
    side: str,
    quantity: Decimal,
    order_type: str = 'MARKET',
    price: Optional[Decimal] = None,
    stop_price: Optional[Decimal] = None,
    time_in_force: str = 'GTC',
    **kwargs
) -> OrderResult:
```

### Paramètres

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `symbol` | str | ✅ | Symbole de la paire (ex: "BTCUSDT") |
| `side` | str | ✅ | "BUY" ou "SELL" |
| `quantity` | Decimal | ✅ | Quantité à acheter/vendre |
| `order_type` | str | ❌ | "MARKET", "LIMIT", "STOP", "STOP_LIMIT" (défaut: "MARKET") |
| `price` | Decimal | ❌ | Prix limite (requis pour LIMIT et STOP_LIMIT) |
| `stop_price` | Decimal | ❌ | Prix stop (requis pour STOP et STOP_LIMIT) |
| `time_in_force` | str | ❌ | Durée de validité (défaut: "GTC" - Good Till Cancel) |

## Types d'ordres supportés

### Mapping des types d'ordres

| Type interne | Type Binance | Description |
|--------------|--------------|-------------|
| `MARKET` | `MARKET` | Ordre au marché |
| `LIMIT` | `LIMIT` | Ordre à cours limité |
| `STOP` | `STOP_LOSS` | Ordre stop loss |
| `STOP_LIMIT` | `STOP_LOSS_LIMIT` | Ordre stop loss limité |

### MARKET Order

**Paramètres requis :**
- `symbol`
- `side`
- `quantity`

**Exemple de requête :**
```python
result = binance_broker.place_order(
    symbol="BTCUSDT",
    side="BUY",
    quantity=Decimal('0.001'),
    order_type="MARKET"
)
```

**Paramètres Binance envoyés :**
```json
{
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "MARKET",
    "quantity": "0.001"
}
```

### LIMIT Order

**Paramètres requis :**
- `symbol`
- `side`
- `quantity`
- `price`
- `time_in_force` (optionnel, défaut: "GTC")

**Exemple de requête :**
```python
result = binance_broker.place_order(
    symbol="BTCUSDT",
    side="BUY",
    quantity=Decimal('0.001'),
    order_type="LIMIT",
    price=Decimal('50000.00'),
    time_in_force="GTC"
)
```

**Paramètres Binance envoyés :**
```json
{
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "LIMIT",
    "quantity": "0.001",
    "price": "50000.00",
    "timeInForce": "GTC"
}
```

**Options timeInForce :**
- `GTC` : Good Till Cancel (valide jusqu'à annulation)
- `IOC` : Immediate Or Cancel (exécution immédiate ou annulation)
- `FOK` : Fill Or Kill (exécution complète ou annulation)

### STOP Order (Stop Loss)

**Paramètres requis :**
- `symbol`
- `side`
- `quantity`
- `stop_price`

**Exemple de requête :**
```python
result = binance_broker.place_order(
    symbol="BTCUSDT",
    side="SELL",
    quantity=Decimal('0.001'),
    order_type="STOP",
    stop_price=Decimal('48000.00')
)
```

**Paramètres Binance envoyés :**
```json
{
    "symbol": "BTCUSDT",
    "side": "SELL",
    "type": "STOP_LOSS",
    "quantity": "0.001",
    "stopPrice": "48000.00"
}
```

**Note :** Binance mappe automatiquement `STOP` en `STOP_LOSS` dans le code.

### STOP_LIMIT Order

**Paramètres requis :**
- `symbol`
- `side`
- `quantity`
- `price` (prix limite)
- `stop_price` (prix stop)
- `time_in_force` (optionnel)

**Exemple de requête :**
```python
result = binance_broker.place_order(
    symbol="BTCUSDT",
    side="SELL",
    quantity=Decimal('0.001'),
    order_type="STOP_LIMIT",
    price=Decimal('47900.00'),
    stop_price=Decimal('48000.00'),
    time_in_force="GTC"
)
```

**Paramètres Binance envoyés :**
```json
{
    "symbol": "BTCUSDT",
    "side": "SELL",
    "type": "STOP_LOSS_LIMIT",
    "quantity": "0.001",
    "price": "47900.00",
    "stopPrice": "48000.00",
    "timeInForce": "GTC"
}
```

## Authentification

### HMAC SHA256

Binance utilise l'authentification HMAC SHA256 pour les requêtes signées. La méthode `_make_request()` avec `signed=True` gère automatiquement :

1. Ajout du timestamp
2. Calcul de la signature HMAC
3. Ajout des en-têtes requis

**Exemple d'en-têtes générés :**
```
X-MBX-APIKEY: <api_key>
Content-Type: application/json
```

**Signature calculée :**
```python
query_string = urlencode(sorted(params.items()))
signature = hmac.new(
    api_secret.encode('utf-8'),
    query_string.encode('utf-8'),
    hashlib.sha256
).hexdigest()
```

## Réponse de l'API Binance

### Réponse réussie

```json
{
    "symbol": "BTCUSDT",
    "orderId": 123456789,
    "orderListId": -1,
    "clientOrderId": "xxxxx",
    "transactTime": 1612345678901,
    "price": "50000.00",
    "origQty": "0.001",
    "executedQty": "0.000",
    "cummulativeQuoteQty": "0.000",
    "status": "NEW",
    "timeInForce": "GTC",
    "type": "LIMIT",
    "side": "BUY"
}
```

### Mapping vers OrderResult

```python
OrderResult(
    success=True,
    order_id=str(response.get('orderId', '')),
    message=f"Order placed: {response.get('status', 'UNKNOWN')}",
    raw_data=response
)
```

### Statuts Binance

| Statut Binance | Description | Mapping interne |
|----------------|-------------|-----------------|
| `NEW` | Ordre créé | `PENDING` / `OPEN` |
| `PARTIALLY_FILLED` | Partiellement exécuté | `PARTIALLY_FILLED` |
| `FILLED` | Complètement exécuté | `FILLED` |
| `CANCELED` | Annulé | `CANCELLED` |
| `PENDING_CANCEL` | En attente d'annulation | `OPEN` |
| `REJECTED` | Rejeté | `REJECTED` |
| `EXPIRED` | Expiré | `EXPIRED` |

## Gestion des erreurs

### Erreurs d'authentification

```python
if not self._ensure_authenticated():
    return OrderResult(
        success=False,
        error="Not authenticated"
    )
```

**Causes possibles :**
- API key invalide
- Secret manquant
- Token expiré

### Erreurs de validation

```python
if order_type.upper() == 'LIMIT' and not price:
    return OrderResult(
        success=False,
        error="Limit orders require a price"
    )
```

### Erreurs API Binance

Les erreurs Binance sont capturées et retournées dans `OrderResult.error` :

```python
# Exemple d'erreur Binance
{
    "code": -1013,
    "msg": "Filter failure: LOT_SIZE"
}

# Retourné comme
OrderResult(
    success=False,
    error="Filter failure: LOT_SIZE"
)
```

### Codes d'erreur Binance courants

| Code | Message | Cause |
|------|---------|-------|
| -1013 | Filter failure | Quantité/prix ne respecte pas les filtres du symbole |
| -2010 | NEW_ORDER_REJECTED | Ordre rejeté (fond insuffisants, etc.) |
| -1021 | Timestamp for this request is outside of the recvWindow | Timestamp incorrect |
| -1121 | Invalid symbol | Symbole invalide |
| -1100 | Illegal characters | Paramètres invalides |

## Exemples d'utilisation

### Placement d'un ordre MARKET simple

```python
from apps.trading.services.broker_service import BrokerService
from apps.trading.models import BrokerAccount
from decimal import Decimal

service = BrokerService(user)
broker_account = BrokerAccount.objects.get(user=user, broker_type='BINANCE')

result = service.place_order(
    broker_account=broker_account,
    symbol="BTCUSDT",
    side="BUY",
    quantity=Decimal('0.001'),
    order_type="MARKET"
)

if result.success:
    print(f"Order placed: {result.order_id}")
else:
    print(f"Error: {result.error}")
```

### Placement d'un ordre LIMIT avec gestion d'erreur

```python
result = service.place_order(
    broker_account=broker_account,
    symbol="ETHUSDT",
    side="SELL",
    quantity=Decimal('1.5'),
    order_type="LIMIT",
    price=Decimal('3500.00'),
    time_in_force="GTC"
)

if result.success:
    print(f"✅ Limit order placed: {result.order_id}")
    print(f"Status: {result.message}")
else:
    print(f"❌ Error: {result.error}")
    # Gérer l'erreur selon le type
    if "insufficient" in result.error.lower():
        print("Fonds insuffisants")
    elif "LOT_SIZE" in result.error:
        print("Quantité invalide (vérifier les filtres du symbole)")
```

## Limitations et particularités

### Limites de quantité

Binance applique des filtres sur chaque symbole :
- **LOT_SIZE** : Quantité min/max et précision
- **PRICE_FILTER** : Prix min/max et précision
- **MIN_NOTIONAL** : Valeur minimale de l'ordre

**Exemple pour BTCUSDT :**
- Quantité min : 0.00001 BTC
- Quantité max : 9000 BTC
- Prix min : 0.01 USDT
- Prix max : 1000000 USDT
- Valeur min : 10 USDT

### Précision des décimales

- Les quantités doivent respecter la précision du symbole
- Les prix doivent respecter le tick size
- Utiliser `Decimal` pour éviter les erreurs d'arrondi

### Rate Limits

Binance limite les requêtes :
- **Order placement** : 10 requêtes/seconde/IP
- **Ordres** : 40 requêtes/seconde/IP

Le système doit implémenter un rate limiting pour éviter les erreurs `429 Too Many Requests`.

### Testnet

Binance fournit un testnet pour les tests :
- **Testnet URL** : `https://testnet.binance.vision`
- **Testnet API Key** : Créer depuis le site testnet

## Méthode cancel_order

### Signature

```python
def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> OrderResult:
```

### Exemple

```python
result = binance_broker.cancel_order(
    order_id="123456789",
    symbol="BTCUSDT"
)

if result.success:
    print(f"Order {order_id} cancelled")
```

## Fichiers de référence

- **Implémentation** : `backend/apps/trading/brokers/binance.py` (lignes 719-792)
- **Interface** : `backend/apps/trading/brokers/base.py` (méthode `place_order`)
- **Documentation Binance** : https://binance-docs.github.io/apidocs/spot/en/#new-order-trade

## Notes importantes

1. **Symboles** : Toujours en majuscules (ex: "BTCUSDT", pas "btcusdt")
2. **Quantités** : Utiliser `Decimal` pour la précision
3. **Signatures** : Les requêtes de placement d'ordre doivent être signées (`signed=True`)
4. **Testnet** : Utiliser le testnet pour les développements/tests
5. **Rate Limits** : Respecter les limites de requêtes pour éviter les bannissements








