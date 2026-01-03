# Migration Saxo : SIM → LIVE

**Date :** 29 Décembre 2025  
**Objectif :** Migrer l'environnement Saxo Bank de SIM vers LIVE pour éviter les erreurs `NoAccess` sur les prix.

## 🔍 Analyse des fichiers à modifier

### Fichiers principaux (code actif)

1. **`backend/apps/trading/brokers/saxo.py`**
   - Ligne 121 : Défaut `'simulation'` → `'live'`
   - Lignes 126-127 : URLs SIM (sera utilisé si environment='simulation')

2. **`backend/apps/trading/services/yahoo_validator.py`**
   - Ligne 177 : Défaut URL SIM → LIVE
   - Ligne 445 : Fallback URL SIM → LIVE

3. **`backend/apps/trading/api/views.py`**
   - Ligne 252 : Fallback URL SIM → LIVE

4. **`backend/apps/trading/services/broker_service.py`**
   - Ligne 140 : Défaut `'simulation'` → `'live'`

5. **`backend/apps/trading/services/sync/asset_sync_service.py`**
   - Ligne 629 : Logique `is_sandbox` à vérifier

6. **`backend/apps/trading/models/brokers.py`**
   - Ligne 78 : Défaut `'simulation'` → `'live'` (optionnel, dépend de la stratégie)
   - Ligne 94 : Défaut `'simulation'` → `'live'` pour `saxo_environment`

### Fichiers de commandes (génération de données)

7. **`backend/apps/trading/management/commands/create_default_brokers.py`**
   - Ligne 16 : URL SIM → LIVE

8. **`backend/apps/trading/management/commands/validate_yahoo_assets.py`**
   - Ligne 265 : Défaut URL SIM → LIVE

### Fichiers de configuration/utilitaire

9. **`backend/apps/trading/utils/yahoo_config.py`**
   - Déjà configuré pour supporter les deux (pas de changement nécessaire)

### Documentation (à mettre à jour)

10. Fichiers dans `backend/docs/` - Mise à jour des exemples

## 📋 Stratégie de migration

### Option 1 : Migration complète (recommandée)
- Changer tous les défauts de `'simulation'` vers `'live'`
- Modifier les URLs hardcodées en SIM vers LIVE
- **Avantage :** Tout utilise LIVE par défaut
- **Inconvénient :** Les comptes existants doivent être mis à jour manuellement

### Option 2 : Migration partielle (sécurisée)
- Garder les défauts en SIM mais permettre la configuration
- Modifier uniquement les URLs hardcodées en fallback
- **Avantage :** Pas de changement de comportement par défaut
- **Inconvénient :** Nécessite de mettre à jour chaque compte individuellement

## ✅ Plan d'action choisi : Option 1 (Migration complète)

Nous allons changer les défauts pour utiliser LIVE, mais garder la logique conditionnelle pour permettre de revenir en SIM si nécessaire.

## 🔧 Modifications à effectuer

### 1. Fichier `saxo.py` - Défaut d'environnement

**Avant :**
```python
environment = credentials.get('environment', 'simulation')
```

**Après :**
```python
environment = credentials.get('environment', 'live')
```

### 2. Fichier `yahoo_validator.py` - URLs par défaut

**Avant :**
```python
base_url: str = "https://gateway.saxobank.com/sim/openapi"
```

**Après :**
```python
base_url: str = "https://gateway.saxobank.com/openapi"
```

### 3. Fichier `views.py` - Fallback URL

**Avant :**
```python
broker_config['base_url'] = 'https://gateway.saxobank.com/sim/openapi'
```

**Après :**
```python
broker_config['base_url'] = 'https://gateway.saxobank.com/openapi'
```

### 4. Fichier `broker_service.py` - Défaut environnement

**Avant :**
```python
credentials['environment'] = broker_account.environment or 'simulation'
```

**Après :**
```python
credentials['environment'] = broker_account.environment or 'live'
```

### 5. Fichier `models/brokers.py` - Défaut modèle

**Avant :**
```python
default='simulation',
```

**Après :**
```python
default='live',
```

### 6. Commandes management - URLs par défaut

**Avant :**
```python
'api_base_url': 'https://gateway.saxobank.com/sim/openapi',
```

**Après :**
```python
'api_base_url': 'https://gateway.saxobank.com/openapi',
```

## 🗄️ Migration de la base de données

### Script de migration pour les comptes existants

Un script de migration Django sera créé pour mettre à jour tous les comptes Saxo existants :

```python
# backend/apps/trading/management/commands/migrate_saxo_to_live.py
```

Ce script :
1. Trouve tous les `BrokerAccount` de type SAXO
2. Met à jour `environment` et `saxo_environment` vers `'live'`
3. Met à jour `api_base_url` si présent
4. Log toutes les modifications

## ✅ Checklist post-migration

- [ ] Vérifier que les credentials (CLIENT_ID, CLIENT_SECRET) sont ceux du compte LIVE
- [ ] Tester l'authentification OAuth2 avec le compte LIVE
- [ ] Tester la récupération d'un prix simple (ex: EURUSD)
- [ ] Vérifier les logs pour confirmer l'absence d'erreurs `NoAccess`
- [ ] Confirmer que le token généré est bien pour l'environnement LIVE
- [ ] Tester la synchronisation des assets
- [ ] Tester la validation Yahoo Finance

## 🧪 Tests de validation

### Test 1 : Récupération de prix

```bash
# Test avec UIC d'EURUSD (généralement 21)
curl -X GET "https://gateway.saxobank.com/openapi/trade/v1/infoprices?Uic=21&AssetType=FxSpot&FieldGroups=Quote" \
  -H "Authorization: Bearer VOTRE_TOKEN_LIVE"
```

**Réponse attendue :**
```json
{
  "Quote": {
    "Mid": 1.0850,
    "Bid": 1.0849,
    "Ask": 1.0851
  }
}
```

**Pas de :**
- `Amount: 0`
- `PriceTypeAsk: "NoAccess"`
- `PriceTypeBid: "NoAccess"`

### Test 2 : Vérification dans l'application

1. Se connecter à l'application
2. Aller dans `/brokers`
3. Cliquer sur "Synchroniser" pour un compte Saxo
4. Vérifier que la synchronisation fonctionne
5. Vérifier les logs pour confirmer l'utilisation de l'URL LIVE

## ⚠️ Points d'attention

### Si `NoAccess` persiste après migration :

1. **Vérifier les permissions du compte LIVE :**
   - Se connecter à SaxoTraderGO
   - Activer "Market Data" dans les paramètres
   - Vérifier que le compte a accès aux données de marché

2. **Vérifier le token :**
   - Le token doit être généré avec les credentials LIVE
   - Le token SIM ne fonctionnera pas avec l'environnement LIVE
   - Régénérer un token si nécessaire

3. **Vérifier les credentials :**
   - `SAXO_CLIENT_ID` et `SAXO_CLIENT_SECRET` doivent être ceux du compte LIVE
   - Les redirect URIs doivent être enregistrés pour l'environnement LIVE

4. **Instruments non disponibles :**
   - Certains instruments peuvent ne pas être disponibles en LIVE
   - Vérifier dans SaxoTraderGO si l'instrument est tradable

## 🔄 Rollback (en cas de problème)

Si des problèmes surviennent, il est possible de revenir en SIM :

1. Exécuter le script de migration en sens inverse (SIM)
2. Ou modifier manuellement les comptes dans l'admin Django
3. Ou utiliser la variable d'environnement pour forcer SIM

## 📝 Notes importantes

- ⚠️ **Attention :** Après migration, tous les nouveaux comptes Saxo utiliseront LIVE par défaut
- ⚠️ **Important :** Les tokens SIM existants ne fonctionneront pas avec LIVE
- ✅ **Recommandation :** Tester d'abord avec un compte de test avant de migrer le compte principal
- ✅ **Sécurité :** S'assurer que les credentials LIVE sont bien sécurisés










