# Diagramme “catégories” (secteur/ETF/crypto/cash) — heuristiques + overrides UI

Objectif : afficher une répartition **pour tout le portefeuille**, même quand Yahoo ne fournit pas `sector/industry` (ETF/ETC/FX).

## Où c’est affiché

- Dashboard : `frontend/src/pages/Dashboard.tsx`
- Composant : `frontend/src/components/dashboard/PortfolioCategoryChart.tsx`

## Données utilisées

Positions ouvertes via `/api/positions/` (liste), avec champs `all_asset_*` enrichis :
- `all_asset_sector`, `all_asset_industry` (si Yahoo)
- `all_asset_platform`, `all_asset_asset_type`, `all_asset_currency` (pour heuristiques)

Cash :
- `kpi.total_cash` depuis `GET /api/analytics/summary/`

## Heuristiques automatiques (résumé)

Implémentation : `frontend/src/utils/portfolioCategory.ts`

Priorité :
1) **Override manuel** (si défini)  
2) **BINANCE → Crypto** (stablecoins → `Crypto:Stablecoin`)  
3) **Actions** : si `sector` existe → `Actions:{sector}`  
4) **ETF/ETC/ETN** : détection par `asset_type` ou mots-clés du `name` (UCITS/ETF/ETC/ETN/Index…) puis catégories :
   - `ETF:Equity`, `ETF:Equity_World`, `ETF:Equity_Europe`, `ETF:Bond`, `ETF:Other`
   - Commodities : `Commodity:Gold`, `Commodity:Oil`
5) **FX** : `FxSpot`, symboles type `EUR/USD` ou suffixe `=X`  
6) **Cash** : symboles type `EUR` / `USD` (3 lettres)  
7) fallback : `Other`

## Overrides manuels (UI)

Dans le graphique, bouton **Overrides** :
- Permet de forcer une catégorie par symbole `AllAssets.symbol`
- Stockage : `localStorage` (clé `portfolio_category_overrides_v1`)
- Un override est **prioritaire** sur toutes les heuristiques

## Backend (champs ajoutés sur la liste positions)

Serializer : `backend/apps/trading/api/serializers.py` (`PositionListSerializer`)
- Ajouts : `all_asset_platform`, `all_asset_asset_type`, `all_asset_currency`

