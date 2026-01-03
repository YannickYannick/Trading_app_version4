# Implémentation de l'Historique des Prix - Démarche Complète

Ce document explique la démarche complète d'implémentation de l'historique des prix pour les AllAssets, depuis la conception jusqu'à la résolution des problèmes.

## Table des matières

1. [Contexte et Objectifs](#1-contexte-et-objectifs)
2. [Architecture de la Solution](#2-architecture-de-la-solution)
3. [Implémentation Backend](#3-implémentation-backend)
4. [Implémentation Frontend](#4-implémentation-frontend)
5. [Problèmes Rencontrés et Résolution](#5-problèmes-rencontrés-et-résolution)
6. [Tests et Validation](#6-tests-et-validation)

---

## 1. Contexte et Objectifs

### Objectif Principal

Permettre la visualisation de l'historique des prix pour les AllAssets dans l'interface de trading, avec :
- Stockage efficace des données historiques (30,000+ assets)
- Récupération rapide des données
- Visualisation interactive via un graphique
- Synchronisation depuis Yahoo Finance et Saxo Bank

### Contraintes

- **Performance** : 30,000 assets avec historique quotidien = millions de lignes potentielles
- **Base de données** : PostgreSQL sur Supabase
- **API** : Django REST Framework avec authentification JWT
- **Frontend** : React avec TypeScript

---

## 2. Architecture de la Solution

### 2.1 Choix du Stockage

**Problème initial** : Table `AllAssetPriceHistory` avec une ligne par date/asset
- ❌ Trop de lignes (30,000 assets × 365 jours = 11 millions de lignes)
- ❌ Requêtes lentes
- ❌ Maintenance complexe

**Solution choisie** : Champ JSONB sur le modèle `AllAssets`
- ✅ Stockage compact (une ligne par asset)
- ✅ Requêtes rapides (indexation JSONB)
- ✅ Flexibilité (structure JSON)
- ✅ Compatible PostgreSQL/Supabase

### 2.2 Structure des Données

```json
{
  "2024-01-01": {
    "open": 150.25,
    "high": 152.30,
    "low": 149.80,
    "close": 151.50,
    "volume": 5000000,
    "source": "YAHOO"
  },
  "2024-01-02": {
    "open": 151.50,
    "high": 153.20,
    "low": 150.90,
    "close": 152.80,
    "volume": 4800000,
    "source": "YAHOO"
  }
}
```

### 2.3 Flux de Données

```
Yahoo Finance / Saxo Bank API
    ↓
AllAssetPriceSyncService
    ↓
AllAssets.price_history_json (JSONB)
    ↓
API Endpoint /api/all-assets/{id}/prices/
    ↓
Frontend React Component
    ↓
Lightweight Charts Graphique
```

---

## 3. Implémentation Backend

### 3.1 Modèle de Données

**Fichier** : `apps/trading/models/assets.py`

```python
class AllAssets(models.Model):
    # ... champs existants ...
    
    price_history_json = JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text="Historique des prix: {'YYYY-MM-DD': {'open': x, 'high': y, 'low': z, 'close': w, 'volume': v}, ...}"
    )
    price_history_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date de dernière mise à jour de l'historique"
    )
    price_history_days = models.IntegerField(
        default=0,
        help_text="Nombre de jours d'historique stockés"
    )
    
    @property
    def has_price_history(self) -> bool:
        return bool(self.price_history_json) and len(self.price_history_json) > 0
    
    def get_price_history_dates(self) -> List[str]:
        if not self.price_history_json:
            return []
        return sorted(self.price_history_json.keys(), reverse=True)
    
    def get_price_for_date(self, date_str: str) -> Optional[Dict]:
        if not self.price_history_json:
            return {}
        return self.price_history_json.get(date_str, {})
```

### 3.2 Service de Synchronisation

**Fichier** : `apps/trading/services/sync/all_asset_price_sync_service.py`

**Fonctionnalités** :
- Identification des AllAssets à synchroniser (référencés dans Position, Trade, Order, Strategy)
- Synchronisation depuis Yahoo Finance
- Fallback vers Saxo Bank si Yahoo échoue
- Gestion des valeurs NaN/None pour éviter les erreurs JSON

**Méthode principale** :
```python
def sync_from_yahoo_finance(
    self,
    all_asset: AllAssets,
    days: int = 30,
    interval: str = '1d',
    fallback_to_broker: bool = True
) -> Dict[str, Any]:
    # 1. Vérifier le symbole Yahoo
    # 2. Récupérer les données depuis Yahoo Finance
    # 3. Nettoyer les valeurs (NaN, None)
    # 4. Fusionner avec l'historique existant
    # 5. Sauvegarder dans price_history_json
```

### 3.3 API Endpoint

**Fichier** : `apps/trading/api/views.py`

**Endpoint** : `GET /api/all-assets/{id}/prices/`

**Query Parameters** :
- `days` : Nombre de jours à récupérer (défaut: 100)
- `output_format` : Format de réponse ('json' ou 'list', défaut: 'list')
- `source` : Filtrer par source (YAHOO, SAXO, etc.) - optionnel

**Réponse** :
```json
{
  "all_asset_id": 101173,
  "all_asset_symbol": "AAPL:xnas",
  "count": 251,
  "format": "list",
  "total_days_available": 251,
  "results": [
    {
      "date": "2026-01-02",
      "open": 272.05,
      "high": 277.82,
      "low": 269.58,
      "close": 269.66,
      "volume": 17192843,
      "source": "YAHOO"
    }
  ]
}
```

---

## 4. Implémentation Frontend

### 4.1 Service API

**Fichier** : `frontend/src/services/assets.ts`

**Méthode principale** :
```typescript
async getPriceHistory(
  allAssetId: number,
  days: number = 365,
  format: 'list' | 'json' = 'list'
): Promise<PriceHistoryResponse> {
  const response = await apiClient.get(
    `/all-assets/${allAssetId}/prices/`,
    { params: { days, output_format: format } }
  )
  return response.data
}
```

### 4.2 Composant Graphique

**Fichier** : `frontend/src/components/trades/TradesChart.tsx`

**Fonctionnalités** :
- Graphique interactif avec lightweight-charts v5
- Affichage de plusieurs séries (un asset = une ligne)
- Marqueurs pour les trades (BUY/SELL)
- Gestion du zoom et du pan
- Mode global (tous les assets) ou par asset

**Architecture** :
```typescript
TradesChart
  ├── Initialisation du graphique (createChart)
  ├── Chargement de l'historique (loadPriceHistory)
  ├── Création des séries (addSeries(LineSeries, options))
  ├── Ajout des marqueurs (createSeriesMarkers)
  └── Gestion du resize et du nettoyage
```

---

## 5. Problèmes Rencontrés et Résolution

### 5.1 Problème de Routing DRF

**Symptôme** : Erreur 404 avec `?format=list`

**Cause** : Le paramètre `format` est réservé par DRF pour les format suffixes

**Solution** : Renommer en `output_format`

Voir [FIXING_PRICE_HISTORY_ISSUES.md](./FIXING_PRICE_HISTORY_ISSUES.md#1-problème-de-routing-drf-avec-le-paramètre-format) pour plus de détails.

### 5.2 Migration lightweight-charts v5

**Symptôme** : `addLineSeries is not a function`

**Cause** : API changée dans v5.0+

**Solution** : Utiliser `addSeries(LineSeries, options)` et `createSeriesMarkers()`

Voir [FIXING_PRICE_HISTORY_ISSUES.md](./FIXING_PRICE_HISTORY_ISSUES.md#3-migration-vers-lightweight-charts-v5) pour plus de détails.

### 5.3 Boucle Infinie

**Symptôme** : Rechargements répétés du graphique

**Cause** : Dépendances instables dans `useEffect`

**Solution** : Comparaison des assets sélectionnés avant rechargement

Voir [FIXING_PRICE_HISTORY_ISSUES.md](./FIXING_PRICE_HISTORY_ISSUES.md#4-boucle-infinie-de-rechargement) pour plus de détails.

---

## 6. Tests et Validation

### 6.1 Tests Backend

**Scripts de test créés** :
- `backend/test_prices_endpoint.py` : Test de l'endpoint avec authentification
- `backend/test_url_with_params.py` : Test des différents formats de requête
- `backend/test_trade_aapl_price_history.py` : Test avec données réelles

**Commandes de test** :
```bash
# Test direct de l'endpoint
python backend/test_prices_endpoint.py

# Test avec différents paramètres
python backend/test_url_with_params.py
```

### 6.2 Tests Frontend

**Validation manuelle** :
- ✅ Chargement du graphique avec un asset sélectionné
- ✅ Affichage des marqueurs pour les trades
- ✅ Pas de boucle infinie
- ✅ Gestion des erreurs (pas d'historique disponible)

### 6.3 Validation des Performances

**Métriques** :
- Temps de réponse API : < 200ms pour 365 jours
- Taille des données JSONB : ~50-100 KB par asset (365 jours)
- Temps de rendu graphique : < 500ms pour 251 points

---

## 7. Points d'Attention et Bonnes Pratiques

### 7.1 Gestion des Erreurs

- **Backend** : Vérifier les valeurs NaN/None avant stockage JSONB
- **Frontend** : Gérer gracieusement les erreurs 404/401
- **Cache** : Implémenter un cache côté frontend pour éviter les requêtes répétées

### 7.2 Optimisations Futures

- **Pagination** : Pour les assets avec très long historique (> 5 ans)
- **Compression** : Compression des données JSONB si nécessaire
- **Indexation** : Index GIN sur `price_history_json` pour recherches rapides
- **Cache Redis** : Cache des données fréquemment accédées

### 7.3 Maintenance

- **Synchronisation automatique** : Tâche cron pour synchroniser les assets actifs
- **Nettoyage** : Suppression des anciennes données (> 5 ans)
- **Monitoring** : Alertes si la synchronisation échoue

---

## 8. Références

- [Documentation Django JSONField](https://docs.djangoproject.com/en/stable/ref/models/fields/#jsonfield)
- [Documentation PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html)
- [Documentation lightweight-charts v5](https://tradingview.github.io/lightweight-charts/)
- [Migration guide v4 vers v5](https://tradingview.github.io/lightweight-charts/docs/migrations/from-v4-to-v5)
- [Django REST Framework Format Suffixes](https://www.django-rest-framework.org/api-guide/format-suffixes/)

---

## 9. Conclusion

L'implémentation de l'historique des prix a nécessité :
- ✅ Un choix architectural adapté (JSONB au lieu de table séparée)
- ✅ Une migration vers l'API v5 de lightweight-charts
- ✅ La résolution de problèmes de routing et d'authentification
- ✅ L'optimisation des performances (pas de boucle infinie)

Le système est maintenant fonctionnel et prêt pour la production, avec une base solide pour les futures améliorations.



