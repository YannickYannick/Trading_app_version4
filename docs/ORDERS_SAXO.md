# Implémentation Saxo - Système d'ordres

## Introduction

Ce document décrit l'implémentation du placement d'ordres pour Saxo Bank dans le système de trading. Saxo Bank est un courtier qui supporte le trading d'actions, de devises, de matières premières et d'autres instruments financiers via son API OpenAPI.

## Architecture

### Méthode place_order

Fichier : `backend/apps/trading/brokers/saxo.py` (lignes 1300-1394)

La méthode `place_order` implémente l'interface `BrokerBase.place_order()` pour Saxo Bank.

### Signature

```python
def place_order(
    self, 
    symbol: str, 
    side: str, 
    quantity: Decimal, 
    price: Optional[Decimal] = None,
    order_type: str = None,
    uic: int = None,
    asset_type: str = "Stock",
    **kwargs
) -> OrderResult:
```

### Paramètres

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `symbol` | str | ✅ | Symbole de l'instrument (ex: "AAPL") |
| `side` | str | ✅ | "buy" ou "sell" (lowercase) |
| `quantity` | Decimal | ✅ | Quantité à acheter/vendre |
| `price` | Decimal | ❌ | Prix limite (requis pour Limit et StopLimit) |
| `order_type` | str | ❌ | Type d'ordre (si None, déduit de price) |
| `uic` | int | ❌ | UIC Saxo (si None, recherché automatiquement) |
| `asset_type` | str | ❌ | Type d'asset (défaut: "Stock") |
| `duration` | str | ❌ | Durée de l'ordre (défaut: "DayOrder") |

## Types d'ordres supportés

### Mapping des types d'ordres

| Type interne | Type Saxo | Description |
|--------------|-----------|-------------|
| `MARKET` | `Market` | Ordre au marché |
| `LIMIT` | `Limit` | Ordre à cours limité |
| `STOP` | `Stop` | Ordre stop |
| `STOP_LIMIT` | `StopLimit` | Ordre stop limité |

### Détection automatique du type

Si `order_type` n'est pas fourni, il est déduit automatiquement :

```python
if order_type is None:
    order_type = 'Limit' if price else 'Market'
```

### MARKET Order

**Paramètres requis :**
- `symbol`
- `side`
- `quantity`

**Exemple de requête :**
```python
result = saxo_broker.place_order(
    symbol="AAPL",
    side="buy",
    quantity=Decimal('10'),
    asset_type="Stock"
)
```

**Données envoyées à Saxo :**
```json
{
    "Uic": 25263,
    "AssetType": "Stock",
    "Amount": 10.0,
    "BuySell": "Buy",
    "OrderType": "Market",
    "AccountKey": "CON123456",
    "OrderDuration": {
        "DurationType": "DayOrder"
    }
}
```

### LIMIT Order

**Paramètres requis :**
- `symbol`
- `side`
- `quantity`
- `price`

**Exemple de requête :**
```python
result = saxo_broker.place_order(
    symbol="AAPL",
    side="buy",
    quantity=Decimal('10'),
    price=Decimal('150.25'),
    asset_type="Stock"
)
```

**Données envoyées à Saxo :**
```json
{
    "Uic": 25263,
    "AssetType": "Stock",
    "Amount": 10.0,
    "BuySell": "Buy",
    "OrderType": "Limit",
    "OrderPrice": 150.25,
    "AccountKey": "CON123456",
    "OrderDuration": {
        "DurationType": "DayOrder"
    }
}
```

### STOP Order

**Paramètres requis :**
- `symbol`
- `side`
- `quantity`
- `stop_price` (passé via `**kwargs` ou prix limite)

**Exemple de requête :**
```python
result = saxo_broker.place_order(
    symbol="AAPL",
    side="sell",
    quantity=Decimal('10'),
    order_type="Stop",
    price=Decimal('145.00'),  # Prix stop
    asset_type="Stock"
)
```

### STOP_LIMIT Order

**Paramètres requis :**
- `symbol`
- `side`
- `quantity`
- `price` (prix limite)
- `stop_price` (passé via `**kwargs`)

**Exemple de requête :**
```python
result = saxo_broker.place_order(
    symbol="AAPL",
    side="sell",
    quantity=Decimal('10'),
    order_type="StopLimit",
    price=Decimal('145.50'),  # Prix limite
    stop_price=Decimal('145.00'),  # Prix stop
    asset_type="Stock"
)
```

**Note :** Pour StopLimit, le système utilise à la fois `price` (OrderPrice) et `stop_price` (StopPrice) dans les données envoyées.

## Récupération de l'UIC

### Méthode _get_uic_from_symbol

L'UIC (Unique Instrument Code) est un identifiant unique utilisé par Saxo pour chaque instrument. Il est automatiquement recherché si non fourni :

```python
if uic is None:
    uic = self._get_uic_from_symbol(symbol, asset_type)
    if uic is None:
        return OrderResult(
            success=False,
            error_message=f"Could not find UIC for {symbol}"
        )
```

### Processus de recherche

1. Recherche dans `AllAssets` avec le symbole et le type
2. Extraction de l'UIC depuis `broker_id` ou `asset_identifier`
3. Fallback sur recherche directe via l'API Saxo si non trouvé

**Exemple :**
```python
# Recherche UIC pour AAPL (Stock)
uic = saxo_broker._get_uic_from_symbol("AAPL", "Stock")
# Retourne : 25263
```

## Mapping des types d'assets

### ASSET_TYPE_MAPPING

Saxo utilise des noms spécifiques pour les types d'assets. Le système effectue un mapping :

```python
ASSET_TYPE_MAPPING = {
    'stock': 'Stock',
    'equity': 'Stock',
    'fx': 'FxSpot',
    'forex': 'FxSpot',
    'crypto': 'CfdOnStock',
    # ... autres mappings
}
```

**Utilisation :**
```python
saxo_asset_type = self.ASSET_TYPE_MAPPING.get(
    asset_type.lower(), 
    asset_type
)
```

### Types d'assets supportés

- `Stock` : Actions
- `FxSpot` : Forex (paires de devises)
- `CfdOnStock` : CFD sur actions
- `Future` : Futures
- `Option` : Options
- `Bond` : Obligations

## Structure des données d'ordre

### Données requises minimales

```json
{
    "Uic": 25263,
    "AssetType": "Stock",
    "Amount": 10.0,
    "BuySell": "Buy",
    "OrderType": "Market"
}
```

### Données complètes (avec compte et durée)

```json
{
    "Uic": 25263,
    "AssetType": "Stock",
    "Amount": 10.0,
    "BuySell": "Buy",
    "OrderType": "Limit",
    "OrderPrice": 150.25,
    "AccountKey": "CON123456",
    "OrderDuration": {
        "DurationType": "DayOrder"
    }
}
```

### Champs expliqués

| Champ | Type | Description |
|-------|------|-------------|
| `Uic` | int | Identifiant unique de l'instrument |
| `AssetType` | string | Type d'asset (Stock, FxSpot, etc.) |
| `Amount` | float | Quantité |
| `BuySell` | string | "Buy" ou "Sell" |
| `OrderType` | string | Type d'ordre (Market, Limit, Stop, StopLimit) |
| `OrderPrice` | float | Prix limite (optionnel) |
| `AccountKey` | string | Clé du compte (si disponible) |
| `OrderDuration` | object | Durée de validité de l'ordre |

### Durées d'ordre (OrderDuration)

| Durée | Description |
|-------|-------------|
| `DayOrder` | Valide jusqu'à la fin de la journée de trading |
| `GoodTillCancel` | Valide jusqu'à annulation |
| `GoodTillDate` | Valide jusqu'à une date spécifique |
| `ImmediateOrCancel` | Exécution immédiate ou annulation |
| `FillOrKill` | Exécution complète ou annulation |

**Exemple avec durée personnalisée :**
```python
result = saxo_broker.place_order(
    symbol="AAPL",
    side="buy",
    quantity=Decimal('10'),
    price=Decimal('150.25'),
    duration="GoodTillCancel",  # Via kwargs
    asset_type="Stock"
)
```

## Authentification

### OAuth2 Bearer Token

Saxo utilise l'authentification OAuth2 avec Bearer token. Le token est automatiquement géré par `_make_request()` :

```python
headers = {
    "Authorization": f"Bearer {self.access_token}",
    "Content-Type": "application/json"
}
```

### Gestion du token

- Le token est stocké dans `self.access_token`
- Renouvellement automatique si expiré
- Vérification de validité avant chaque requête

## Réponse de l'API Saxo

### Réponse réussie

```json
{
    "OrderId": "12345678",
    "Status": "Submitted",
    "StatusMessage": "Order submitted successfully",
    "Orders": [
        {
            "OrderId": "12345678",
            "Uic": 25263,
            "Amount": 10.0,
            "BuySell": "Buy",
            "OrderType": "Limit",
            "OrderPrice": 150.25,
            "Status": "Submitted"
        }
    ]
}
```

### Mapping vers OrderResult

```python
OrderResult(
    success=True,
    order_id=str(order_id) if order_id else None,
    broker_order_id=str(order_id) if order_id else None,
    status=data.get('Status', 'Submitted'),
    filled_quantity=Decimal('0'),
    raw_data=data
)
```

### Statuts Saxo

| Statut Saxo | Description | Mapping interne |
|-------------|-------------|-----------------|
| `Submitted` | Ordre soumis | `PENDING` / `OPEN` |
| `Accepted` | Ordre accepté | `OPEN` |
| `PartiallyFilled` | Partiellement exécuté | `PARTIALLY_FILLED` |
| `Filled` | Complètement exécuté | `FILLED` |
| `Cancelled` | Annulé | `CANCELLED` |
| `Rejected` | Rejeté | `REJECTED` |
| `Expired` | Expiré | `EXPIRED` |

## Gestion des erreurs

### Erreur UIC non trouvé

```python
if uic is None:
    return OrderResult(
        success=False,
        error_message=f"Could not find UIC for {symbol}"
    )
```

**Causes possibles :**
- Symbole incorrect
- Type d'asset incorrect
- Instrument non disponible sur Saxo

### Erreurs API Saxo

Les erreurs Saxo sont capturées et retournées dans `OrderResult.error_message` :

```python
except BrokerError as e:
    logger.error(f"Saxo place_order broker error: {e}")
    return OrderResult(
        success=False,
        error_message=str(e)
    )
```

### Codes d'erreur Saxo courants

| Code HTTP | Message | Cause |
|-----------|---------|-------|
| 401 | Unauthorized | Token expiré ou invalide |
| 403 | Forbidden | Pas de permission pour cet instrument |
| 400 | Bad Request | Paramètres invalides (UIC, quantité, prix) |
| 404 | Not Found | UIC non trouvé |
| 500 | Internal Server Error | Erreur serveur Saxo |

### Erreurs spécifiques

- **NoAccess** : Pas d'accès aux données de marché pour cet instrument
- **InsufficientFunds** : Fonds insuffisants
- **InvalidUIC** : UIC invalide ou introuvable

## Exemples d'utilisation

### Placement d'un ordre MARKET simple

```python
from apps.trading.services.broker_service import BrokerService
from apps.trading.models import BrokerAccount
from decimal import Decimal

service = BrokerService(user)
broker_account = BrokerAccount.objects.get(user=user, broker_type='SAXO')

result = service.place_order(
    broker_account=broker_account,
    symbol="AAPL",
    side="buy",
    quantity=Decimal('10'),
    order_type="MARKET",
    asset_type="Stock"
)

if result.success:
    print(f"Order placed: {result.order_id}")
else:
    print(f"Error: {result.error_message}")
```

### Placement d'un ordre LIMIT avec gestion d'erreur

```python
result = service.place_order(
    broker_account=broker_account,
    symbol="AAPL",
    side="buy",
    quantity=Decimal('10'),
    order_type="LIMIT",
    price=Decimal('150.25'),
    asset_type="Stock"
)

if result.success:
    print(f"✅ Limit order placed: {result.order_id}")
    print(f"Status: {result.status}")
else:
    print(f"❌ Error: {result.error_message}")
    # Gérer l'erreur selon le type
    if "UIC" in result.error_message:
        print("Symbole introuvable, vérifier le nom et le type d'asset")
    elif "insufficient" in result.error_message.lower():
        print("Fonds insuffisants")
```

### Ordre sur Forex (FxSpot)

```python
result = service.place_order(
    broker_account=broker_account,
    symbol="EURUSD",
    side="buy",
    quantity=Decimal('1000'),  # Montant en devise de base
    order_type="MARKET",
    asset_type="FxSpot"  # ou "forex"
)
```

### Ordre avec durée personnalisée

```python
result = service.place_order(
    broker_account=broker_account,
    symbol="AAPL",
    side="buy",
    quantity=Decimal('10'),
    price=Decimal('150.25'),
    order_type="LIMIT",
    asset_type="Stock",
    duration="GoodTillCancel"  # Via kwargs
)
```

## Méthodes associées

### cancel_order

```python
def cancel_order(self, order_id: str, **kwargs) -> bool:
    """Annuler un ordre"""
```

**Exemple :**
```python
success = saxo_broker.cancel_order(order_id="12345678")
if success:
    print("Order cancelled")
```

### modify_order

```python
def modify_order(
    self, 
    order_id: str, 
    quantity: Decimal = None, 
    price: Decimal = None,
    **kwargs
) -> bool:
    """Modifier un ordre existant"""
```

**Exemple :**
```python
success = saxo_broker.modify_order(
    order_id="12345678",
    price=Decimal('151.00')  # Nouveau prix
)
```

## Limitations et particularités

### UIC requis

- Chaque instrument doit avoir un UIC valide
- L'UIC est unique pour chaque instrument chez Saxo
- Si non fourni, le système tente de le rechercher automatiquement

### AccountKey

- Si disponible, `AccountKey` est automatiquement ajouté aux requêtes
- Permet de spécifier le compte à utiliser (utile pour comptes multiples)

### Types d'assets

- Les types d'assets doivent correspondre à ceux supportés par Saxo
- Le mapping automatique facilite l'utilisation de noms génériques

### Précision des prix

- Les prix doivent respecter la précision du marché
- Utiliser `Decimal` pour éviter les erreurs d'arrondi

### Durée des ordres

- Par défaut : `DayOrder` (valide jusqu'à la fin du jour de trading)
- Peut être modifiée via le paramètre `duration`

## Fichiers de référence

- **Implémentation** : `backend/apps/trading/brokers/saxo.py` (lignes 1300-1394)
- **Interface** : `backend/apps/trading/brokers/base.py` (méthode `place_order`)
- **Récupération UIC** : `backend/apps/trading/brokers/saxo.py` (méthode `_get_uic_from_symbol`, lignes 1588-1621)
- **Documentation Saxo OpenAPI** : https://www.developer.saxo/openapi/learn

## Notes importantes

1. **Side** : Utiliser "buy" ou "sell" en lowercase (contrairement à Binance qui utilise "BUY"/"SELL")
2. **UIC** : Toujours vérifier que l'UIC existe avant de placer un ordre
3. **AssetType** : Utiliser les types Saxo standardisés (Stock, FxSpot, etc.)
4. **AccountKey** : Ajouté automatiquement si disponible dans les credentials
5. **Durée** : Par défaut `DayOrder`, spécifier explicitement pour d'autres durées
6. **Token** : Le token OAuth2 doit être valide et non expiré








