# API Saxo : Récupération des détails d'un instrument par UIC

## Endpoint

```
GET https://gateway.saxobank.com/{environment}/openapi/ref/v1/instruments/details/{UIC}/{AssetType}
```

Où :
- `{environment}` = `sim` (simulation) ou `live` (production)
- `{UIC}` = L'UIC (Unified Instrument Code) de l'instrument
- `{AssetType}` = Type d'asset (ex: `Stock`, `Etf`, `CfdOnStock`, etc.)

## Paramètres de requête

- `AccountKey` : Clé du compte (optionnel mais recommandé)
- `ClientKey` : Clé du client (optionnel mais recommandé)
- `FieldGroups` : Groupes de champs à récupérer (défaut: 0 pour tous les champs)

## Récupération des clés (AccountKey, ClientKey, AccountId)

Pour récupérer ces clés, utiliser les endpoints suivants :

### Récupérer ClientKey
```
GET /port/v1/clients/me
```
Réponse : `{"ClientKey": "yFb5EAMRwy0HDb7xaHVR9A==", ...}`

### Récupérer AccountKey et AccountId
```
GET /port/v1/accounts/me
```
Réponse : `{"Data": [{"AccountKey": "yFb5EAMRwy0HDb7xaHVR9A==", "AccountId": 20376954, ...}], ...}`

### Exemple Python

```python
import requests

headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json"
}

# Récupérer ClientKey
res1 = requests.get(
    "https://gateway.saxobank.com/sim/openapi/port/v1/clients/me",
    headers=headers
)
client_key = res1.json()['ClientKey']

# Récupérer AccountKey et AccountId
res2 = requests.get(
    "https://gateway.saxobank.com/sim/openapi/port/v1/accounts/me",
    headers=headers
)
account_id = res2.json()["Data"][0]["AccountId"]
account_key = res2.json()['Data'][0]['AccountKey']

print(f"🔑 account_id = {account_id}")
print(f"🔑 client_key = {client_key}")
print(f"🔑 account_key = {account_key}")
```

## Headers requis

```
Authorization: Bearer {access_token}
Accept: application/json
```

## Exemple de requête

```python
import requests

uic = 211
asset_type = "Stock"
field_groups = 0
account_key = "..."
client_key = "..."
access_token = "..."

url = (
    f"https://gateway.saxobank.com/sim/openapi/ref/v1/instruments/details/"
    f"{uic}/{asset_type}"
    f"?AccountKey={account_key}&ClientKey={client_key}&FieldGroups={field_groups}"
)

headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json"
}

response = requests.get(url, headers=headers)
data = response.json()
```

## Champs importants de la réponse

### Champs principaux pour AllAsset

| Champ API | Description | Exemple | Mapping AllAsset |
|-----------|-------------|---------|------------------|
| `Symbol` | Symbole complet de l'instrument | `AAPL:xnas` | `symbol` |
| `Description` | Nom/Description de l'instrument | `Apple Inc.` | `name` |
| `AssetType` | Type d'asset | `Stock` | `asset_type` |
| `CurrencyCode` | Code de devise | `USD` | `currency` |
| `Uic` | UIC de l'instrument | `211` | `saxo_uic` |
| `IsTradable` | Si l'instrument est tradable | `True` | `is_tradable` |

### Champs Exchange (objet)

| Champ API | Description | Exemple | Mapping AllAsset |
|-----------|-------------|---------|------------------|
| `Exchange.ExchangeId` | ID de la bourse | `NASDAQ` | `exchange` |
| `Exchange.CountryCode` | Code pays | `US` | `market` ou `saxo_country_code` |
| `Exchange.Name` | Nom de la bourse | `NASDAQ` | - |

### Autres champs utiles

| Champ API | Description | Exemple | Usage |
|-----------|-------------|---------|-------|
| `PrimaryListing` | UIC de l'instrument primaire | `211` | Identifiant principal |
| `TradableAs` | Liste des types tradables | `['Stock']` | Vérification du type |
| `TradingStatus` | Statut de trading | `Tradable` | Validation |
| `PriceCurrency` | Devise du prix | `USD` | Alternative à CurrencyCode |

## Exemple de réponse complète

```json
{
  "AffiliateInfoRequired": false,
  "AmountDecimals": 4,
  "AssetType": "Stock",
  "CurrencyCode": "USD",
  "DefaultAmount": 0.0,
  "DefaultSlippage": 0.0,
  "DefaultSlippageType": "Ticks",
  "Description": "Apple Inc.",
  "Exchange": {
    "CountryCode": "US",
    "ExchangeId": "NASDAQ",
    "Name": "NASDAQ",
    "TimeZoneId": "3"
  },
  "Format": {
    "Decimals": 2,
    "OrderDecimals": 2
  },
  "IsTradable": true,
  "Symbol": "AAPL:xnas",
  "TradableAs": ["Stock"],
  "TradingStatus": "Tradable",
  "Uic": 211,
  ...
}
```

## Utilisation pour créer/mettre à jour AllAsset

Lors de la synchronisation des positions Saxo, si le symbole n'est pas disponible directement, utiliser cet endpoint pour :

1. Récupérer le vrai symbole (`Symbol`) au lieu de créer `UIC_xxxx`
2. Récupérer le nom complet (`Description`)
3. Récupérer toutes les métadonnées nécessaires (exchange, currency, etc.)
4. Créer l'AllAsset avec toutes les données complètes

## Avantages par rapport à `/ref/v1/instruments`

- **Rapide** : Une seule requête au lieu de parcourir des milliers d'instruments
- **Précis** : Retourne directement l'instrument recherché
- **Complet** : Contient toutes les métadonnées nécessaires
- **Efficace** : Pas de pagination ni de recherche nécessaire

