# Endpoints API pour passer des ordres

## Endpoints disponibles

### 1. POST /api/orders/place/ - Placer un ordre directement via le broker

**URL complète** : `http://localhost:8000/api/orders/place/`

**Méthode** : `POST`

**Authentification** : Requise (Bearer Token ou Session)

**Body (JSON)** :
```json
{
  "broker_account_id": 1,
  "symbol": "AAPL",
  "side": "BUY",
  "quantity": "10",
  "order_type": "MARKET",
  "price": "150.25",        // Optionnel (requis pour LIMIT)
  "stop_price": "145.00",   // Optionnel (requis pour STOP)
  "asset_id": 123           // Optionnel (sera cherché si non fourni)
}
```

**Réponse (201 Created)** :
```json
{
  "success": true,
  "message": "Order placed: NEW",
  "order": {
    "id": 1,
    "asset": {...},
    "order_type": "MARKET",
    "side": "BUY",
    "status": "OPEN",
    "quantity": "10.00000000",
    "broker_order_id": "123456789",
    ...
  },
  "broker_result": {
    "order_id": "123456789",
    "message": "Order placed: NEW"
  }
}
```

### 2. POST /api/orders/{id}/place_broker/ - Placer un ordre existant via le broker

**URL complète** : `http://localhost:8000/api/orders/1/place_broker/`

**Méthode** : `POST`

**Description** : Place un ordre existant (avec statut PENDING) via le broker

**Réponse (200 OK)** :
```json
{
  "success": true,
  "message": "Order placed: NEW",
  "order": {...},
  "broker_result": {...}
}
```

### 3. POST /api/orders/sync/ - Synchroniser les ordres depuis un broker

**URL complète** : `http://localhost:8000/api/orders/sync/`

**Méthode** : `POST`

**Body (JSON)** :
```json
{
  "broker_account_id": 1,
  "status": "OPEN",         // Optionnel (défaut: "OPEN")
  "symbol": "AAPL"          // Optionnel (filtrer par symbole)
}
```

**Réponse (200 OK)** :
```json
{
  "success": true,
  "message": "Synced 5 orders (2 created, 3 updated)",
  "created": 2,
  "updated": 3,
  "errors": []
}
```

### 4. POST /api/orders/{id}/cancel_broker/ - Annuler un ordre chez le broker

**URL complète** : `http://localhost:8000/api/orders/1/cancel_broker/`

**Méthode** : `POST`

**Description** : Annule un ordre chez le broker (nécessite un broker_order_id)

**Réponse (200 OK)** :
```json
{
  "success": true,
  "message": "Order cancelled at broker",
  "order": {
    "id": 1,
    "status": "CANCELLED",
    ...
  }
}
```

### 5. POST /api/orders/{id}/cancel/ - Annuler un ordre (local + broker si possible)

**URL complète** : `http://localhost:8000/api/orders/1/cancel/`

**Méthode** : `POST`

**Description** : Annule un ordre localement. Si l'ordre a un `broker_order_id`, essaie aussi d'annuler chez le broker.

## Comment tester avec cURL

### 1. Placer un ordre MARKET

```bash
curl -X POST http://localhost:8000/api/orders/place/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "broker_account_id": 1,
    "symbol": "BTCUSDT",
    "side": "BUY",
    "quantity": "0.001",
    "order_type": "MARKET"
  }'
```

### 2. Placer un ordre LIMIT

```bash
curl -X POST http://localhost:8000/api/orders/place/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "broker_account_id": 1,
    "symbol": "AAPL",
    "side": "BUY",
    "quantity": "10",
    "order_type": "LIMIT",
    "price": "150.25"
  }'
```

### 3. Synchroniser les ordres

```bash
curl -X POST http://localhost:8000/api/orders/sync/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "broker_account_id": 1,
    "status": "OPEN"
  }'
```

## Accès via l'interface web

### Option 1 : Utiliser le navigateur avec l'authentification Django Session

1. **Connectez-vous** : `http://localhost:8000/admin/` ou via votre interface de login
2. **Ouvrez la console du navigateur** (F12)
3. **Testez avec fetch** :

```javascript
// Placer un ordre MARKET
fetch('http://localhost:8000/api/orders/place/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
  },
  credentials: 'include',
  body: JSON.stringify({
    broker_account_id: 1,
    symbol: 'BTCUSDT',
    side: 'BUY',
    quantity: '0.001',
    order_type: 'MARKET'
  })
})
.then(r => r.json())
.then(data => console.log(data));
```

### Option 2 : Utiliser Postman ou Insomnia

1. Configurez l'authentification (Bearer Token ou Session)
2. Utilisez les endpoints listés ci-dessus

### Option 3 : Créer une page frontend React (à faire)

Il n'existe pas encore de page React pour passer des ordres. Vous devrez créer :

- **Page** : `frontend/src/pages/Orders.tsx`
- **Composant** : `frontend/src/components/orders/PlaceOrderModal.tsx`
- **Mise à jour du service** : Ajouter les nouvelles méthodes dans `frontend/src/services/orders.ts`

## Paramètres des ordres

### Types d'ordres supportés

- **MARKET** : Ordre au marché (pas de prix requis)
- **LIMIT** : Ordre à cours limité (prix requis)
- **STOP** : Ordre stop (stop_price requis)
- **STOP_LIMIT** : Ordre stop-limité (prix et stop_price requis)

### Côtés (Side)

- **BUY** : Achat
- **SELL** : Vente

### Statuts possibles

- **PENDING** : En attente (non envoyé au broker)
- **OPEN** : Ouvert et actif chez le broker
- **FILLED** : Complètement exécuté
- **PARTIALLY_FILLED** : Partiellement exécuté
- **CANCELLED** : Annulé
- **REJECTED** : Rejeté par le broker
- **EXPIRED** : Expiré

## Exemple d'utilisation complète

### Workflow typique

1. **Placer un ordre** :
   ```bash
   POST /api/orders/place/
   ```

2. **Vérifier les ordres en attente** :
   ```bash
   GET /api/orders/pending/
   ```

3. **Synchroniser les ordres depuis le broker** :
   ```bash
   POST /api/orders/sync/
   ```

4. **Annuler un ordre si nécessaire** :
   ```bash
   POST /api/orders/{id}/cancel_broker/
   ```

## Erreurs courantes

### 401 Unauthorized
- **Cause** : Token d'authentification manquant ou invalide
- **Solution** : Vérifier l'authentification

### 404 Not Found
- **Cause** : Broker account ou asset introuvable
- **Solution** : Vérifier que le `broker_account_id` et le `symbol` existent

### 400 Bad Request
- **Cause** : Paramètres manquants ou invalides
- **Solution** : Vérifier le body de la requête

### Erreur broker
- **Cause** : Erreur lors du placement chez le broker (fonds insuffisants, symbole invalide, etc.)
- **Solution** : Vérifier le message d'erreur retourné

## Prochaines étapes

Pour créer l'interface frontend, voir :
- `frontend/src/services/orders.ts` - Service à mettre à jour
- Créer `frontend/src/components/orders/PlaceOrderModal.tsx`
- Créer `frontend/src/pages/Orders.tsx`










