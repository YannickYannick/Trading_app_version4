# 🧩 Phase 4.3 : Composants de Base Créés

## Vue d'ensemble

Tous les composants de base réutilisables ont été créés et améliorés, permettant de construire l'interface utilisateur de manière cohérente et efficace.

## ✅ Checklist Complétée

- [x] `Button` créé avec variants, tailles et état loading
- [x] `Card` créé avec header, subtitle, actions et footer
- [x] `Input` créé avec label, error et helperText
- [x] `Table` créé avec colonnes configurables et keyExtractor
- [x] `Modal` créé avec overlay et fermeture (Escape, overlay)
- [x] `Badge` créé avec variants
- [x] `Loading` créé avec spinner et tailles
- [x] Styles CSS pour tous les composants
- [x] Types TypeScript pour tous les composants

---

## 📦 Composants Créés

### 1. Button

**Fichier** : `src/components/common/Button.tsx`

**Fonctionnalités** :
- Variants : `primary`, `secondary`, `success`, `danger`, `buy`, `sell`, `outline`
- Tailles : `sm`, `md`, `lg`
- État loading avec spinner
- Full width optionnel

**Exemple** :
```tsx
import { Button } from '@components/common'

<Button variant="primary" size="md">Cliquer</Button>
<Button variant="buy" isLoading loadingText="Achat en cours...">
  Acheter
</Button>
<Button variant="outline" fullWidth>Annuler</Button>
```

### 2. Card

**Fichier** : `src/components/common/Card.tsx`

**Fonctionnalités** :
- Header avec titre et sous-titre
- Actions dans le header
- Footer optionnel
- Hover effect (désactivable)

**Exemple** :
```tsx
import { Card, Button } from '@components/common'

<Card
  title="Positions"
  subtitle="Vos positions ouvertes"
  actions={<Button size="sm">Nouvelle</Button>}
  footer={<Button>Voir tout</Button>}
>
  Contenu de la carte
</Card>
```

### 3. Input

**Fichier** : `src/components/common/Input.tsx`

**Fonctionnalités** :
- Label optionnel
- Gestion d'erreurs
- Helper text
- Full width optionnel

**Exemple** :
```tsx
import { Input } from '@components/common'

<Input
  label="Email"
  type="email"
  placeholder="votre@email.com"
  error="Email invalide"
  helperText="Entrez votre adresse email"
  fullWidth
/>
```

### 4. Table

**Fichier** : `src/components/common/Table.tsx`

**Fonctionnalités** :
- Colonnes configurables avec render personnalisé
- Alignement par colonne
- Key extractor personnalisé
- Click sur les lignes
- Mode compact
- État vide

**Exemple** :
```tsx
import { Table, Badge } from '@components/common'

const columns = [
  { key: 'symbol', label: 'Symbole' },
  { key: 'price', label: 'Prix', align: 'right' },
  {
    key: 'pnl',
    label: 'P&L',
    align: 'right',
    render: (value, row) => (
      <Badge variant={value >= 0 ? 'success' : 'danger'}>
        {value.toFixed(2)}
      </Badge>
    ),
  },
]

<Table
  columns={columns}
  data={positions}
  keyExtractor={(row) => row.id}
  onRowClick={(row) => console.log(row)}
/>
```

### 5. Modal

**Fichier** : `src/components/common/Modal.tsx`

**Fonctionnalités** :
- Overlay avec backdrop
- Fermeture avec Escape
- Fermeture au clic sur overlay (configurable)
- Tailles : `sm`, `md`, `lg`, `xl`
- Bouton de fermeture (configurable)
- Bloque le scroll du body

**Exemple** :
```tsx
import { Modal, Button } from '@components/common'
import { useState } from 'react'

function MyComponent() {
  const [isOpen, setIsOpen] = useState(false)
  
  return (
    <>
      <Button onClick={() => setIsOpen(true)}>Ouvrir</Button>
      <Modal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Confirmation"
        size="md"
      >
        <p>Êtes-vous sûr ?</p>
        <Button onClick={() => setIsOpen(false)}>Confirmer</Button>
      </Modal>
    </>
  )
}
```

### 6. Badge

**Fichier** : `src/components/common/Badge.tsx`

**Fonctionnalités** :
- Variants : `success`, `danger`, `warning`, `info`, `primary`, `outline`

**Exemple** :
```tsx
import { Badge } from '@components/common'

<Badge variant="success">Actif</Badge>
<Badge variant="danger">Inactif</Badge>
<Badge variant="outline">En attente</Badge>
```

### 7. Loading

**Fichier** : `src/components/common/Loading.tsx`

**Fonctionnalités** :
- Tailles : `sm`, `md`, `lg`
- Texte optionnel
- Mode fullscreen

**Exemple** :
```tsx
import { Loading } from '@components/common'

<Loading size="md" text="Chargement..." />
<Loading size="lg" text="Chargement des données..." fullScreen />
```

---

## 🎨 Styles et Animations

### Animations

- **Modal** : Fade-in overlay + slide-up modal
- **Button spinner** : Rotation infinie
- **Loading spinner** : Rotation infinie

### Responsive

Tous les composants sont responsives :
- Modal s'adapte sur mobile
- Table avec scroll horizontal si nécessaire
- Input full width sur mobile

---

## 📝 Utilisation Complète

### Exemple : Page Dashboard

```tsx
import { Card, Table, Button, Badge, Loading } from '@components/common'
import { useState } from 'react'
import type { Position } from '@types'

export default function DashboardPage() {
  const [positions, setPositions] = useState<Position[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const columns = [
    {
      key: 'symbol',
      label: 'Symbole',
    },
    {
      key: 'size',
      label: 'Taille',
      align: 'right' as const,
      render: (value: number) => value.toFixed(2),
    },
    {
      key: 'pnl',
      label: 'P&L',
      align: 'right' as const,
      render: (value: number) => (
        <Badge variant={value >= 0 ? 'success' : 'danger'}>
          {value >= 0 ? '+' : ''}{value.toFixed(2)}
        </Badge>
      ),
    },
  ]

  if (isLoading) {
    return <Loading text="Chargement des positions..." />
  }

  return (
    <Card
      title="Positions"
      subtitle={`${positions.length} position(s) ouverte(s)`}
      actions={<Button variant="primary">Nouvelle position</Button>}
    >
      <Table
        columns={columns}
        data={positions}
        keyExtractor={(pos) => pos.id}
        onRowClick={(pos) => console.log('Position:', pos)}
      />
    </Card>
  )
}
```

---

## 🔗 Imports

Tous les composants sont exportés depuis `@components/common` :

```tsx
import {
  Button,
  Card,
  Table,
  Input,
  Modal,
  Badge,
  Loading,
} from '@components/common'
```

---

## 📁 Structure

```
src/components/common/
├── Button.tsx          ✅ Avec loading
├── Button.css
├── Card.tsx            ✅ Avec subtitle et actions
├── Card.css
├── Input.tsx           ✅ Avec helperText
├── Input.css
├── Table.tsx           ✅ Avec keyExtractor
├── Table.css
├── Modal.tsx           ✅ Nouveau
├── Modal.css
├── Badge.tsx           ✅ Existant
├── Badge.css
├── Loading.tsx         ✅ Nouveau
├── Loading.css
└── index.ts            ✅ Exports
```

---

## ✅ Prochaines Étapes

1. **Composants Trading** : Créer des composants spécifiques (AssetCard, PositionCard, etc.)
2. **Services API** : Créer les services pour appeler l'API
3. **Hooks personnalisés** : useAuth, useApi, etc.
4. **Pages principales** : Implémenter avec les composants

---

## 📚 Ressources

- **Composants** : `src/components/common/`
- **Styles** : `src/styles/components.css`
- **Types** : `src/types/index.ts`

