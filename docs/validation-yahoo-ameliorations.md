# Améliorations de la validation Yahoo Finance

## 📋 Résumé

Ce document décrit les améliorations apportées au système de validation Yahoo Finance, incluant :
- Support des batches progressifs
- Filtrage par assets existants
- Interface utilisateur améliorée
- Amélioration du logging et diagnostic

## 🎯 Nouvelles fonctionnalités

### 1. Validation par batches

#### Problème résolu
Permet de valider un nombre limité d'assets à la fois, sans retraiter ceux déjà validés.

#### Utilisation

**Commande Django :**
```bash
# Valider 50 assets supplémentaires
python manage.py validate_yahoo_assets --broker=SAXO --limit=50

# Relancer pour valider 50 autres (différents car les premiers sont maintenant validés)
python manage.py validate_yahoo_assets --broker=SAXO --limit=50
```

**API :**
```bash
POST /api/all-assets/validate-yahoo-symbols/
{
  "limit": 50,
  "reset": false,
  "onlyExistingAssets": false
}
```

**Interface web :**
Dans la modale de validation, utilisez le champ "Limite" pour spécifier le nombre d'assets.

#### Fonctionnement
- Les assets validés changent leur `symbole_yahoo` de `'Not_searched'` vers le symbole Yahoo trouvé
- Le filtre `symbole_yahoo='Not_searched'` exclut automatiquement ceux déjà validés
- L'ordre stable par ID garantit que chaque batch prend toujours les mêmes assets dans le même ordre
- Chaque exécution traite les N prochains assets non validés

### 2. Filtrage par assets existants

#### Problème résolu
Limiter la validation uniquement aux assets qui existent dans le modèle `Asset` (ceux visibles dans `/admin/trading/asset/`).

#### Utilisation

**Commande Django :**
```bash
python manage.py validate_yahoo_assets --broker=SAXO --only-existing-assets
python manage.py validate_yahoo_assets --broker=SAXO --only-existing-assets --limit=50
```

**API :**
```bash
POST /api/all-assets/validate-yahoo-symbols/
{
  "onlyExistingAssets": true,
  "limit": 50
}
```

**Interface web :**
Cochez la case "Uniquement les assets existants (du modèle Asset)" dans la modale.

#### Fonctionnement
- Récupère les IDs des `AllAssets` qui ont au moins un `Asset` associé
- Filtre le queryset pour ne garder que ces assets
- Évite de valider des assets non utilisés dans l'application

### 3. Reset des assets "not_found"

#### Utilisation

**Commande Django :**
```bash
python manage.py validate_yahoo_assets --broker=SAXO --reset-not-found
```

**API :**
```bash
POST /api/all-assets/validate-yahoo-symbols/
{
  "reset": true
}
```

**Interface web :**
Cochez la case "Reset (revalider les assets marqués 'not_found')" dans la modale.

#### Fonctionnement
- Réinitialise le `symbole_yahoo` des assets marqués `'not_found'` vers `'Not_searched'`
- Permet de réessayer la validation si les conditions ont changé (ex: permissions Market Data activées)

## 🎨 Interface utilisateur

### Modale de validation

La modale de validation Yahoo Finance dans l'interface web (`/brokers`) offre maintenant :

1. **Champ "Limite"** : Input numérique pour spécifier le nombre d'assets à valider
2. **Checkbox "Reset"** : Pour revalider les assets marqués "not_found"
3. **Checkbox "Uniquement les assets existants"** : Pour limiter aux assets du modèle Asset

### Paramètres par défaut
- **Limite** : 100 assets
- **Reset** : Non
- **Uniquement assets existants** : Non

## 📊 Logging et diagnostic

### Améliorations du logging

#### Dans `yahoo_validator.py`
- Détection automatique de l'environnement (SIM/LIVE) depuis l'URL
- Messages d'erreur détaillés pour diagnostiquer les problèmes
- Détection des erreurs 401 (token invalide pour l'environnement)
- Logging des URLs complètes utilisées

**Exemple de log amélioré :**
```
🔍 Getting Saxo price for UIC 1125560 (Stock) - Environment: LIVE, URL: https://gateway.saxobank.com/openapi, Token: eyJhbGciOiJFUzI1NiIs...
❌ LIVE MODE: Price access denied for UIC 1125560 (PriceTypeAsk=NoAccess, PriceTypeBid=NoAccess). 
⚠️ Possible causes: 1) Token SIM used with LIVE URL, 2) Market Data subscription not activated, 
3) Instrument not available for this account. URL used: https://gateway.saxobank.com/openapi
```

#### Dans `saxo.py`
- Affichage de l'environnement et de l'URL lors de l'initialisation
- Aperçu du token pour faciliter le débogage

### Script de diagnostic

Un nouveau script de test a été créé : `backend/test_saxo_live_connection.py`

**Usage :**
```bash
cd backend
python test_saxo_live_connection.py
```

**Fonctionnalités :**
- Teste la connexion à l'API Saxo LIVE
- Vérifie la validité du token pour l'environnement
- Teste l'accès aux prix pour différents instruments
- Fournit un diagnostic automatique du problème

## 🔧 Administration Django

### Filtre personnalisé dans l'admin

Dans `/admin/trading/allassets/`, un nouveau filtre "Validation Yahoo" permet de :

- **Validés** : Voir uniquement les assets avec un symbole Yahoo valide
- **Non recherchés** : Voir les assets pas encore traités
- **Non trouvés** : Voir les assets pour lesquels aucun symbole Yahoo n'a été trouvé
- **Validation manuelle** : Voir les assets nécessitant une validation manuelle

### Affichage amélioré

Le champ `symbole_yahoo` est maintenant visible dans la liste des assets dans l'admin pour voir rapidement le statut de validation.

### Accès aux tokens Saxo

Dans `/admin/trading/brokeraccount/`, la section "Credentials Saxo Bank" contient maintenant :
- Les champs `saxo_access_token` et `saxo_refresh_token` dans des zones de texte larges
- Les tokens sont éditables directement dans l'interface
- La section est repliable par défaut pour la sécurité

## 📝 Paramètres de la commande Django

### Nouveaux paramètres

```bash
python manage.py validate_yahoo_assets \
  --broker=SAXO \
  --limit=50 \
  --batch-size=50 \
  --only-existing-assets \
  --reset-not-found \
  --asset-type=Stock \
  --workers=2 \
  --tolerance=5.0 \
  --dry-run
```

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| `--limit` | Nombre d'assets à valider dans ce batch | Aucune limite |
| `--batch-size` | Alias pour `--limit` | Aucune limite |
| `--only-existing-assets` | Filtrer uniquement les assets du modèle Asset | False |
| `--reset-not-found` | Revalider les assets marqués "not_found" | False |
| `--broker` | Broker source (obligatoire) | - |
| `--asset-type` | Type d'actif à filtrer | Tous |
| `--workers` | Nombre de threads parallèles | 2 |
| `--tolerance` | Tolérance de prix en % | 5.0 |
| `--dry-run` | Exécuter sans sauvegarder | False |

## 🔍 Résolution des problèmes

### Problème : NoAccess sur les prix Saxo

**Diagnostic :**
1. Exécuter le script de test : `python test_saxo_live_connection.py`
2. Vérifier les logs pour identifier l'environnement utilisé
3. Vérifier si le problème vient d'un mismatch Token/URL ou des permissions Market Data

**Solutions :**
- Si erreur 401 : Token incompatible avec l'environnement (SIM vs LIVE)
- Si NoAccess : Permissions Market Data non activées dans SaxoTraderGO

**Documentation :**
- `docs/probleme-validation-yahoo.md` - Description du problème
- `docs/test-results-saxo-diagnostic.md` - Résultats des tests
- `docs/correction-probleme-yahoo.md` - Guide de correction

## 📚 Fichiers modifiés

### Backend
- `backend/apps/trading/management/commands/validate_yahoo_assets.py` - Support des batches et nouveaux paramètres
- `backend/apps/trading/services/yahoo_validator.py` - Logging amélioré
- `backend/apps/trading/brokers/saxo.py` - Logging amélioré
- `backend/apps/trading/api/views.py` - Support du paramètre `onlyExistingAssets`
- `backend/apps/trading/admin.py` - Filtre personnalisé et affichage amélioré
- `backend/test_saxo_live_connection.py` - Script de diagnostic (nouveau)

### Frontend
- `frontend/src/components/brokers/YahooValidationModal.tsx` - Interface avec paramètres configurables
- `frontend/src/components/brokers/YahooValidationModal.css` - Styles pour les nouveaux champs
- `frontend/src/services/brokers.ts` - Support du paramètre `onlyExistingAssets`

### Documentation
- `docs/validation-yahoo-ameliorations.md` - Ce fichier (nouveau)
- `docs/probleme-validation-yahoo.md` - Mise à jour avec les résultats des tests
- `docs/test-results-saxo-diagnostic.md` - Résultats des tests de diagnostic (nouveau)
- `docs/correction-probleme-yahoo.md` - Guide de correction (nouveau)

## 🚀 Exemples d'utilisation

### Exemple 1 : Validation progressive
```bash
# Premier batch de 50 assets
python manage.py validate_yahoo_assets --broker=SAXO --limit=50

# Deuxième batch de 50 assets (différents des premiers)
python manage.py validate_yahoo_assets --broker=SAXO --limit=50

# Continuer jusqu'à validation complète
```

### Exemple 2 : Valider uniquement les assets utilisés
```bash
python manage.py validate_yahoo_assets \
  --broker=SAXO \
  --only-existing-assets \
  --limit=100
```

### Exemple 3 : Réessayer les assets "not_found"
```bash
python manage.py validate_yahoo_assets \
  --broker=SAXO \
  --reset-not-found \
  --limit=50
```

### Exemple 4 : Validation via l'interface web
1. Aller sur `/brokers`
2. Cliquer sur le bouton de validation Yahoo
3. Configurer les paramètres dans la modale :
   - Limite : 50
   - Reset : Non
   - Uniquement assets existants : Oui
4. Cliquer sur "Démarrer la validation"

## ⚠️ Notes importantes

1. **Ordre stable** : Les assets sont triés par ID pour garantir un ordre reproductible
2. **Pas de doublons** : Le filtre `symbole_yahoo='Not_searched'` empêche de retraiter les assets déjà validés
3. **Permissions Market Data** : Les erreurs NoAccess nécessitent l'activation des permissions dans SaxoTraderGO
4. **Environnement Token/URL** : Le token doit correspondre à l'environnement (SIM token → SIM URL, LIVE token → LIVE URL)

## 🔗 Références

- [Documentation du problème initial](./probleme-validation-yahoo.md)
- [Résultats des tests de diagnostic](./test-results-saxo-diagnostic.md)
- [Guide de correction](./correction-probleme-yahoo.md)

