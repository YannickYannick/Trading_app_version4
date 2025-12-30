# Interface Frontend React - Système de Stratégies

## Vue d'ensemble

Ce document décrit l'implémentation de l'interface React pour le système de stratégies, utilisant React Table (TanStack Table) au lieu de Tabulator.

## Technologies

- **React 18+** avec TypeScript
- **React Table (TanStack Table)** pour les tableaux
- **React Hook Form** pour les formulaires
- **Axios** pour les appels API

## Structure des Composants

```
frontend/src/
├── pages/
│   └── Strategies.tsx              # Page principale
├── components/
│   └── strategies/
│       ├── StrategyModal.tsx       # Modal création/édition
│       ├── AlgorithmParameters.tsx # Paramètres d'algorithme
│       ├── ExecutionHistory.tsx    # Historique d'exécution
│       ├── StrategyStatusBadge.tsx # Badge de statut
│       └── StrategyActions.tsx     # Actions (exécuter, etc.)
├── services/
│   └── strategies.ts               # Service API
└── types/
    └── index.ts                    # Types TypeScript
```

## Page Principale : Strategies.tsx

### Structure

```typescript
import React, { useState, useEffect } from 'react'
import { useTable } from '@tanstack/react-table'
import { strategyService } from '@services/strategies'
import StrategyModal from '@components/strategies/StrategyModal'
import StrategyActions from '@components/strategies/StrategyActions'

export default function Strategies() {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null)
  
  // Charger les stratégies
  useEffect(() => {
    loadStrategies()
  }, [])
  
  const loadStrategies = async () => {
    try {
      setLoading(true)
      const response = await strategyService.list()
      setStrategies(response.results || [])
    } catch (error) {
      console.error('Erreur chargement stratégies:', error)
    } finally {
      setLoading(false)
    }
  }
  
  // Définir les colonnes React Table
  const columns = [
    {
      accessorKey: 'name',
      header: 'Nom',
    },
    {
      accessorKey: 'asset_name',
      header: 'Asset',
    },
    {
      accessorKey: 'algorithm_type_display',
      header: 'Algorithme',
    },
    {
      accessorKey: 'status_display',
      header: 'Statut',
      cell: ({ row }) => (
        <StrategyStatusBadge status={row.original.status} />
      ),
    },
    {
      accessorKey: 'last_execution',
      header: 'Dernière exécution',
      cell: ({ row }) => 
        row.original.last_execution 
          ? new Date(row.original.last_execution).toLocaleString()
          : 'Jamais'
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => (
        <StrategyActions
          strategy={row.original}
          onExecute={handleExecute}
          onEdit={handleEdit}
          onDelete={handleDelete}
        />
      ),
    },
  ]
  
  const table = useTable({
    data: strategies,
    columns,
  })
  
  return (
    <div className="strategies-page">
      <div className="strategies-header">
        <h1>Stratégies de Trading</h1>
        <button onClick={() => setIsModalOpen(true)}>
          Créer une stratégie
        </button>
      </div>
      
      {/* Table React Table */}
      <Table table={table} />
      
      {/* Modal */}
      <StrategyModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setSelectedStrategy(null)
        }}
        strategy={selectedStrategy}
        onSuccess={loadStrategies}
      />
    </div>
  )
}
```

## Service API : strategies.ts

```typescript
import apiClient from '@utils/apiClient'

export interface Strategy {
  id: number
  name: string
  description: string
  asset: number
  all_asset: number | null
  broker_account: number
  algorithm_type: string
  parameters: Record<string, any>
  execution_mode: 'simulation' | 'paper_trading' | 'live_trading'
  status: 'active' | 'inactive' | 'paused'
  check_frequency: number
  target_min_quantity: number
  target_max_quantity: number
  portfolio_quantity: number
  // ...
}

export const strategyService = {
  async list(): Promise<{ results: Strategy[] }> {
    const response = await apiClient.get('/strategies/')
    return response.data
  },
  
  async get(id: number): Promise<Strategy> {
    const response = await apiClient.get(`/strategies/${id}/`)
    return response.data
  },
  
  async create(data: Partial<Strategy>): Promise<Strategy> {
    const response = await apiClient.post('/strategies/', data)
    return response.data
  },
  
  async update(id: number, data: Partial<Strategy>): Promise<Strategy> {
    const response = await apiClient.patch(`/strategies/${id}/`, data)
    return response.data
  },
  
  async delete(id: number): Promise<void> {
    await apiClient.delete(`/strategies/${id}/`)
  },
  
  async execute(id: number): Promise<any> {
    const response = await apiClient.post(`/strategies/${id}/execute/`)
    return response.data
  },
  
  async calculateSignal(id: number): Promise<any> {
    const response = await apiClient.post(`/strategies/${id}/calculate-signal/`)
    return response.data
  },
  
  async getExecutions(id: number): Promise<any[]> {
    const response = await apiClient.get(`/strategies/${id}/executions/`)
    return response.data.results || []
  },
  
  async getAlgorithms(): Promise<any> {
    const response = await apiClient.get('/strategies/algorithms/')
    return response.data
  },
}
```

## Composant StrategyModal

Modal pour créer/éditer une stratégie avec :
- Formulaire React Hook Form
- Sélection d'asset (avec autocomplétion)
- Sélection d'algorithme avec paramètres dynamiques
- Configuration des quantités cibles

```typescript
import { useForm } from 'react-hook-form'
import { assetService } from '@services/assets'
import AlgorithmParameters from './AlgorithmParameters'

interface StrategyModalProps {
  isOpen: boolean
  onClose: () => void
  strategy?: Strategy | null
  onSuccess: () => void
}

export default function StrategyModal({
  isOpen,
  onClose,
  strategy,
  onSuccess
}: StrategyModalProps) {
  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm({
    defaultValues: strategy || {}
  })
  
  const selectedAlgorithm = watch('algorithm_type')
  const [algorithms, setAlgorithms] = useState<any>({})
  
  useEffect(() => {
    strategyService.getAlgorithms().then(data => {
      setAlgorithms(data)
    })
  }, [])
  
  const onSubmit = async (data: any) => {
    try {
      if (strategy) {
        await strategyService.update(strategy.id, data)
      } else {
        await strategyService.create(data)
      }
      onSuccess()
      onClose()
    } catch (error) {
      console.error('Erreur sauvegarde:', error)
    }
  }
  
  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <form onSubmit={handleSubmit(onSubmit)}>
        <input {...register('name', { required: true })} placeholder="Nom" />
        <select {...register('algorithm_type', { required: true })}>
          <option value="">Sélectionner un algorithme</option>
          {Object.entries(algorithms.algorithms || {}).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>
        
        {selectedAlgorithm && (
          <AlgorithmParameters
            algorithmType={selectedAlgorithm}
            parameters={algorithms.parameters?.[selectedAlgorithm] || []}
            value={watch('parameters')}
            onChange={(params) => setValue('parameters', params)}
          />
        )}
        
        <button type="submit">Enregistrer</button>
      </form>
    </Modal>
  )
}
```

## Composant AlgorithmParameters

Génère dynamiquement les champs de paramètres selon l'algorithme sélectionné.

```typescript
interface AlgorithmParametersProps {
  algorithmType: string
  parameters: Array<{
    name: string
    label: string
    type: string
    default: any
  }>
  value: Record<string, any>
  onChange: (params: Record<string, any>) => void
}

export default function AlgorithmParameters({
  algorithmType,
  parameters,
  value,
  onChange
}: AlgorithmParametersProps) {
  const handleChange = (name: string, val: any) => {
    onChange({ ...value, [name]: val })
  }
  
  return (
    <div className="algorithm-parameters">
      <h3>Paramètres de l'algorithme</h3>
      {parameters.map(param => (
        <div key={param.name}>
          <label>{param.label}</label>
          <input
            type={param.type}
            value={value[param.name] ?? param.default}
            onChange={(e) => handleChange(
              param.name,
              param.type === 'number' ? parseFloat(e.target.value) : e.target.value
            )}
          />
        </div>
      ))}
    </div>
  )
}
```

## Intégration dans l'Application

### Route

```typescript
// App.tsx
<Route path="/strategies" element={<Strategies />} />
```

### Menu

```typescript
// Sidebar.tsx
{ path: '/strategies', label: 'Stratégies', icon: '📈' }
```

---

**Voir aussi** :
- [STRATEGIES_API.md](STRATEGIES_API.md) : API utilisée par le frontend
- [STRATEGIES_EXAMPLES.md](STRATEGIES_EXAMPLES.md) : Exemples d'utilisation

