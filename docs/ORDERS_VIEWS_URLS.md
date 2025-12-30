# Endpoints API REST - Système d'ordres

## Introduction

Ce document décrit les endpoints API REST pour la gestion des ordres. Les endpoints sont fournis via Django REST Framework ViewSets, offrant une interface RESTful standard pour les opérations CRUD et des actions personnalisées.

## Vue d'ensemble

### OrderViewSet

Fichier : `backend/apps/trading/api/views.py` (lignes 670-734)

Le `OrderViewSet` expose les endpoints suivants :

- **CRUD standard** : Liste, création, lecture, mise à jour, suppression
- **Actions personnalisées** : `pending`, `filled`, `cancel`

## Configuration des URLs

### Router

Fichier : `backend/apps/trading/api/urls.py` (ligne 86)

```python
router.register(r'orders', views.OrderViewSet, basename='order')
```

### URLs générées automatiquement

Le router Django REST Framework génère automatiquement les URLs suivantes :

| Méthode | URL | Action | Description |
|---------|-----|--------|-------------|
| GET | `/api/orders/` | `list()` | Liste tous les ordres |
| POST | `/api/orders/` | `create()` | Créer un nouvel ordre |
| GET | `/api/orders/{id}/` | `retrieve()` | Détails d'un ordre |
| PUT | `/api/orders/{id}/` | `update()` | Mettre à jour un ordre |
| PATCH | `/api/orders/{id}/` | `partial_update()` | Mettre à jour partiellement |
| DELETE | `/api/orders/{id}/` | `destroy()` | Supprimer un ordre |

## Endpoints CRUD

### GET /api/orders/ - Liste des ordres

Récupère la liste paginée des ordres de l'utilisateur authentifié.

**Requête :**
```http
GET /api/orders/
Authorization: Bearer <token>
```

**Paramètres de requête :**
- `page` : Numéro de page (pagination)
- `page_size` : Taille de la page (défaut: 50, max: 200)
- `order_type` : Filtrer par type (`MARKET`, `LIMIT`, `STOP`, `STOP_LIMIT`)
- `side` : Filtrer par sens (`BUY`, `SELL`)
- `status` : Filtrer par statut (`PENDING`, `OPEN`, `FILLED`, etc.)
- `broker` : Filtrer par broker (ID)
- `asset` : Filtrer par asset (ID)
- `search` : Recherche dans `asset__symbol` et `broker_order_id`
- `ordering` : Tri (`created_at`, `price`, `quantity`, ou préfixer par `-` pour desc)

**Exemple de requête :**
```http
GET /api/orders/?status=OPEN&ordering=-created_at&page_size=20
```

**Réponse (200 OK) :**
```json
{
    "count": 42,
    "next": "http://localhost:8000/api/orders/?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "asset": {
                "id": 123,
                "symbol": "AAPL",
                "name": "Apple Inc."
            },
            "broker_name": "Saxo Bank",
            "order_type": "LIMIT",
            "side": "BUY",
            "status": "OPEN",
            "quantity": "10.00000000",
            "filled_quantity": "0.00000000",
            "fill_percentage": 0.0,
            "price": "150.25000000",
            "stop_price": null,
            "broker_order_id": "12345678",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:05Z"
        }
    ]
}
```

### POST /api/orders/ - Créer un ordre

Crée un nouvel ordre dans la base de données.

**Requête :**
```http
POST /api/orders/
Authorization: Bearer <token>
Content-Type: application/json

{
    "asset_id": 123,
    "broker_id": 1,
    "order_type": "LIMIT",
    "side": "BUY",
    "quantity": "10.5",
    "price": "150.25"
}
```

**Corps de la requête :**
- `asset_id` (int) : ID de l'asset (requis)
- `broker_id` (int) : ID du broker (requis)
- `order_type` (string) : Type d'ordre (`MARKET`, `LIMIT`, `STOP`, `STOP_LIMIT`)
- `side` (string) : Sens (`BUY`, `SELL`)
- `quantity` (string/decimal) : Quantité (requis)
- `price` (string/decimal) : Prix limite (requis pour LIMIT)
- `stop_price` (string/decimal) : Prix stop (requis pour STOP/STOP_LIMIT)

**Réponse (201 Created) :**
```json
{
    "id": 1,
    "asset": {
        "id": 123,
        "symbol": "AAPL",
        "name": "Apple Inc."
    },
    "broker_name": "Saxo Bank",
    "order_type": "LIMIT",
    "side": "BUY",
    "status": "PENDING",
    "quantity": "10.50000000",
    "filled_quantity": "0.00000000",
    "fill_percentage": 0.0,
    "price": "150.25000000",
    "stop_price": null,
    "broker_order_id": "",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
}
```

**Erreurs possibles :**
- `400 Bad Request` : Validation échouée
- `401 Unauthorized` : Non authentifié

**Exemple d'erreur de validation :**
```json
{
    "price": ["Un ordre LIMIT nécessite un prix"]
}
```

### GET /api/orders/{id}/ - Détails d'un ordre

Récupère les détails complets d'un ordre.

**Requête :**
```http
GET /api/orders/1/
Authorization: Bearer <token>
```

**Réponse (200 OK) :**
```json
{
    "id": 1,
    "asset": {
        "id": 123,
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "currency": "USD"
    },
    "broker_name": "Saxo Bank",
    "order_type": "LIMIT",
    "side": "BUY",
    "status": "OPEN",
    "quantity": "10.00000000",
    "filled_quantity": "3.50000000",
    "fill_percentage": 35.0,
    "price": "150.25000000",
    "stop_price": null,
    "broker_order_id": "12345678",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:35:00Z"
}
```

**Erreurs possibles :**
- `404 Not Found` : Ordre introuvable
- `403 Forbidden` : Ordre n'appartient pas à l'utilisateur

### PUT /api/orders/{id}/ - Mettre à jour un ordre

Met à jour complètement un ordre.

**Requête :**
```http
PUT /api/orders/1/
Authorization: Bearer <token>
Content-Type: application/json

{
    "asset_id": 123,
    "broker_id": 1,
    "order_type": "LIMIT",
    "side": "BUY",
    "quantity": "15.0",
    "price": "151.00",
    "status": "OPEN"
}
```

**Réponse (200 OK) :** Même format que GET

### PATCH /api/orders/{id}/ - Mettre à jour partiellement

Met à jour uniquement les champs fournis.

**Requête :**
```http
PATCH /api/orders/1/
Authorization: Bearer <token>
Content-Type: application/json

{
    "status": "CANCELLED"
}
```

**Réponse (200 OK) :** Même format que GET

### DELETE /api/orders/{id}/ - Supprimer un ordre

Supprime un ordre de la base de données.

**Requête :**
```http
DELETE /api/orders/1/
Authorization: Bearer <token>
```

**Réponse (204 No Content) :** Pas de contenu

**Erreurs possibles :**
- `404 Not Found` : Ordre introuvable
- `403 Forbidden` : Ordre n'appartient pas à l'utilisateur

## Actions personnalisées

### GET /api/orders/pending/ - Ordres en attente

Récupère tous les ordres en attente d'exécution (statuts `PENDING`, `OPEN`, `PARTIALLY_FILLED`).

**Requête :**
```http
GET /api/orders/pending/
Authorization: Bearer <token>
```

**Paramètres de requête :**
- Même filtres que GET /api/orders/ (sauf `status` qui est implicitement filtré)

**Réponse (200 OK) :**
```json
[
    {
        "id": 1,
        "asset": {
            "id": 123,
            "symbol": "AAPL"
        },
        "broker_name": "Saxo Bank",
        "order_type": "LIMIT",
        "side": "BUY",
        "status": "OPEN",
        "quantity": "10.00000000",
        "filled_quantity": "0.00000000",
        "fill_percentage": 0.0,
        "price": "150.25000000",
        "broker_order_id": "12345678",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:05Z"
    }
]
```

**Note :** Cette action retourne un array directement (pas de pagination).

### GET /api/orders/filled/ - Ordres exécutés

Récupère tous les ordres complètement exécutés (statut `FILLED`).

**Requête :**
```http
GET /api/orders/filled/
Authorization: Bearer <token>
```

**Paramètres de requête :**
- Même filtres que GET /api/orders/
- Pagination disponible (défaut: 50 par page)

**Réponse (200 OK) :**
```json
{
    "count": 125,
    "next": "http://localhost:8000/api/orders/filled/?page=2",
    "previous": null,
    "results": [
        {
            "id": 10,
            "asset": {
                "id": 123,
                "symbol": "AAPL"
            },
            "broker_name": "Saxo Bank",
            "order_type": "MARKET",
            "side": "BUY",
            "status": "FILLED",
            "quantity": "10.00000000",
            "filled_quantity": "10.00000000",
            "fill_percentage": 100.0,
            "price": null,
            "broker_order_id": "12345679",
            "created_at": "2024-01-14T14:20:00Z",
            "updated_at": "2024-01-14T14:20:05Z"
        }
    ]
}
```

**Note :** Cette action retourne une réponse paginée (contrairement à `pending`).

### POST /api/orders/{id}/cancel/ - Annuler un ordre

Annule un ordre en attente (change le statut en `CANCELLED`).

**Requête :**
```http
POST /api/orders/1/cancel/
Authorization: Bearer <token>
```

**Réponse (200 OK) :**
```json
{
    "status": "Order cancelled",
    "order": {
        "id": 1,
        "asset": {
            "id": 123,
            "symbol": "AAPL"
        },
        "broker_name": "Saxo Bank",
        "order_type": "LIMIT",
        "side": "BUY",
        "status": "CANCELLED",
        "quantity": "10.00000000",
        "filled_quantity": "0.00000000",
        "fill_percentage": 0.0,
        "price": "150.25000000",
        "broker_order_id": "12345678",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T11:00:00Z"
    }
}
```

**Erreurs possibles :**
- `400 Bad Request` : Ordre ne peut pas être annulé (déjà `FILLED`, `CANCELLED`, ou `EXPIRED`)

**Exemple d'erreur :**
```json
{
    "error": "Cannot cancel order with status FILLED"
}
```

**Validation :**
Seuls les ordres avec statut `PENDING`, `OPEN` ou `PARTIALLY_FILLED` peuvent être annulés.

## Pagination

### Configuration

Le `OrderViewSet` utilise `StandardPagination` :

```python
pagination_class = StandardPagination
```

### Paramètres

- **page_size** : 50 (défaut)
- **page_size_query_param** : `page_size` (paramètre pour changer la taille)
- **max_page_size** : 200 (limite maximum)

### Exemple

```http
GET /api/orders/?page=2&page_size=100
```

## Filtres

### Filtres automatiques (django-filter)

```python
filterset_fields = ['order_type', 'side', 'status', 'broker', 'asset']
```

**Exemples :**
- `/api/orders/?status=OPEN`
- `/api/orders/?side=BUY&order_type=LIMIT`
- `/api/orders/?broker=1`

### Recherche

```python
search_fields = ['asset__symbol', 'broker_order_id']
```

**Exemple :**
- `/api/orders/?search=AAPL` (recherche dans symbol et broker_order_id)

### Tri

```python
ordering_fields = ['created_at', 'price', 'quantity']
ordering = ['-created_at']  # Défaut: plus récent d'abord
```

**Exemples :**
- `/api/orders/?ordering=price` (tri croissant par prix)
- `/api/orders/?ordering=-quantity` (tri décroissant par quantité)

## Permissions

### Authentification requise

```python
permission_classes = [permissions.IsAuthenticated]
```

Tous les endpoints nécessitent une authentification. Les méthodes supportées :

- **JWT Token** : `Authorization: Bearer <token>`
- **Session** : Cookie de session Django

### Filtrage par utilisateur

```python
def get_queryset(self):
    return Order.objects.filter(user=self.request.user)
```

Seuls les ordres de l'utilisateur authentifié sont accessibles.

### Création d'ordre

```python
def perform_create(self, serializer):
    serializer.save(user=self.request.user)
```

L'utilisateur est automatiquement assigné lors de la création.

## Serializer

### OrderSerializer

Fichier : `backend/apps/trading/api/serializers.py` (lignes 351-412)

Le serializer inclut :

- **Relations imbriquées** : `asset` (AssetNestedSerializer), `broker_name`
- **Champs calculés** : `fill_percentage`
- **Validations** : Quantité positive, prix requis pour LIMIT, etc.

Voir [ORDERS_MODELS.md](./ORDERS_MODELS.md) pour plus de détails sur le serializer.

## Codes de statut HTTP

| Code | Description | Cas d'usage |
|------|-------------|-------------|
| 200 OK | Succès | GET, PUT, PATCH réussi |
| 201 Created | Créé | POST réussi |
| 204 No Content | Succès sans contenu | DELETE réussi |
| 400 Bad Request | Requête invalide | Validation échouée |
| 401 Unauthorized | Non authentifié | Token manquant/invalide |
| 403 Forbidden | Accès refusé | Ordre n'appartient pas à l'utilisateur |
| 404 Not Found | Non trouvé | Ordre introuvable |
| 500 Internal Server Error | Erreur serveur | Erreur interne |

## Exemples d'utilisation

### Liste des ordres ouverts avec filtres

```python
import requests

headers = {
    'Authorization': 'Bearer <token>',
    'Content-Type': 'application/json'
}

response = requests.get(
    'http://localhost:8000/api/orders/',
    headers=headers,
    params={
        'status': 'OPEN',
        'ordering': '-created_at',
        'page_size': 20
    }
)

orders = response.json()
print(f"Total: {orders['count']} ordres")
for order in orders['results']:
    print(f"{order['asset']['symbol']}: {order['side']} {order['quantity']} @ {order['price']}")
```

### Créer un ordre LIMIT

```python
order_data = {
    'asset_id': 123,
    'broker_id': 1,
    'order_type': 'LIMIT',
    'side': 'BUY',
    'quantity': '10.5',
    'price': '150.25'
}

response = requests.post(
    'http://localhost:8000/api/orders/',
    headers=headers,
    json=order_data
)

if response.status_code == 201:
    order = response.json()
    print(f"Ordre créé: {order['id']}")
else:
    print(f"Erreur: {response.json()}")
```

### Annuler un ordre

```python
response = requests.post(
    'http://localhost:8000/api/orders/1/cancel/',
    headers=headers
)

if response.status_code == 200:
    result = response.json()
    print(f"Statut: {result['status']}")
    print(f"Ordre: {result['order']['status']}")
else:
    print(f"Erreur: {response.json()}")
```

## Fichiers de référence

- **ViewSet** : `backend/apps/trading/api/views.py` (OrderViewSet, lignes 670-734)
- **URLs** : `backend/apps/trading/api/urls.py` (router.orders, ligne 86)
- **Serializer** : `backend/apps/trading/api/serializers.py` (OrderSerializer, lignes 351-412)

## Notes importantes

1. **Filtrage utilisateur** : Tous les endpoints filtrent automatiquement par utilisateur authentifié
2. **Pagination** : Les endpoints `list()` et `filled()` sont paginés, `pending()` ne l'est pas
3. **Annulation** : L'annulation ne fait que changer le statut localement, elle n'annule pas l'ordre chez le broker (utiliser `BrokerService.cancel_order()` pour cela)
4. **Validation** : Les validations sont effectuées au niveau du serializer
5. **Statuts** : Seuls certains statuts peuvent être modifiés/annulés

