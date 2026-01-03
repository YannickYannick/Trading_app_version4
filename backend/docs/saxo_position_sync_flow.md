# Flux de synchronisation des positions Saxo

## Vue d'ensemble

Lors de la synchronisation des positions depuis Saxo Bank, le système utilise une logique intelligente pour récupérer ou créer des `AllAssets` avec les vraies données (symbole, nom, exchange, etc.) au lieu de créer des assets génériques avec des noms bizarres comme `UIC_xxxx`.

## Architecture du flux

```
Frontend (Interface utilisateur)
    ↓
API REST: POST /api/sync/ {"sync_type": "POSITIONS"}
    ↓
PositionSyncService.sync()
    ↓
SaxoBroker.get_positions() → Récupère les positions depuis Saxo
    ↓
Pour chaque position → _sync_single_position()
    ↓
_get_or_create_all_asset() → Logique intelligente en 4 étapes
    ├─ Étape 1: Recherche par (symbol, platform)
    ├─ Étape 2: Si UIC_xxx → Recherche par saxo_uic
    ├─ Étape 3: Récupération depuis API Saxo via /instruments/details
    └─ Étape 4: Création minimale (fallback)
    ↓
Position créée/mise à jour avec le bon AllAsset
```

## Étapes détaillées

### Étape 1 : Déclenchement depuis le frontend

L'utilisateur clique sur le bouton de synchronisation dans l'interface frontend, ce qui déclenche :

```
POST /api/sync/
Body: {"sync_type": "POSITIONS", "force": false}
```

L'API appelle ensuite `PositionSyncService.sync(broker_account)`.

### Étape 2 : Initialisation et authentification

```python
# PositionSyncService.sync()
1. Récupère les credentials du BrokerAccount
2. Crée une instance SaxoBroker avec ces credentials
3. Authentifie le broker via OAuth2
   - Vérifie si le token est encore valide
   - Si expiré, utilise le refresh_token pour obtenir un nouveau access_token
```

### Étape 3 : Récupération des positions depuis l'API Saxo

```python
# SaxoBroker.get_positions()
→ Appelle: GET /port/v1/positions
→ Paramètres: ClientKey, AccountKey (récupérés via _get_account_keys())

Réponse Saxo pour chaque position:
{
    "PositionBase": {
        "Symbol": "AAPL:xnas",      # Peut être vide !
        "Uic": 211,                  # Toujours présent
        "AssetType": "Stock",
        "Currency": "USD",
        ...
    },
    "PositionView": {
        "AverageOpenPrice": 150.50,
        "CurrentPrice": 152.30,
        "Amount": 10,
        ...
    }
}
```

**Traitement dans `get_positions()`:**

Si le `Symbol` est vide ou manquant :
1. Essaie de récupérer le symbole via `_get_symbol_from_uic()` (ancienne méthode)
2. Si échec, crée un symbole fallback : `"UIC_{uic}"` (ex: `"UIC_211"`)

Dans tous les cas, un objet `BrokerPosition` est créé avec :
- `symbol`: Le symbole récupéré ou le fallback `"UIC_xxxx"`
- `raw_data`: Contient `uic`, `asset_type`, et toutes les autres métadonnées

### Étape 4 : Pour chaque position → Création/Matching AllAsset

C'est ici que la logique intelligente s'exécute dans `_sync_single_position()`.

#### 4.1 Extraction des données de la position

```python
raw_data = broker_position.raw_data  # Dictionnaire avec toutes les métadonnées
uic = raw_data.get('uic')           # Ex: 211 (int)
asset_type = raw_data.get('asset_type')  # Ex: "Stock"
symbol = broker_position.symbol     # Peut être "AAPL:xnas" ou "UIC_211"
```

#### 4.2 Préparation du broker pour l'API

Si c'est une position Saxo et qu'un UIC est disponible :

```python
1. Crée une nouvelle instance SaxoBroker (si nécessaire)
2. Authentifie le broker (vérifie/rafraîchit le token)
3. Cette instance sera utilisée pour appeler get_asset_by_uic()
```

#### 4.3 Logique intelligente : `_get_or_create_all_asset()`

Cette méthode essaie 4 approches successives :

**🔍 Étape 1 : Recherche par (symbol, platform)**

```python
AllAssets.objects.filter(
    symbol=symbol,           # Ex: "AAPL:xnas" ou "UIC_211"
    platform='SAXO'
).first()
```

→ Si trouvé : retourne l'AllAsset existant et met à jour l'UIC s'il manque.

**🔍 Étape 2 : Si symbol = "UIC_xxxx" → Recherche par UIC**

```python
if symbol.startswith('UIC_') and uic:
    extracted_uic = int(symbol.replace('UIC_', ''))  # Ex: 211
    uic_int = int(uic)  # S'assurer que c'est un int
    
    AllAssets.objects.filter(
        saxo_uic=uic_int,
        platform='SAXO'
    ).first()
```

→ Si trouvé : retourne l'AllAsset existant (même si le symbol était `UIC_211`, l'AllAsset peut avoir le vrai symbole `AAPL:xnas`).

**🚀 Étape 3 : Récupération depuis l'API Saxo (NOUVELLE MÉTHODE)**

Si toujours pas trouvé et qu'un UIC est disponible :

```python
if platform == 'SAXO' and uic and broker_instance:
    broker_asset = broker_instance.get_asset_by_uic(uic, asset_type)
```

**Détails de `get_asset_by_uic()` :**

1. **Récupération des clés de compte** :
   ```python
   # Via _get_account_keys()
   GET /port/v1/clients/me → client_key
   GET /port/v1/accounts/me → account_key + account_id
   ```

2. **Appel à l'endpoint details** :
   ```python
   GET /ref/v1/instruments/details/{UIC}/{AssetType}
   ?AccountKey={account_key}
   &ClientKey={client_key}
   &FieldGroups=0
   ```
   
   Exemple :
   ```
   GET /ref/v1/instruments/details/211/Stock
   ?AccountKey=yFb5EAMRwy0HDb7xaHVR9A==
   &ClientKey=yFb5EAMRwy0HDb7xaHVR9A==
   &FieldGroups=0
   ```

3. **Réponse de l'API Saxo** :
   ```json
   {
     "Symbol": "AAPL:xnas",
     "Description": "Apple Inc.",
     "AssetType": "Stock",
     "CurrencyCode": "USD",
     "Uic": 211,
     "IsTradable": true,
     "Exchange": {
       "ExchangeId": "NASDAQ",
       "CountryCode": "US",
       "Name": "NASDAQ"
     },
     ...
   }
   ```

4. **Création d'un BrokerAsset complet** :
   ```python
   BrokerAsset(
       symbol="AAPL:xnas",           # ✅ Vrai symbole
       name="Apple Inc.",            # ✅ Nom complet
       asset_type="Stock",
       exchange="NASDAQ",
       currency="USD",
       is_tradable=True,
       broker_id="211",
       raw_data={...}  # Toutes les métadonnées
   )
   ```

5. **Essai de différents asset_types** :
   Si le premier asset_type échoue (erreur 404), la méthode essaie :
   - Le type demandé (ex: "Stock")
   - "Etf"
   - "CfdOnStock"
   - Etc.

6. **Création de l'AllAsset avec toutes les données** :
   ```python
   AllAssets.objects.create(
       symbol="AAPL:xnas",           # ✅ Vrai symbole (pas "UIC_211")
       name="Apple Inc.",            # ✅ Nom complet
       platform="SAXO",
       asset_type="Stock",
       currency="USD",
       exchange="NASDAQ",
       market="US",                  # CountryCode
       is_tradable=True,
       saxo_uic=211,                 # ✅ UIC sauvegardé
       saxo_exchange_id="NASDAQ",
       saxo_country_code="US"
   )
   ```

**⚠️ Étape 4 : Fallback - Création minimale**

Si toutes les étapes précédentes ont échoué :

```python
AllAssets.objects.create(
    symbol="UIC_211",             # ⚠️ Fallback
    name="UIC_211",               # ⚠️ Fallback
    platform="SAXO",
    asset_type=asset_type or 'UNKNOWN',
    currency='USD',
    is_tradable=True,
    saxo_uic=211,                 # Au moins l'UIC est sauvegardé
    ...
)
```

### Étape 5 : Création/Mise à jour de la Position

Une fois l'AllAsset trouvé ou créé :

```python
Position.objects.update_or_create(
    broker_position_id=broker_position.broker_position_id,
    broker=broker_account.broker,
    user=user,
    defaults={
        'all_asset': all_asset,          # ✅ Référence vers le bon AllAsset
        'side': 'LONG' or 'SHORT',
        'quantity': broker_position.quantity,
        'entry_price': broker_position.entry_price,
        'current_price': broker_position.current_price,
        'pnl': broker_position.pnl,
        ...
    }
)
```

## Avantages de cette approche

### Performance

- **Avant** : Parcourir jusqu'à 5000 assets pour trouver l'UIC → lent (plusieurs secondes par position)
- **Maintenant** : Une seule requête directe à `/instruments/details/{UIC}/{AssetType}` → rapide (< 1 seconde)

### Qualité des données

- **Avant** : AllAssets créés avec `symbol="UIC_211"`, `name="UIC_211"` → inutilisable
- **Maintenant** : AllAssets créés avec les vraies données :
  - `symbol="AAPL:xnas"`
  - `name="Apple Inc."`
  - `exchange="NASDAQ"`
  - `currency="USD"`
  - Toutes les métadonnées complètes

### Robustesse

- Essai de différents asset_types si le premier échoue
- Fallback gracieux si l'API ne trouve pas l'instrument
- Logs détaillés pour le débogage
- Sauvegarde toujours de l'UIC même en cas d'échec

## Logs et débogage

Le système génère des logs détaillés à chaque étape :

```
INFO: Position with UIC fallback symbol: UIC_211, UIC=211, asset_type=Stock, will attempt to fetch real symbol from API
INFO: Attempting to fetch asset from Saxo API for UIC 211 (asset_type=Stock)
INFO: ✅ Successfully fetched asset from API: AAPL:xnas (Apple Inc.) for UIC 211
INFO: Created AllAsset from API for UIC 211: AAPL:xnas (Apple Inc.)
```

En cas d'erreur :

```
WARNING: ⚠️ get_asset_by_uic returned None for UIC 211. Asset may not be found in API or search limit reached.
WARNING: AllAsset not found for UIC_211 (SAXO). Creating minimal AllAsset.
```

## Cas d'usage

### Cas 1 : Position avec symbole complet

```
Position reçue: Symbol="AAPL:xnas", UIC=211
→ Étape 1: Trouve AllAsset existant avec symbol="AAPL:xnas"
→ Utilise l'AllAsset existant ✅
```

### Cas 2 : Position sans symbole (nouveau)

```
Position reçue: Symbol="", UIC=211, AssetType="Stock"
→ Étape 1: Pas trouvé (symbol vide)
→ Étape 2: Pas trouvé (pas de UIC_211 dans la DB)
→ Étape 3: Appelle /instruments/details/211/Stock
   → Retourne: Symbol="AAPL:xnas", Description="Apple Inc.", etc.
   → Crée AllAsset avec toutes les données ✅
```

### Cas 3 : Position avec UIC_xxx existant

```
Position reçue: Symbol="UIC_211", UIC=211
→ Étape 1: Trouve AllAsset avec symbol="UIC_211"
→ Utilise l'AllAsset existant (mais il a encore le mauvais symbol)
→ À la prochaine sync, si l'AllAsset est supprimé :
   → Étape 3 récupérera le vrai symbole et créera un nouvel AllAsset ✅
```

### Cas 4 : UIC non trouvé dans l'API

```
Position reçue: Symbol="UIC_99999", UIC=99999
→ Étape 1: Pas trouvé
→ Étape 2: Pas trouvé
→ Étape 3: API retourne 404 (instrument n'existe pas)
→ Étape 4: Crée AllAsset minimal avec UIC_99999 ⚠️
```

## Points d'attention

1. **Performance** : Si vous avez beaucoup de positions (50+), la synchronisation peut prendre du temps car chaque position avec UIC_xxx fait une requête API.

2. **Rate limiting** : L'API Saxo peut avoir des limites de taux. Si vous avez beaucoup de positions, envisagez d'ajouter un délai entre les requêtes.

3. **Cache** : Pour améliorer les performances, on pourrait mettre en cache les résultats de `get_asset_by_uic()` pour éviter de refaire la même requête plusieurs fois.

4. **Asset types** : Si un UIC n'est pas trouvé avec le premier asset_type, la méthode essaie d'autres types. Cela peut ralentir la recherche si beaucoup de types doivent être essayés.

## Fichiers concernés

- `apps/trading/services/sync/position_sync_service.py` : Logique de synchronisation
- `apps/trading/brokers/saxo.py` : 
  - `get_positions()` : Récupération des positions depuis Saxo
  - `get_asset_by_uic()` : Récupération des détails d'un instrument par UIC
  - `_get_account_keys()` : Récupération des clés de compte

## Références

- [Documentation API Saxo - Instrument Details](saxo_instrument_details_api.md)
- [Documentation API Saxo - Positions](https://www.developer.saxo/openapi/referencedocs/port/v1/positions/getpositions)



