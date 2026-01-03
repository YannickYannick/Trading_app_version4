# Dropdown AssetSelect dans les tableaux

## Fonctionnalité

Ajout d'un sélecteur dropdown pour choisir un AllAsset dans les colonnes "Symbole AllAsset" et "Symbole Yahoo" de la page `/strategies`.

## Utilisation

1. Double-cliquez sur une cellule "Symbole AllAsset" ou "Symbole Yahoo"
2. Une liste déroulante apparaît - tapez pour rechercher dans **toute la base de données**
3. Cliquez sur un asset pour le sélectionner
4. La sélection est sauvegardée automatiquement sans recharger la page

## Fonctionnalités

- **Recherche API** : Recherche dans toute la base de données AllAssets (pas seulement les assets préchargés)
- **Mise à jour optimiste** : L'interface se met à jour immédiatement sans attendre le serveur
- **Auto-positionnement** : Le dropdown s'ouvre vers le haut si pas assez d'espace en bas
- **Scroll horizontal** : Le tableau reste scrollable horizontalement pour accéder à toutes les colonnes

## Visualisation des stratégies

### Tableau des trades simulés

Un tableau affiche tous les trades simulés sous le graphique avec :
- Date entrée / sortie
- Type (BUY/SELL avec couleurs)
- Prix entrée / sortie
- Quantité
- PnL (absolue et %)

### Contrôle du short selling

| `min_quantity` | Peut commencer par SELL ? |
|---------------|---------------------------|
| `>= 0` | ❌ Non - Premier trade doit être BUY |
| `< 0` | ✅ Oui - Short selling autorisé |

## Fichiers modifiés

| Fichier | Modification |
|---------|--------------|
| `frontend/src/pages/Strategies.tsx` | Colonnes avec `cellType: 'asset_select'`, mise à jour optimiste |
| `frontend/src/pages/Strategies.css` | `overflow-x: auto` pour scroll horizontal |
| `frontend/src/components/common/AssetSelect.tsx` | Classe `.asset-select-open`, détection upward |
| `frontend/src/components/common/AssetSelect.css` | Styles dropdown, couleurs fixes |
| `frontend/src/components/strategies/StrategyVisualizationChart.tsx` | Tableau des trades simulés, marqueurs simplifiés |
| `frontend/src/components/strategies/StrategyVisualizationChart.css` | Styles du tableau des trades |
| `frontend/src/utils/strategyPerformance.ts` | Contrôle short selling via min_quantity |
