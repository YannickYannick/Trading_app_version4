# Correction UIC Saxo et Optimisations

## Date
29 Décembre 2025

## Problème Identifié

### 1. UIC non sauvegardé
Lors de la synchronisation des assets Saxo, l'UIC (Unique Instrument Code) n'était pas sauvegardé dans la base de données. Tous les `AllAssets` pour Saxo avaient `saxo_uic = NULL`.

### 2. Cause Racine
Le code cherchait le champ `'Uic'` dans la réponse de l'API `/ref/v1/instruments`, mais l'API Saxo retourne en réalité le champ `'Identifier'` pour cet endpoint.

**Code problématique :**
```python
# ❌ MAUVAIS
uic_value = item.get('Uic')  # Retourne toujours None
```

**Réponse réelle de l'API :**
```json
{
  "Identifier": 57321,  // ✅ C'est ça !
  "Symbol": "ENEL:xmil",
  "Description": "Enel SpA",
  ...
}
```

### 3. Performance
La synchronisation était très lente car elle utilisait `update_or_create` en boucle pour chaque asset (20 000 requêtes SQL pour 20 000 assets).

### 4. Timeout Frontend
Le frontend timeout après 30 secondes, alors que la synchronisation de 20 000 assets prend plusieurs minutes.

---

## Solutions Implémentées

### 1. Correction Extraction UIC

**Fichier :** `backend/apps/trading/brokers/saxo.py`

**Changement :**
```python
# ✅ CORRECT
uic_value = item.get('Identifier')  # Utilise le bon champ
```

**Détails :**
- Utilisation de `'Identifier'` au lieu de `'Uic'` pour l'endpoint `/ref/v1/instruments`
- Conservation de l'UIC original dans `raw_data['identifier']` et `raw_data['uic']`
- Validation et conversion en entier avant sauvegarde
- Logging détaillé pour diagnostiquer les UIC manquants

### 2. Extraction UIC avec Fallback

**Fichier :** `backend/apps/trading/services/sync/asset_sync_service.py`

**Logique d'extraction :**
```python
# 1. Essayer depuis broker_id (string)
if broker_asset.broker_id and broker_asset.broker_id.strip():
    uic_value = int(broker_asset.broker_id)

# 2. Fallback : vérifier dans raw_data['uic']
if uic_value is None and broker_asset.raw_data:
    raw_uic = broker_asset.raw_data.get('uic')
    if raw_uic:
        uic_value = int(raw_uic)
```

### 3. Optimisation Bulk Operations

**Avant :**
```python
# ❌ LENT : 1 requête SQL par asset
for asset in assets:
    AllAssets.objects.update_or_create(...)  # 20 000 requêtes !
```

**Après :**
```python
# ✅ RAPIDE : 1 requête SQL par batch de 500
AllAssets.objects.bulk_create(assets_to_create, ignore_conflicts=False)
AllAssets.objects.bulk_update(assets_to_update, update_fields)
# ~40 requêtes pour 20 000 assets
```

**Amélioration de performance :**
- **Avant** : ~20 000 requêtes SQL = très lent
- **Après** : ~40 requêtes SQL = beaucoup plus rapide

### 4. Gestion des Champs Spécifiques par Plateforme

**Problème :** Les champs Binance (`binance_base_asset`, etc.) sont des `CharField` avec `blank=True` mais pas `null=True`, donc ils n'acceptent pas `None`.

**Solution :**
```python
# Pour SAXO : ne pas inclure les champs Binance
if platform == 'SAXO':
    defaults['saxo_uic'] = uic_value
    # Pas de champs Binance (seront des chaînes vides par défaut)

# Pour BINANCE : inclure les champs Binance avec chaînes vides si absents
elif platform == 'BINANCE':
    defaults['binance_base_asset'] = getattr(asset, 'binance_base_asset', '')
    defaults['binance_quote_asset'] = getattr(asset, 'binance_quote_asset', '')
    defaults['binance_status'] = getattr(asset, 'binance_status', '')
```

### 5. Timeout Frontend Augmenté

**Fichier :** `frontend/src/services/brokers.ts`

**Changements :**
```typescript
// Méthode sync()
async sync(...) {
  const response = await apiClient.post(
    `/broker-accounts/${accountId}/sync/`,
    syncRequest,
    {
      timeout: 600000, // 10 minutes au lieu de 30 secondes
    }
  )
}

// Méthode validateYahooSymbols()
async validateYahooSymbols(...) {
  const response = await apiClient.post(
    '/all-assets/validate-yahoo-symbols/',
    options || {},
    {
      timeout: 600000, // 10 minutes
    }
  )
}
```

### 6. Handler Logging Sécurisé pour Windows

**Fichier :** `backend/config_django/settings/base.py`

**Problème :** Sur Windows, la rotation des fichiers de log échoue avec `PermissionError` car le fichier est verrouillé.

**Solution :** Création d'un handler personnalisé qui ignore les erreurs de rotation :

```python
class SafeRotatingFileHandler(logging.handlers.RotatingFileHandler):
    def doRollover(self):
        try:
            super().doRollover()
        except (PermissionError, OSError):
            pass  # Ignorer les erreurs de permission sur Windows
```

---

## Résultats

### Tests de Vérification

**Statistiques après correction :**
- ✅ **100% des assets SAXO ont leur UIC** (28 848/28 848)
- ✅ **0 asset sans UIC**
- ✅ UIC correctement extrait depuis `'Identifier'`
- ✅ UIC correctement sauvegardé dans `AllAssets.saxo_uic`

**Exemples vérifiés :**
- `NVDA:xnas` → `saxo_uic=1249`
- `AMD:xnas` → `saxo_uic=1422226`
- `TSLA:xnas` → `saxo_uic=47556`

### Performance

- **Synchronisation** : ~40 requêtes SQL au lieu de 20 000
- **Temps de synchronisation** : Réduit de manière significative
- **Timeout** : Plus de problème de timeout pour les synchronisations longues

---

## Fichiers Modifiés

1. **`backend/apps/trading/brokers/saxo.py`**
   - Correction extraction UIC : `item.get('Identifier')`
   - Logging amélioré

2. **`backend/apps/trading/services/sync/asset_sync_service.py`**
   - Optimisation bulk operations
   - Gestion UIC avec fallback
   - Logging détaillé

3. **`backend/config_django/settings/base.py`**
   - Handler logging sécurisé pour Windows

4. **`frontend/src/services/brokers.ts`**
   - Timeout augmenté à 10 minutes pour sync et validateYahooSymbols

---

## Impact sur la Validation Yahoo Finance

Maintenant que l'UIC est sauvegardé pour tous les assets Saxo, la validation Yahoo Finance peut :
- ✅ Récupérer le prix de référence depuis Saxo via l'UIC
- ✅ Comparer avec les prix Yahoo Finance
- ✅ Valider correctement les symboles Yahoo

---

## Notes Techniques

### Endpoints Saxo API

- **`/ref/v1/instruments`** → Retourne `'Identifier'` (pas `'Uic'`)
- **`/port/v1/positions`** → Retourne `'Uic'` (correct pour positions)
- **`/hist/v1/transactions`** → Retourne `'Uic'` (correct pour transactions)

Donc seule l'extraction dans `get_assets()` nécessitait la correction.

### Bulk Operations vs Individual Operations

**bulk_create/bulk_update :**
- ✅ Beaucoup plus rapide (requêtes groupées)
- ✅ Moins de charge sur la base de données
- ⚠️ Nécessite de séparer les assets à créer vs mettre à jour avant

**update_or_create en boucle :**
- ❌ Très lent (1 requête par asset)
- ❌ Charge élevée sur la base de données
- ✅ Plus simple à implémenter

---

## Recommandations Futures

1. **Synchronisation Asynchrone** : Pour les très grandes synchronisations, envisager d'utiliser des tâches asynchrones (Celery) avec suivi de progression
2. **Cache UIC** : Mettre en cache les UIC pour éviter les requêtes répétées
3. **Monitoring** : Ajouter des métriques de performance pour suivre les temps de synchronisation

---

## Références

- Issue GitHub : [Lien si applicable]
- API Saxo Documentation : https://www.developer.saxo/
- Commit : `687ab0f` - "Fix UIC extraction and saving: use 'Identifier' instead of 'Uic', optimize bulk operations, increase timeout for sync"

