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

## Problèmes résolus

### 1. Dropdown coupé par les lignes du tableau

**Problème** : Le dropdown était masqué par les lignes suivantes du tableau.

**Solution** : Ajout d'une classe `.asset-select-open` avec `z-index: 9998` quand le dropdown est ouvert.

### 2. Texte illisible sur fond blanc

**Problème** : Le thème sombre utilisait des couleurs claires invisibles sur fond blanc.

**Solution** : Couleurs fixes dans `AssetSelect.css` :
- Fond : `#ffffff`
- Symboles : `#111827` (noir)
- Noms : `#6b7280` (gris)

### 3. Dropdown ouvert vers le haut si pas d'espace

**Solution** : Détection automatique de l'espace disponible et classe `.asset-select-dropdown-upward`.

### 4. Recherche dans toute la base

**Solution** : `useApiAutocomplete={true}` pour utiliser l'API de recherche plutôt que la liste locale.

## Fichiers modifiés

| Fichier | Modification |
|---------|--------------|
| `frontend/src/pages/Strategies.tsx` | Colonnes avec `cellType: 'asset_select'`, mise à jour optimiste |
| `frontend/src/pages/Strategies.css` | `overflow-x: auto` pour scroll horizontal, `min-height: 400px` |
| `frontend/src/components/common/AssetSelect.tsx` | Classe `.asset-select-open`, détection upward |
| `frontend/src/components/common/AssetSelect.css` | Styles dropdown, couleurs fixes, `.asset-select-dropdown-upward` |
| `frontend/src/components/common/Table.tsx` | `useApiAutocomplete={true}` |
| `frontend/src/styles/index.css` | Ordre des @import corrigé |
