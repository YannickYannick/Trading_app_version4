# IA — Suggestions de diversification (page Orders)

Cette fonctionnalité ajoute, sur la page **Orders**, un bouton **« Suggérer 3 actions (IA) »**.
Il déclenche une analyse Gemini qui propose **3 actions** visant à diversifier le portefeuille actuel, avec argumentaire (fondamentaux, avantages compétitifs, macro/géopolitique, stratégie d’entreprise, horizon).

## UI (frontend)

- **Page** : `frontend/src/pages/Orders.tsx`
- **Modal** : `frontend/src/components/orders/AIDiversifyModal.tsx`
- **Pré-remplissage ordre** : `frontend/src/components/orders/PlaceOrderModal.tsx`

Comportement :
- Clic bouton → ouverture de la modal IA → appel API.
- Affichage de 3 cartes (détails repliables) + bouton **« Passer un ordre (pré-rempli) »**.
- Si la suggestion est résolue vers `AllAssets` (champ `all_asset_id`), l’ordre est pré-rempli avec :
  - `initialAllAssetId`
  - `initialSymbol` (symbole broker `AllAssets.symbol` quand disponible)
  - `initialSide='BUY'`

## API (backend)

### Endpoint

- `POST /api/ai/analyses/suggest-diversification/`
- Auth: **JWT requis**
- Body :

```json
{ "force_new": true }
```

### Réponse

Retourne un objet `AIAnalysis` (type `MARKET`).
Les **3 suggestions** sont stockées dans `recommendations` (JSON).

Chaque suggestion peut inclure :
- `yahoo_symbol`, `symbol`, `name`
- `sector`, `industry`, `country`
- `fundamentals`: `{ per, valuation, profitability }`
- `moat`, `company_strategy`
- `macro_and_geopolitical`, `investment_horizon`
- `risks` (liste)
- `confidence` (0–100)
- **enrichissement serveur** :
  - `all_asset_id` (si résolu dans `AllAssets` via `symbole_yahoo`)
  - `tradable` (bool)
  - `broker_symbol` (symbole broker `AllAssets.symbol`)

## Implémentation

- Prompt : `backend/apps/ai_assistant/services/prompt_templates.py` (`DIVERSIFY_PROMPT`)
- Service : `backend/apps/ai_assistant/services/trading_analysis_service.py`
  - `TradingAnalysisService.suggest_diversification(user)`
  - Matching catalogue : `AllAssets.symbole_yahoo` (case-insensitive)
- Endpoint : `backend/apps/ai_assistant/api/views.py` (`AIAnalysisViewSet.suggest_diversification`)

## Notes

- Les chiffres fondamentaux **peuvent être partiels** selon les limites de données disponibles côté IA : `per` peut être `null`.
- La fonctionnalité est informative : l’utilisateur conserve la responsabilité finale avant passage d’ordre.

