# Stratégies V3 : quantités affichées & correctifs récents

## Champs « Quantité » (min – max) dans l’interface

Dans **Stratégies V3**, la ligne **Quantité** avec deux champs (ex. `0` et `2`) correspond à :

| Interface (Strategies V3) | API / Serializer | Modèle Django `Strategy` |
|---------------------------|------------------|---------------------------|
| `target_min_quantity` (gauche) | `target_min_quantity` | `min_quantity` |
| `target_max_quantity` (droite) | `target_max_quantity` | `max_quantity` |

Les noms `target_*` sont des **alias** côté API pour le frontend ; en base, les champs s’appellent `min_quantity` et `max_quantity` (voir `StrategySerializer`).

### Rôle métier

- **`min_quantity`** : quantité **minimale** utilisée pour dimensionner une **entrée** en position lors de la **simulation** du graphique (backtest sur l’historique). Elle sert aussi de plancher quand un **budget** est renseigné (voir `simulateTradesFromSignals` dans `frontend/src/utils/strategyPerformance.ts`).
- **`max_quantity`** : quantité **maximale** par position simulée : la taille calculée est **plafonnée** à cette valeur.

La taille d’ordre de base pour la simulation est **`order_size`** (dans les paramètres d’algo / JSON `parameters`) ; par défaut **1** si absent. Pour un **BUY**, la logique combine grossièrement :

1. `buyQuantity = max(order_size, min_quantity)`
2. si `max_quantity` est défini et que `buyQuantity` la dépasse → on ramène à `max_quantity`
3. si un **budget** est défini → la quantité peut encore être réduite pour respecter `budget / prix`

Les libellés du modèle Django indiquent « quantité minimale / maximale d’achat » ; la même structure est réutilisée pour la partie **SELL** / short dans la simulation (avec `Math.abs(min_quantity)` comme plancher côté vente).

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
   - Prise en compte de `target_min_quantity` / `target_max_quantity` dans `StrategyVisualizationChart` (alignement avec les champs saisis dans V3).

---

*Dernière mise à jour : 2026-05-02.*
