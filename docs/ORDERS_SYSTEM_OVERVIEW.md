# Vue d'ensemble du système d'ordres

## Introduction

Le système d'ordres permet de placer, suivre et gérer des ordres de trading à travers différents brokers (Binance, Saxo Bank) via une interface unifiée. Ce document présente l'architecture générale, les flux de données et les concepts clés du système.

## Architecture générale

Le système d'ordres suit une architecture en couches avec séparation des responsabilités :

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND / API                            │
│              (REST API Endpoints)                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                  API VIEWSETS                                │
│              (OrderViewSet)                                  │
│  • CRUD operations                                          │
│  • Custom actions (pending, filled, cancel)                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   SERVICES                                   │
│            (BrokerService)                                   │
│  • Unified order placement                                  │
│  • Broker instance management                               │
│  • Error handling & logging                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   BROKERS                                    │
│    ┌──────────────┐          ┌──────────────┐              │
│    │  Binance     │          │    Saxo      │              │
│    │  Broker      │          │    Broker    │              │
│    └──────────────┘          └──────────────┘              │
│         │                           │                       │
│         └───────────┬───────────────┘                       │
│                     │                                       │
│              BrokerBase (Abstract)                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                  DATABASE                                    │
│              (Order Model)                                   │
│  • Order storage                                            │
│  • Status tracking                                          │
└─────────────────────────────────────────────────────────────┘
```

## Flux de données

### Flux de placement d'ordre

```mermaid
sequenceDiagram
    participant Client as Client/API
    participant ViewSet as OrderViewSet
    participant Service as BrokerService
    participant Broker as BrokerInstance
    participant DB as Database
    participant BrokerAPI as Broker API

    Client->>ViewSet: POST /api/orders/
    ViewSet->>Service: place_order(broker_account, symbol, ...)
    Service->>Broker: authenticate()
    Broker->>BrokerAPI: Authenticate request
    BrokerAPI-->>Broker: Authentication token
    Service->>Broker: place_order(symbol, side, quantity, ...)
    Broker->>BrokerAPI: POST /order (signed request)
    BrokerAPI-->>Broker: OrderResult (order_id, status)
    Broker-->>Service: OrderResult
    Service->>Service: Log order placement
    Service->>DB: Save order log (BrokerSyncLog)
    Service-->>ViewSet: OrderResult
    ViewSet->>DB: Save Order (optional)
    ViewSet-->>Client: OrderResponse with status
```

### Flux de synchronisation des ordres

```mermaid
sequenceDiagram
    participant Client as Client
    participant ViewSet as OrderViewSet
    participant Service as BrokerService
    participant Broker as BrokerInstance
    participant BrokerAPI as Broker API
    participant DB as Database

    Client->>ViewSet: GET /api/orders/pending/
    ViewSet->>Service: get_orders(broker_account, status='OPEN')
    Service->>Broker: authenticate()
    Broker->>BrokerAPI: Authenticate
    BrokerAPI-->>Broker: Token
    Service->>Broker: get_orders(status='OPEN')
    Broker->>BrokerAPI: GET /orders
    BrokerAPI-->>Broker: List of BrokerOrder
    Broker-->>Service: List[BrokerOrder]
    Service->>DB: Update Order status
    Service-->>ViewSet: List[BrokerOrder]
    ViewSet->>DB: Query Order model
    ViewSet-->>Client: Serialized orders
```

### Flux d'annulation d'ordre

```mermaid
sequenceDiagram
    participant Client as Client
    participant ViewSet as OrderViewSet
    participant Service as BrokerService
    participant Broker as BrokerInstance
    participant BrokerAPI as Broker API
    participant DB as Database

    Client->>ViewSet: POST /api/orders/{id}/cancel/
    ViewSet->>DB: Get Order by id
    DB-->>ViewSet: Order instance
    ViewSet->>ViewSet: Validate status (can cancel?)
    ViewSet->>Broker: cancel_order(order_id)
    Broker->>BrokerAPI: DELETE /orders/{order_id}
    BrokerAPI-->>Broker: Success/Error
    Broker-->>ViewSet: OrderResult
    ViewSet->>DB: Update Order.status = 'CANCELLED'
    ViewSet-->>Client: Cancel confirmation
```

## Types d'ordres supportés

Le système supporte quatre types d'ordres standardisés :

### 1. MARKET (Ordre au marché)
- **Description** : Ordre exécuté immédiatement au meilleur prix disponible
- **Paramètres requis** : `symbol`, `side`, `quantity`
- **Prix** : Déterminé par le marché au moment de l'exécution
- **Support** : Binance ✅, Saxo ✅

### 2. LIMIT (Ordre à cours limité)
- **Description** : Ordre exécuté uniquement si le prix atteint le niveau spécifié
- **Paramètres requis** : `symbol`, `side`, `quantity`, `price`
- **Prix** : Prix limite spécifié par l'utilisateur
- **Support** : Binance ✅, Saxo ✅

### 3. STOP (Ordre stop)
- **Description** : Ordre déclenché quand le prix atteint le niveau stop
- **Paramètres requis** : `symbol`, `side`, `quantity`, `stop_price`
- **Prix** : Stop price spécifié
- **Support** : Binance ✅ (STOP_LOSS), Saxo ✅

### 4. STOP_LIMIT (Ordre stop-limité)
- **Description** : Ordre stop avec prix limite
- **Paramètres requis** : `symbol`, `side`, `quantity`, `price`, `stop_price`
- **Prix** : Stop price déclenche l'ordre, limit price limite l'exécution
- **Support** : Binance ✅, Saxo ✅ (StopLimit)

## Statuts des ordres

Les ordres passent par différents statuts au cours de leur cycle de vie :

```mermaid
stateDiagram-v2
    [*] --> PENDING: Order created
    PENDING --> OPEN: Submitted to broker
    PENDING --> REJECTED: Broker rejection
    OPEN --> PARTIALLY_FILLED: Partial execution
    OPEN --> FILLED: Complete execution
    OPEN --> CANCELLED: User cancellation
    OPEN --> EXPIRED: Time expiration
    PARTIALLY_FILLED --> FILLED: Complete execution
    PARTIALLY_FILLED --> CANCELLED: User cancellation
    FILLED --> [*]
    CANCELLED --> [*]
    REJECTED --> [*]
    EXPIRED --> [*]
```

### Description des statuts

| Statut | Description | Transitions possibles |
|--------|-------------|----------------------|
| `PENDING` | Ordre créé localement, pas encore soumis au broker | → `OPEN`, `REJECTED` |
| `OPEN` | Ordre soumis et actif sur le broker | → `FILLED`, `PARTIALLY_FILLED`, `CANCELLED`, `EXPIRED` |
| `PARTIALLY_FILLED` | Ordre partiellement exécuté | → `FILLED`, `CANCELLED` |
| `FILLED` | Ordre complètement exécuté | → `[*]` (terminé) |
| `CANCELLED` | Ordre annulé par l'utilisateur ou le broker | → `[*]` (terminé) |
| `REJECTED` | Ordre rejeté par le broker (fond insuffisants, etc.) | → `[*]` (terminé) |
| `EXPIRED` | Ordre expiré (dépassement de la durée de validité) | → `[*]` (terminé) |

## Intégration avec les brokers

### Pattern Factory

Le système utilise le pattern Factory pour créer des instances de brokers :

```python
# BrokerService utilise BrokerFactory
broker = BrokerFactory.create_broker(broker_account)
```

### Interface unifiée (BrokerBase)

Tous les brokers implémentent l'interface `BrokerBase` qui définit :

- `place_order()` : Placer un ordre
- `cancel_order()` : Annuler un ordre
- `get_orders()` : Récupérer les ordres
- `authenticate()` : Authentification

### Mapping des types d'ordres

Chaque broker peut avoir des noms différents pour les types d'ordres. Le système effectue un mapping :

**Binance :**
- `MARKET` → `MARKET`
- `LIMIT` → `LIMIT`
- `STOP` → `STOP_LOSS`
- `STOP_LIMIT` → `STOP_LOSS_LIMIT`

**Saxo :**
- `MARKET` → `Market`
- `LIMIT` → `Limit`
- `STOP` → `Stop`
- `STOP_LIMIT` → `StopLimit`

## Gestion des erreurs

### Types d'erreurs

1. **BrokerAuthenticationError** : Échec d'authentification
   - Cause : Token expiré, credentials invalides
   - Action : Ré-authentifier ou vérifier les credentials

2. **BrokerAPIError** : Erreur API du broker
   - Cause : Problème de connexion, endpoint invalide
   - Action : Vérifier la connectivité, les endpoints

3. **InsufficientFundsError** : Fonds insuffisants
   - Cause : Balance insuffisante pour l'ordre
   - Action : Vérifier la balance disponible

4. **RateLimitError** : Limite de requêtes dépassée
   - Cause : Trop de requêtes envoyées
   - Action : Implémenter un backoff exponentiel

### Flux de gestion d'erreur

```mermaid
flowchart TD
    A[Place Order Request] --> B{Authenticate}
    B -->|Success| C[Place Order]
    B -->|Failed| D[Return AuthenticationError]
    C --> E{Order Valid?}
    E -->|Yes| F[Submit to Broker API]
    E -->|No| G[Return ValidationError]
    F --> H{API Response}
    H -->|Success| I[Return OrderResult.success=True]
    H -->|Error| J{Error Type}
    J -->|Insufficient Funds| K[Return InsufficientFundsError]
    J -->|Rate Limit| L[Return RateLimitError]
    J -->|Other| M[Return BrokerAPIError]
    I --> N[Log Success]
    D --> O[Log Error]
    K --> O
    L --> O
    M --> O
    G --> O
```

## Structure des données

### OrderResult

Résultat de placement d'ordre retourné par les brokers :

```python
@dataclass
class OrderResult:
    success: bool                    # Succès ou échec
    order_id: Optional[str] = None   # ID de l'ordre chez le broker
    message: str = ''                # Message informatif
    error: Optional[str] = None      # Message d'erreur si échec
    raw_data: Optional[Dict] = None  # Données brutes de la réponse
```

### BrokerOrder

Représentation standardisée d'un ordre depuis un broker :

```python
@dataclass
class BrokerOrder:
    symbol: str                      # Symbole de l'asset
    order_type: str                  # Type d'ordre
    side: str                        # BUY ou SELL
    quantity: Decimal                # Quantité
    price: Optional[Decimal] = None  # Prix (si applicable)
    status: str = 'PENDING'          # Statut de l'ordre
    filled_quantity: Decimal = Decimal('0')  # Quantité exécutée
    broker_order_id: Optional[str] = None    # ID chez le broker
    raw_data: Optional[Dict] = None          # Données brutes
```

## Fichiers de référence

- **Modèle Order** : `backend/apps/trading/models/trading.py` (lignes 160-220)
- **Interface BrokerBase** : `backend/apps/trading/brokers/base.py`
- **Service unifié** : `backend/apps/trading/services/broker_service.py` (méthode `place_order`, lignes 420-488)

## Prochaines étapes

Pour plus de détails, consultez :

1. [ORDERS_MODELS.md](./ORDERS_MODELS.md) - Documentation détaillée du modèle Order
2. [ORDERS_BINANCE.md](./ORDERS_BINANCE.md) - Implémentation Binance
3. [ORDERS_SAXO.md](./ORDERS_SAXO.md) - Implémentation Saxo
4. [ORDERS_VIEWS_URLS.md](./ORDERS_VIEWS_URLS.md) - Endpoints API REST
5. [ORDERS_SERVICES.md](./ORDERS_SERVICES.md) - Services et logique métier

