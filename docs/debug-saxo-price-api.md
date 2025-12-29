# Problème : Récupération des prix Saxo pour validation Yahoo Finance

## Contexte

La fonctionnalité de **validation Yahoo Finance** nécessite de récupérer des prix de référence depuis les brokers (Saxo et Binance) pour comparer avec les prix Yahoo et valider les symboles.

Pour les assets Saxo, le processus est le suivant :
1. Récupérer le prix depuis l'API Saxo Bank (`/trade/v1/infoprices`)
2. Comparer ce prix avec le prix Yahoo Finance
3. Valider le symbole Yahoo si la différence est dans une tolérance acceptable

## Problème rencontré

### 1. Structure de réponse API variable

L'API Saxo Bank `/trade/v1/infoprices` peut retourner deux formats différents :

**Format 1 (avec tableau Data)** :
```json
{
  "Data": [
    {
      "Quote": {
        "Mid": 150.50,
        "Bid": 150.48,
        "Ask": 150.52
      },
      "PriceInfo": {...}
    }
  ]
}
```

**Format 2 (structure directe - observé en tests)** :
```json
{
  "Quote": {
    "Amount": 0,
    "ErrorCode": "None",
    "PriceSource": "NASDAQ",
    "PriceSourceType": "Firm",
    "PriceTypeAsk": "NoAccess",
    "PriceTypeBid": "NoAccess"
  },
  "Uic": 1422226,
  "AssetType": "Stock",
  "PriceSource": "NASDAQ"
}
```

### 2. Accès aux prix refusé

Dans de nombreux cas, l'API retourne :
- `Amount: 0` (pas de prix disponible)
- `PriceTypeAsk: "NoAccess"` 
- `PriceTypeBid: "NoAccess"`

Cela indique que les permissions du compte ne permettent pas d'accéder aux prix, ou que l'instrument n'est pas disponible avec les permissions actuelles.

### 3. Champs de prix manquants

Selon les `FieldGroups` utilisés dans la requête, les champs disponibles diffèrent :
- Avec `FieldGroups: "Quote"` : souvent seulement `Amount`, `PriceTypeAsk`, `PriceTypeBid`
- Avec `FieldGroups: "PriceInfo,Quote"` : devrait inclure `PriceInfo.LastTraded`, `PriceInfo.Bid`, `PriceInfo.Ask`
- Les champs `Quote.Mid`, `Quote.Bid`, `Quote.Ask` ne sont pas toujours présents

## Solutions implémentées

### 1. Gestion des structures multiples

Le code gère maintenant les deux formats de réponse :
- Vérifie d'abord la présence de `Data` (tableau)
- Sinon, extrait directement depuis la racine
- Extrait `Quote` et `PriceInfo` selon la structure disponible

**Fichiers modifiés** :
- `backend/apps/trading/services/yahoo_validator.py` : fonction `get_saxo_price()`
- `backend/apps/trading/brokers/saxo.py` : méthode `get_asset_price()`

### 2. Priorité des champs de prix

Le code essaie plusieurs champs dans l'ordre de priorité :

1. **Format standard** : `Quote.Mid` > `Quote.Bid` > `Quote.Ask`
2. **Format Amount** : `Quote.Amount` (si > 0)
3. **Format PriceInfo** : `PriceInfo.LastTraded` > `PriceInfo.Bid` > `PriceInfo.Ask`

### 3. Utilisation de FieldGroups appropriés

La requête utilise maintenant `FieldGroups: "PriceInfo,Quote"` pour obtenir le maximum d'informations de prix.

### 4. Logging détaillé

Des logs détaillés ont été ajoutés pour :
- Identifier la structure de réponse reçue
- Détecter les accès refusés (`PriceTypeAsk/Bid: "NoAccess"`)
- Logger les champs disponibles pour le débogage

### 5. Gestion du token avec refresh automatique

Le code utilise maintenant `BrokerService.get_broker_instance()` qui :
- Gère automatiquement le refresh du token si expiré
- Authentifie le broker avant de faire les requêtes
- Évite les erreurs 401 (Unauthorized)

## Ce qui reste à faire / Limitations

### 1. Permissions du compte

Si `PriceTypeAsk/Bid: "NoAccess"` et `Amount: 0`, cela peut indiquer :
- **Compte simulation** : certains instruments peuvent ne pas être disponibles
- **Permissions insuffisantes** : le compte peut nécessiter des permissions supplémentaires pour accéder aux prix
- **Instrument non disponible** : l'instrument peut ne pas être tradable via Saxo avec ce compte

**Solutions possibles** :
- Vérifier les permissions du compte Saxo
- Utiliser un compte live au lieu de simulation
- Contacter Saxo pour activer l'accès aux prix pour ces instruments

### 2. Fallback vers d'autres sources

Si le prix Saxo n'est pas disponible, la validation Yahoo Finance pourrait :
- Utiliser directement le prix Yahoo comme référence (sans validation croisée)
- Sauter la validation de prix et valider uniquement l'existence du symbole
- Utiliser un autre broker comme référence (si disponible)

### 3. Mapping AssetType

Certains types d'assets peuvent nécessiter un mapping spécifique. Vérifier que le `AssetType` passé à l'API correspond bien aux types attendus par Saxo.

## Tests effectués

Des tests ont été réalisés avec plusieurs assets :
- Structure de réponse identifiée (format direct, pas de tableau Data)
- Champs disponibles identifiés (`Amount`, `PriceTypeAsk`, `PriceTypeBid`)
- Problème d'accès identifié (`NoAccess`)

**Exemple de réponse observée** :
```json
{
  "AssetType": "Stock",
  "LastUpdated": "0001-01-01T00:00:00.000000Z",
  "PriceSource": "NASDAQ",
  "Quote": {
    "Amount": 0,
    "ErrorCode": "None",
    "PriceSource": "NASDAQ",
    "PriceSourceType": "Firm",
    "PriceTypeAsk": "NoAccess",
    "PriceTypeBid": "NoAccess"
  },
  "Uic": 1422226
}
```

## Recommandations

1. **Vérifier les permissions du compte Saxo** : s'assurer que le compte a accès aux prix de marché
2. **Tester avec un compte live** : si possible, vérifier si les prix sont accessibles avec un compte live
3. **Implémenter un fallback** : si le prix Saxo n'est pas disponible, permettre la validation sans prix de référence
4. **Documenter les cas d'usage** : identifier quels types d'assets fonctionnent et lesquels ne fonctionnent pas

## Fichiers concernés

- `backend/apps/trading/services/yahoo_validator.py` : Fonction `get_saxo_price()`
- `backend/apps/trading/brokers/saxo.py` : Méthode `get_asset_price()`
- `backend/apps/trading/api/views.py` : Endpoint `validate_yahoo_symbols` (récupération du token)

## Références

- Documentation API Saxo Bank : `/trade/v1/infoprices`
- Issue GitHub : Validation Yahoo Finance nécessite des prix de référence Saxo
- Tests : Voir les logs du serveur Django lors de l'exécution de la validation Yahoo Finance
