# Stratégies V3 : quantités affichées & correctifs récents

## Qté **par trade** (min – max)

Dans **Stratégies V3**, la ligne **« Qté par trade »** (assistant + édition inline) correspond à la **taille d’ordre** ou d’un **trade simulé** sur le graphique — pas à la position totale en portefeuille.

| Interface (Strategies V3) | API / Serializer | Modèle Django `Strategy` |
|---------------------------|------------------|---------------------------|
| `target_min_quantity` (gauche) | `target_min_quantity` | `min_quantity` |
| `target_max_quantity` (droite) | `target_max_quantity` | `max_quantity` |

Les noms `target_*` sont des **alias** côté API pour le frontend ; en base, les champs s’appellent `min_quantity` et `max_quantity` (voir `StrategySerializer`).

### Rôle métier

- **`min_quantity`** : quantité **minimale par trade** pour dimensionner une **entrée** (simulation, et alignement avec certains algos comme **threshold** via `trade_size` / bornes si absentes du JSON `parameters`).
- **`max_quantity`** : quantité **maximale par trade** : la taille d’ordre calculée est **plafonnée** à cette valeur.

La taille d’ordre de base pour la simulation est **`order_size`** (dans les paramètres d’algo / JSON `parameters`) ; par défaut **1** si absent. Pour un **BUY**, la logique combine grossièrement :

1. `buyQuantity = max(order_size, min_quantity)`
2. si `max_quantity` est défini et que `buyQuantity` la dépasse → on ramène à `max_quantity`
3. si un **budget** est défini → la quantité peut encore être réduite pour respecter `budget / prix`

La simulation (`simulateTradesFromSignals`) et l’algo **threshold** (exécution réelle) peuvent s’appuyer sur ces champs lorsque les clés équivalentes ne sont pas déjà dans `parameters` (voir `Strategy.get_execution_parameters()` côté backend).

---

## Portefeuille : **min / max actions** (position totale)

Champs dédiés, **à part** de la qté par trade :

| Interface | API | Modèle Django |
|-----------|-----|---------------|
| `portfolio_min_quantity` | `portfolio_min_quantity` | `portfolio_min_quantity` (défaut `0`) |
| `portfolio_max_quantity` | `portfolio_max_quantity` | `portfolio_max_quantity` (`null` = **pas de plafond**) |

Ils bornent la **quantité totale d’actions détenues** sur l’actif de la stratégie (tous ordres / exécutions confondus) : utile pour le **backtest graphique** et pour l’**exécution threshold**, qui peut en déduire `min_qty` / `max_qty` dans les paramètres d’algo si besoin.

### « EN PORTEFEUILLE : 0.00 unités »

Ce libellé reflète la quantité **réelle** côté API (positions ouvertes liées à l’actif), pas les champs min/max de stratégie. Avec 0 unités en portefeuille, le backtest peut quand même montrer des trades simulés à partir des **signaux** historiques.

---

## Correctifs récents (à déployer ensemble)

1. **Ordres & catalogue AllAssets**  
   - `POST /api/orders/place/` : enregistrement de `all_asset` sur l’ordre.  
   - Création / sync / backfill : résolution `AllAssets` via l’`Asset` (symbole normalisé, ex. `V:xnys` → `V`).  
   - `POST /api/orders/backfill-all-asset/` : réparation des liens existants.

2. **Frontend**  
   - Appel optionnel au backfill à l’ouverture du modal « Créer depuis le portefeuille » (Strategies V3).  
   - **AISellModal** : correction d’une expression orpheline après `useEffect` qui provoquait une interprétation erronée type `useEffect(...)()` en production.

3. **Graphique Stratégies**  
   - Prise en compte des qtés **par trade** (`target_min_quantity` / `target_max_quantity`) et des bornes **portefeuille** (`portfolio_min_quantity` / `portfolio_max_quantity`) dans `StrategyVisualizationChart` et la simulation (`strategyPerformance`).

---

## Déploiement (base de données)

Après récupération du code, appliquer la migration des bornes portefeuille :

```bash
cd backend && python manage.py migrate
```

La migration concernée est `trading.0025_strategy_portfolio_bounds`. Elle doit être exécutée sur l’environnement où les identifiants PostgreSQL / Supabase sont valides.

---

*Dernière mise à jour : 2026-05-02.*
