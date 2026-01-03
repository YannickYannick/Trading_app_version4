# Actions en lot dans l'administration Django

## Vue d'ensemble

Des actions en lot ont été ajoutées pour faciliter la validation des symboles Yahoo et la synchronisation de l'historique des prix directement depuis les pages de liste de l'administration Django.

## Modèles concernés

Les actions en lot sont disponibles pour les modèles suivants :
- **Position** (`/admin/trading/position/`)
- **Trade** (`/admin/trading/trade/`)
- **Order** (`/admin/trading/order/`)
- **Strategy** (`/admin/trading/strategy/`)

## Fonctionnalités

### 1. Validation des symboles Yahoo (Action en lot)

**Action** : `validate_yahoo_bulk`

Permet de valider les symboles Yahoo Finance pour tous les AllAssets uniques associés aux objets sélectionnés.

**Utilisation** :
1. Sur la page de liste (ex: `/admin/trading/position/`)
2. Sélectionner les objets souhaités en cochant les cases
3. Dans le menu déroulant "Action" en haut de la page, choisir **"🔍 Valider les symboles Yahoo des AllAssets sélectionnés"**
4. Cliquer sur "Go"

**Comportement** :
- Collecte automatiquement tous les AllAssets uniques (évite les doublons)
- Valide chaque AllAsset via le service de validation Yahoo
- Pour les assets Saxo, récupère automatiquement un token d'accès valide
- Sauvegarde les résultats (symbole Yahoo, méthode de validation, date)
- Affiche un message récapitulatif avec le nombre de réussites et d'erreurs

**Optimisation** : Si plusieurs objets partagent le même AllAsset, celui-ci n'est traité qu'une seule fois.

### 2. Synchronisation de l'historique des prix (Action en lot)

**Action** : `sync_history_bulk`

Permet de charger l'historique des prix depuis Yahoo Finance pour tous les AllAssets uniques associés aux objets sélectionnés.

**Utilisation** :
1. Sur la page de liste (ex: `/admin/trading/position/`)
2. Sélectionner les objets souhaités en cochant les cases
3. Dans le menu déroulant "Action", choisir **"📊 Synchroniser l'historique des prix des AllAssets sélectionnés"**
4. Cliquer sur "Go"

**Paramètres par défaut** :
- **Durée** : 365 jours (1 an)
- **Intervalle** : 1 jour (`1d`)

**Comportement** :
- Collecte automatiquement tous les AllAssets uniques (évite les doublons)
- Synchronise l'historique depuis Yahoo Finance pour chaque AllAsset
- Stocke les données dans le champ JSONB `price_history_json` de l'AllAsset
- Affiche un message récapitulatif avec le nombre de réussites, d'erreurs et le total d'enregistrements

**Optimisation** : Si plusieurs objets partagent le même AllAsset, celui-ci n'est traité qu'une seule fois.

## Actions individuelles (Pages de détail)

Sur chaque page de détail d'un objet (Position, Trade, Order, Strategy), deux boutons sont disponibles si l'objet a un AllAsset associé :

### 1. Valider symbole Yahoo

- **Bouton** : 🔍 Valider symbole Yahoo
- **Fonction** : Valide le symbole Yahoo Finance pour l'AllAsset de cet objet
- **Réaction** : Affiche un message de succès/erreur et recharge la page après 2 secondes

### 2. Charger l'historique

- **Bouton** : 📊 Charger l'historique
- **Options** :
  - **Durée** : 1 mois, 3 mois, 6 mois, 1 an, 2 ans, 5 ans
  - **Intervalle** : 1 jour, 1 semaine, 1 mois
- **Fonction** : Charge l'historique des prix depuis Yahoo Finance avec les paramètres sélectionnés
- **Réaction** : Affiche le nombre d'enregistrements synchronisés et recharge la page après 2 secondes

## Architecture technique

### Implémentation

Les actions en lot sont implémentées comme des méthodes dans les classes Admin :

```python
@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    actions = ['validate_yahoo_bulk', 'sync_history_bulk']
    
    def validate_yahoo_bulk(self, request, queryset):
        # Collecte des AllAssets uniques
        # Validation via validate_single_asset()
        # Sauvegarde des résultats
```

### Services utilisés

- **`validate_single_asset()`** : Service de validation Yahoo (`apps.trading.services.yahoo_validator`)
- **`AllAssetPriceSyncService`** : Service de synchronisation des prix (`apps.trading.services.sync.all_asset_price_sync_service`)
- **`BrokerService`** : Service pour obtenir les tokens d'accès Saxo si nécessaire

### Optimisations

1. **Déduplication** : Utilisation de `set()` pour collecter les AllAssets uniques avant traitement
2. **Authentification Saxo** : Réutilisation des instances de broker avec cache (`use_cache=True`)
3. **Gestion d'erreurs** : Chaque AllAsset est traité individuellement, les erreurs n'interrompent pas le traitement des autres

### Templates personnalisés

Chaque modèle utilise un template personnalisé pour la page de détail :
- `admin/trading/position/change_form.html`
- `admin/trading/trade/change_form.html`
- `admin/trading/order/change_form.html`
- `admin/trading/strategy/change_form.html`

Ces templates étendent `admin/change_form.html` et ajoutent une section "Actions rapides" avec les boutons JavaScript pour les actions individuelles.

## Exemples d'utilisation

### Exemple 1 : Valider tous les symboles Yahoo d'un portefeuille

1. Aller sur `/admin/trading/position/`
2. Filtrer par utilisateur ou broker si nécessaire
3. Sélectionner toutes les positions (ou un sous-ensemble)
4. Action : "🔍 Valider les symboles Yahoo des AllAssets sélectionnés"
5. Résultat : Tous les AllAssets uniques sont validés, message de récapitulatif affiché

### Exemple 2 : Charger l'historique pour une stratégie spécifique

1. Aller sur `/admin/trading/strategy/123/change/`
2. Vérifier que la stratégie a un AllAsset associé
3. Dans la section "Actions rapides", sélectionner :
   - Durée : 2 ans
   - Intervalle : 1 jour
4. Cliquer sur "📊 Charger l'historique"
5. Résultat : L'historique de 2 ans (1 prix par jour) est chargé pour l'AllAsset

## Notes importantes

1. **Permissions** : Les actions respectent les permissions Django standard (l'utilisateur doit avoir les droits d'édition)

2. **Performance** : 
   - Les actions en lot peuvent prendre du temps si de nombreux AllAssets sont sélectionnés
   - Pour Saxo, chaque validation nécessite une authentification (réutilisée si possible)

3. **Erreurs** :
   - Les erreurs pour un AllAsset spécifique sont journalisées mais n'interrompent pas le traitement des autres
   - Les messages d'erreur détaillés sont visibles dans les logs Django

4. **AllAssets manquants** :
   - Si un objet n'a pas d'AllAsset associé, il est ignoré silencieusement
   - Un message d'avertissement est affiché si aucun AllAsset n'est trouvé dans la sélection



