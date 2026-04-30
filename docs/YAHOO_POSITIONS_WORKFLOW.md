# Workflow Yahoo — Positions (prix + secteur/industrie)

Sur la page **Positions**, le bouton **« Charger les prix Yahoo »** sert à :

1. **Enrichir** les métadonnées AllAssets depuis Yahoo (nom, secteur, industrie) pour les actifs présents dans les positions.
2. **Charger** les prix actuels Yahoo (affichage dans la colonne « Prix actuel »).
3. **Rafraîchir** la liste des positions afin de refléter les champs mis à jour (secteur/industrie).

## Frontend

- Page : `frontend/src/pages/Positions.tsx`
- Services : `frontend/src/services/assets.ts`

## Backend

### Enrichissement méta (nom/secteur/industrie)

- `POST /api/all-assets/enrich-yahoo-meta/`
- Auth: JWT
- Body :

```json
{
  "all_asset_ids": [123, 456, 789],
  "dry_run": false
}
```

Réponse :
- `success`, `checked`, `updated`
- `sample` (quelques lignes enrichies)

### Prix Yahoo (par AllAsset)

Le frontend utilise en priorité :
- `GET /api/all-assets/{id}/current_price/`

Puis fallback éventuel :
- `GET /api/all-assets/{id}/prices/?days=1&format=list`

## Remarques

- Si l’API Yahoo renvoie 400/404 sur `current_price`, cela peut signifier que le symbole Yahoo n’est pas validé ou non trouvé.
- Le frontend affiche maintenant un message d’erreur si aucun prix n’a pu être récupéré.

