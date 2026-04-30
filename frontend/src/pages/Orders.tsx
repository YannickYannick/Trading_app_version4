/**
 * Page Orders - Liste et gestion des ordres avec édition inline
 */
import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  Search, Filter, RefreshCw, Plus, Eye, Copy, XCircle, Trash2,
  Save, X, Clock, TrendingUp, CheckCircle, Sparkles
} from 'lucide-react'
import { Card, Button, Table, Badge, Loading, ColumnSelector, type ColumnOption, YahooActions } from '@components/common'
import PlaceOrderModal from '@components/orders/PlaceOrderModal'
import { AIDiversifyModal, type OrderPrefillPayload } from '@components/orders'
import { orderService, brokerService, positionService } from '@services/index'
import { assetService } from '@services/assets'
import { formatCurrency, formatDate } from '@utils/format'
import type { Order, BrokerAccount, Position } from '@types'
import './Orders.css'

export default function Orders() {
  // États principaux
  const [orders, setOrders] = useState<Order[]>([])
  const [originalOrders, setOriginalOrders] = useState<Order[]>([])
  const [modifiedOrders, setModifiedOrders] = useState<Map<number, Partial<Order>>>(new Map())
  const [newOrders, setNewOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isPlaceOrderModalOpen, setIsPlaceOrderModalOpen] = useState(false)
  const [isDiversifyModalOpen, setIsDiversifyModalOpen] = useState(false)
  const [orderPrefill, setOrderPrefill] = useState<OrderPrefillPayload | null>(null)

  // États pour les positions
  const [positions, setPositions] = useState<Position[]>([])
  const [positionsLoading, setPositionsLoading] = useState(false)
  const [sellQuantities, setSellQuantities] = useState<Map<number, number>>(new Map())
  const [sellingPosition, setSellingPosition] = useState<number | null>(null)

  // Filtres et tri
  const [filters, setFilters] = useState({
    broker: '',
    status: '',
    side: '',
    search: ''
  })
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>(null)

  // Brokers pour filtre
  const [brokers, setBrokers] = useState<BrokerAccount[]>([])

  // État d'édition inline
  const [editingCell, setEditingCell] = useState<{ orderId: number; field: string } | null>(null)

  // Colonnes éditables
  const editableFields = ['quantity', 'price', 'stop_price']

  // Colonnes visibles
  const [visibleColumns, setVisibleColumns] = useState<string[]>([])
  const [yahooPrices, setYahooPrices] = useState<Record<number, number | null>>({})

  // Métadonnées des colonnes pour ColumnSelector
  const allColumnsData: ColumnOption[] = [
    { key: 'modified', label: 'Modifié', defaultVisible: true },
    { key: 'broker_name', label: 'Broker', defaultVisible: true },
    { key: 'all_asset_symbol', label: 'Symbole AllAsset', defaultVisible: true },
    { key: 'yahoo_symbol', label: 'Symbole Yahoo', defaultVisible: true },
    { key: 'yahoo_price', label: 'Prix Yahoo', defaultVisible: true },
    { key: 'symbol', label: 'Asset', defaultVisible: true },
    { key: 'order_type', label: 'Type', defaultVisible: true },
    { key: 'side', label: 'Côté', defaultVisible: true },
    { key: 'quantity', label: 'Quantité', defaultVisible: true },
    { key: 'price', label: 'Prix', defaultVisible: true },
    { key: 'stop_price', label: 'Stop Prix', defaultVisible: true },
    { key: 'total_value', label: 'Valeur Totale', defaultVisible: true },
    { key: 'status', label: 'Statut', defaultVisible: true },
    { key: 'created_at', label: 'Créé le', defaultVisible: true },
    { key: 'yahoo_actions', label: 'Actions Yahoo', defaultVisible: true },
    { key: 'actions', label: 'Actions', defaultVisible: true },
  ]

  // Charger les positions depuis l'API (même source que /positions)
  const loadPositions = async () => {
    try {
      setPositionsLoading(true)
      // Charger uniquement les positions ouvertes
      const openPositions = await positionService.getOpen()
      setPositions(openPositions)

      // Initialiser les quantités de vente avec la quantité totale
      const initialQuantities = new Map<number, number>()
      openPositions.forEach(p => {
        initialQuantities.set(p.id, Number(p.size) || 0)
      })
      setSellQuantities(initialQuantities)
    } catch (err) {
      console.error('Erreur chargement positions:', err)
    } finally {
      setPositionsLoading(false)
    }
  }

  // Vendre une position au marché
  const handleSellPosition = async (position: Position) => {
    const positionSize = Number(position.size) || 0
    const quantity = sellQuantities.get(position.id) || positionSize
    const symbol = position.asset?.symbol

    if (!symbol) {
      alert('Symbole non trouvé pour cette position')
      return
    }

    if (quantity <= 0) {
      alert('La quantité doit être supérieure à 0')
      return
    }

    if (quantity > positionSize) {
      alert(`La quantité ne peut pas dépasser ${positionSize}`)
      return
    }

    if (!confirm(`Vendre ${quantity} ${symbol} au marché ?`)) {
      return
    }

    try {
      setSellingPosition(position.id)

      // Trouver le broker account associé à cette position
      // On utilise le premier broker disponible si pas d'info spécifique
      const brokerAccount = brokers[0]

      if (!brokerAccount) {
        throw new Error('Aucun compte broker disponible')
      }

      // Créer un ordre de vente au marché via le broker
      const result = await orderService.placeOrder({
        broker_account_id: brokerAccount.id,
        symbol: symbol,
        order_type: 'MARKET',
        side: 'SELL',
        quantity: String(quantity),
      })

      if (result.success) {
        alert(`✅ ${result.message || `Ordre de vente créé pour ${quantity} ${symbol}`}`)
      } else {
        throw new Error(result.message || 'Erreur lors de la vente')
      }

      // Recharger les ordres et positions
      await loadOrders()
      await loadPositions()
    } catch (err: any) {
      console.error('Erreur vente:', err)
      alert(`❌ Erreur: ${err.response?.data?.error || err.message || 'Erreur lors de la vente'}`)
    } finally {
      setSellingPosition(null)
    }
  }

  // Charger les ordres
  const loadOrders = async () => {
    try {
      setLoading(true)
      setError(null)
      const apiFilters: any = {}
      if (filters.status) {
        apiFilters.status = filters.status
      }
      const response = await orderService.getAll(apiFilters)
      const ordersList = response.results || []

      // Calculer total_value pour chaque ordre
      const ordersWithTotal = ordersList.map(order => ({
        ...order,
        total_value: (order.quantity || 0) * (order.price || 0)
      }))

      setOrders(ordersWithTotal)
      setOriginalOrders(ordersWithTotal)
      setModifiedOrders(new Map())
      setNewOrders([])
    } catch (err: any) {
      setError(err.error || 'Erreur lors du chargement des ordres')
      console.error('Erreur:', err)
    } finally {
      setLoading(false)
    }
  }

  // Charger les brokers
  const loadBrokers = async () => {
    try {
      const response = await brokerService.getAccounts()
      setBrokers(response.results || [])
    } catch (err: any) {
      console.error('Erreur lors du chargement des brokers:', err)
    }
  }

  useEffect(() => {
    loadOrders()
    loadBrokers()
    loadPositions() // Charger les positions au démarrage
  }, [])

  // Initialiser les colonnes visibles depuis localStorage
  useEffect(() => {
    if (visibleColumns.length === 0) {
      try {
        const saved = localStorage.getItem('orders_visible_columns')
        if (saved) {
          const parsed = JSON.parse(saved)
          if (Array.isArray(parsed) && parsed.length > 0) {
            setVisibleColumns(parsed)
          } else {
            setVisibleColumns(allColumnsData.filter(c => c.defaultVisible !== false).map(c => c.key))
          }
        } else {
          setVisibleColumns(allColumnsData.filter(c => c.defaultVisible !== false).map(c => c.key))
        }
      } catch (e) {
        setVisibleColumns(allColumnsData.filter(c => c.defaultVisible !== false).map(c => c.key))
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Charger les prix Yahoo actuels pour tous les AllAssets
  useEffect(() => {
    if (orders.length > 0) {
      const loadYahooPrices = async () => {
        const priceMap: Record<number, number | null> = {}
        const allAssetIds = orders
          .map(o => o.all_asset?.id || (typeof o.all_asset === 'number' ? o.all_asset : null))
          .filter((id): id is number => id !== null && id !== undefined)

        // Charger les prix en parallèle (limité à 10 à la fois)
        const batches = []
        for (let i = 0; i < allAssetIds.length; i += 10) {
          batches.push(allAssetIds.slice(i, i + 10))
        }

        for (const batch of batches) {
          const results = await Promise.allSettled(
            batch.map(async (id) => {
              const price = await assetService.getYahooCurrentPrice(id)
              return { id, price }
            })
          )

          results.forEach((result) => {
            if (result.status === 'fulfilled') {
              priceMap[result.value.id] = result.value.price
            }
          })
        }

        setYahooPrices(priceMap)
      }

      loadYahooPrices()
    }
  }, [orders])

  // Vérifier si un ordre a été modifié
  const isOrderModified = useCallback((orderId: number): boolean => {
    return modifiedOrders.has(orderId)
  }, [modifiedOrders])

  // Marquer un ordre comme modifié
  const markAsModified = useCallback((orderId: number, field: string, value: any) => {
    setModifiedOrders(prev => {
      const newMap = new Map(prev)
      const existing = newMap.get(orderId) || {}
      newMap.set(orderId, { ...existing, [field]: value })
      return newMap
    })
  }, [])

  // Fonction pour démarrer l'édition
  const startEdit = (orderId: number, field: string) => {
    if (editableFields.includes(field)) {
      setEditingCell({ orderId, field })
    }
  }

  // Sauvegarder une modification locale
  const saveEditLocally = (orderId: number, field: string, value: string) => {
    const numValue = parseFloat(value)
    if (!isNaN(numValue) && numValue >= 0) {
      setOrders(prev => prev.map(order => {
        if (order.id === orderId) {
          const updated = { ...order, [field]: numValue }

          // Recalculer total_value si quantity ou price change
          if (field === 'quantity' || field === 'price') {
            updated.total_value = (updated.quantity || 0) * (updated.price || 0)
          }

          // Marquer comme modifié
          markAsModified(orderId, field, numValue)

          return updated
        }
        return order
      }))
    }
    setEditingCell(null)
  }

  // Annuler l'édition
  const cancelEdit = () => {
    setEditingCell(null)
  }

  // Sauvegarder toutes les modifications
  const saveAllChanges = async () => {
    setIsSaving(true)
    setError(null)

    try {
      const promises: Promise<any>[] = []

      // Sauvegarder les ordres modifiés
      for (const [orderId, changes] of modifiedOrders.entries()) {
        promises.push(orderService.update(orderId, changes))
      }

      // Créer les nouveaux ordres
      for (const newOrder of newOrders) {
        promises.push(orderService.create({
          asset: newOrder.asset.id || newOrder.asset as any,
          order_type: newOrder.order_type,
          side: newOrder.side,
          quantity: newOrder.quantity,
          price: newOrder.price || undefined,
          stop_price: newOrder.stop_price || undefined,
          broker_id: newOrder.broker_id
        }))
      }

      await Promise.all(promises)

      // Réinitialiser les états
      setModifiedOrders(new Map())
      setNewOrders([])

      // Recharger les ordres
      await loadOrders()

    } catch (err: any) {
      setError(err.response?.data?.error || 'Erreur lors de la sauvegarde')
      console.error('Erreur lors de la sauvegarde:', err)
    } finally {
      setIsSaving(false)
    }
  }

  // Annuler toutes les modifications
  const cancelAllChanges = () => {
    if (window.confirm('Annuler toutes les modifications non sauvegardées ?')) {
      setOrders([...originalOrders])
      setModifiedOrders(new Map())
      setNewOrders([])
      setEditingCell(null)
    }
  }

  // Tri
  const handleSort = (key: string) => {
    setSortConfig(prev => {
      if (prev?.key === key) {
        return prev.direction === 'asc' ? { key, direction: 'desc' } : null
      }
      return { key, direction: 'asc' }
    })
  }

  // Filtrage
  const filteredOrders = orders.filter(order => {
    const matchBroker = !filters.broker ||
      (order.broker_name?.toLowerCase().includes(filters.broker.toLowerCase()) ||
        order.broker?.name?.toLowerCase().includes(filters.broker.toLowerCase()))
    const matchStatus = !filters.status || order.status === filters.status
    const matchSide = !filters.side || order.side === filters.side
    const matchSearch = !filters.search ||
      order.asset?.symbol?.toLowerCase().includes(filters.search.toLowerCase()) ||
      order.asset?.name?.toLowerCase().includes(filters.search.toLowerCase())

    return matchBroker && matchStatus && matchSide && matchSearch
  })

  // Tri des ordres
  const sortedOrders = [...filteredOrders].sort((a, b) => {
    if (!sortConfig) return 0

    let aValue: any = a[sortConfig.key as keyof Order]
    let bValue: any = b[sortConfig.key as keyof Order]

    // Gérer les valeurs imbriquées
    if (sortConfig.key === 'broker_name') {
      aValue = a.broker_name || a.broker?.name || ''
      bValue = b.broker_name || b.broker?.name || ''
    } else if (sortConfig.key === 'symbol') {
      aValue = a.asset?.symbol || ''
      bValue = b.asset?.symbol || ''
    }

    if (aValue === bValue) return 0
    const comparison = aValue < bValue ? -1 : 1
    return sortConfig.direction === 'asc' ? comparison : -comparison
  })

  // Actions sur les ordres
  const handleDuplicate = async (order: Order) => {
    // Générer un ID temporaire unique (négatif pour distinguer des vrais IDs)
    const tempId = -Date.now()
    const newOrder: Order = {
      ...order,
      id: tempId,
      status: 'PENDING' as const,
      broker_order_id: undefined,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
    setNewOrders(prev => [...prev, newOrder])
    setOrders(prev => [newOrder, ...prev])
  }

  // Vérifier si un ordre est un nouvel ordre non sauvegardé
  const isNewOrder = (orderId: number) => {
    return newOrders.some(o => o.id === orderId)
  }

  const handleCancel = async (orderId: number) => {
    if (!confirm('Êtes-vous sûr de vouloir annuler cet ordre ?')) {
      return
    }

    // Si c'est un nouvel ordre non sauvegardé, le supprimer localement
    if (isNewOrder(orderId)) {
      setOrders(prev => prev.filter(o => o.id !== orderId))
      setNewOrders(prev => prev.filter(o => o.id !== orderId))
      setModifiedOrders(prev => {
        const newMap = new Map(prev)
        newMap.delete(orderId)
        return newMap
      })
      return
    }

    try {
      await orderService.cancel(orderId)
      await loadOrders()
    } catch (err: any) {
      alert(err.response?.data?.error || err.error || 'Erreur lors de l\'annulation')
      console.error('Erreur:', err)
    }
  }

  const handleDelete = async (orderId: number) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cet ordre ?')) {
      return
    }

    // Si c'est un nouvel ordre non sauvegardé, le supprimer localement seulement
    if (isNewOrder(orderId)) {
      setOrders(prev => prev.filter(o => o.id !== orderId))
      setNewOrders(prev => prev.filter(o => o.id !== orderId))
      setModifiedOrders(prev => {
        const newMap = new Map(prev)
        newMap.delete(orderId)
        return newMap
      })
      return
    }

    try {
      await orderService.delete(orderId)
      setOrders(prev => prev.filter(o => o.id !== orderId))
      setOriginalOrders(prev => prev.filter(o => o.id !== orderId))
      setModifiedOrders(prev => {
        const newMap = new Map(prev)
        newMap.delete(orderId)
        return newMap
      })
    } catch (err: any) {
      alert(err.response?.data?.error || err.error || 'Erreur lors de la suppression')
      console.error('Erreur:', err)
    }
  }

  // Synchroniser les ordres
  const handleSyncOrders = async () => {
    try {
      setLoading(true)
      // Récupérer le premier broker account disponible
      const brokerAccount = brokers[0]
      if (!brokerAccount) {
        alert('Aucun compte broker disponible')
        return
      }

      await orderService.syncOrders({
        broker_account_id: brokerAccount.id
      })

      await loadOrders()
    } catch (err: any) {
      alert(err.error || 'Erreur lors de la synchronisation')
      console.error('Erreur:', err)
    } finally {
      setLoading(false)
    }
  }

  // Badges de statut
  const getStatusBadge = (status: Order['status']) => {
    const config: Record<string, { variant: string; icon: any; label: string }> = {
      PENDING: { variant: 'warning', icon: Clock, label: 'En attente' },
      OPEN: { variant: 'info', icon: TrendingUp, label: 'Ouvert' },
      FILLED: { variant: 'success', icon: CheckCircle, label: 'Exécuté' },
      PARTIALLY_FILLED: { variant: 'warning', icon: Clock, label: 'Partiel' },
      CANCELLED: { variant: 'default', icon: XCircle, label: 'Annulé' },
      REJECTED: { variant: 'error', icon: XCircle, label: 'Rejeté' },
      EXPIRED: { variant: 'default', icon: XCircle, label: 'Expiré' }
    }

    const statusConfig = config[status] || { variant: 'default', icon: Clock, label: status }
    const Icon = statusConfig.icon

    return (
      <Badge variant={statusConfig.variant as any}>
        <Icon style={{ width: '12px', height: '12px', marginRight: '4px', display: 'inline', verticalAlign: 'middle' }} />
        {statusConfig.label}
      </Badge>
    )
  }

  // Vérifier s'il y a des modifications non sauvegardées
  const hasUnsavedChanges = modifiedOrders.size > 0 || newOrders.length > 0

  // Colonnes du tableau
  const columns = [
    {
      key: 'modified',
      label: '',
      width: '30px',
      minWidth: '30px',
      maxWidth: '30px',
      align: 'center' as const,
      render: (_value: any, row: Order) => (
        isOrderModified(row.id) ? (
          <div className="order-modified-indicator" title="Modifié"></div>
        ) : null
      ),
    },
    {
      key: 'broker_name',
      label: 'Broker',
      minWidth: '120px',
      width: '140px',
      align: 'center' as const,
      render: (_value: any, row: Order) => (
        <div style={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
          <div className="font-medium" style={{ whiteSpace: 'nowrap' }}>{row.broker_name || row.broker?.name || '-'}</div>
          {row.broker_order_id && (
            <div className="text-xs text-gray-500" style={{ whiteSpace: 'nowrap', fontSize: '0.75rem' }}>ID: {row.broker_order_id}</div>
          )}
        </div>
      ),
    },
    {
      key: 'all_asset_symbol',
      label: 'Symbole AllAsset',
      minWidth: '120px',
      width: '140px',
      align: 'center' as const,
      render: (_value: any, row: Order) => (
        <span className="all-asset-symbol">
          {row?.all_asset_symbol || row?.all_asset?.symbol || 'N/A'}
        </span>
      ),
    },
    {
      key: 'yahoo_symbol',
      label: 'Symbole Yahoo',
      minWidth: '120px',
      width: '140px',
      align: 'center' as const,
      render: (_value: any, row: Order) => (
        <span className="yahoo-symbol">
          {row?.all_asset_yahoo_symbol || row?.all_asset?.symbole_yahoo || 'N/A'}
        </span>
      ),
    },
    {
      key: 'yahoo_price',
      label: 'Prix Yahoo',
      minWidth: '100px',
      width: '120px',
      align: 'center' as const,
      render: (_value: any, row: Order) => {
        const allAssetId = row?.all_asset?.id || (typeof row?.all_asset === 'number' ? row.all_asset : null)
        const price = allAssetId ? yahooPrices[allAssetId] : null
        return price !== null && price !== undefined ? formatCurrency(price) : 'N/A'
      },
    },
    {
      key: 'symbol',
      label: 'Asset',
      minWidth: '140px',
      width: '160px',
      align: 'center' as const,
      render: (_value: any, row: Order) => (
        <div style={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
          <Link to={`/assets/${row?.asset?.id || ''}`} className="link-symbol font-medium" style={{ whiteSpace: 'nowrap', display: 'block' }}>
            {row?.asset?.symbol || 'N/A'}
          </Link>
          {row?.asset?.name && (
            <div className="text-xs text-gray-500" style={{ fontSize: '0.75rem', lineHeight: '1.2' }}>{row.asset.name}</div>
          )}
        </div>
      ),
    },
    {
      key: 'order_type',
      label: 'Type',
      minWidth: '80px',
      width: '100px',
      align: 'center' as const,
      render: (value: string) => {
        const labels: Record<string, string> = {
          MARKET: 'Market',
          LIMIT: 'Limit',
          STOP: 'Stop',
          STOP_LIMIT: 'Stop Limit'
        }
        return labels[value] || value
      },
    },
    {
      key: 'side',
      label: 'Côté',
      minWidth: '70px',
      width: '80px',
      align: 'center' as const,
      render: (value: string) => (
        <Badge variant={value === 'BUY' ? 'success' : 'danger'}>
          {value}
        </Badge>
      ),
    },
    {
      key: 'quantity',
      label: 'Quantité',
      minWidth: '100px',
      width: '120px',
      align: 'center' as const,
      editable: true,
      cellType: 'number' as const,
      onCellEdit: async (value: any, row: Order) => {
        const numValue = parseFloat(value)
        if (!isNaN(numValue) && numValue >= 0) {
          saveEditLocally(row.id, 'quantity', value)
        }
      },
      render: (value: any) => {
        const numValue = typeof value === 'string' ? parseFloat(value) : (value || 0)
        return isNaN(numValue) ? '0.0000' : numValue.toFixed(4)
      },
    },
    {
      key: 'price',
      label: 'Prix',
      minWidth: '100px',
      width: '120px',
      align: 'center' as const,
      editable: true,
      cellType: 'number' as const,
      onCellEdit: async (value: any, row: Order) => {
        const numValue = parseFloat(value)
        if (!isNaN(numValue) && numValue >= 0) {
          saveEditLocally(row.id, 'price', value)
        }
      },
      render: (value: any) => {
        if (!value) return 'Market'
        const numValue = typeof value === 'string' ? parseFloat(value) : value
        return isNaN(numValue) ? 'Market' : formatCurrency(numValue)
      },
    },
    {
      key: 'stop_price',
      label: 'Stop Prix',
      minWidth: '100px',
      width: '120px',
      align: 'center' as const,
      editable: true,
      cellType: 'number' as const,
      onCellEdit: async (value: any, row: Order) => {
        const numValue = parseFloat(value)
        if (!isNaN(numValue) && numValue >= 0) {
          saveEditLocally(row.id, 'stop_price', value)
        }
      },
      render: (value: any) => {
        if (!value) return '-'
        const numValue = typeof value === 'string' ? parseFloat(value) : value
        return isNaN(numValue) ? '-' : formatCurrency(numValue)
      },
    },
    {
      key: 'total_value',
      label: 'Valeur Totale',
      minWidth: '120px',
      width: '140px',
      align: 'center' as const,
      render: (value: any, row: Order) => {
        const total = row.total_value || (row.quantity || 0) * (row.price || 0)
        return total > 0 ? formatCurrency(total) : '-'
      },
    },
    {
      key: 'status',
      label: 'Statut',
      minWidth: '120px',
      width: '140px',
      align: 'center' as const,
      render: (value: string, row: Order) => (
        <div style={{ whiteSpace: 'normal' }}>
          {getStatusBadge(value as Order['status'])}
          {row.filled_quantity && row.filled_quantity > 0 && (
            <div className="text-xs text-gray-500 mt-1" style={{ fontSize: '0.75rem', lineHeight: '1.2', marginTop: '0.25rem' }}>
              Exécuté: {typeof row.filled_quantity === 'string'
                ? parseFloat(row.filled_quantity).toFixed(4)
                : row.filled_quantity.toFixed(4)} / {typeof row.quantity === 'string'
                  ? parseFloat(row.quantity).toFixed(4)
                  : row.quantity.toFixed(4)}
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'created_at',
      label: 'Créé le',
      minWidth: '110px',
      width: '130px',
      align: 'center' as const,
      render: (value: string) => formatDate(value),
    },
    {
      key: 'yahoo_actions',
      label: 'Actions Yahoo',
      minWidth: '120px',
      width: '140px',
      align: 'center' as const,
      render: (_value: any, row: Order) => {
        const allAssetId = row?.all_asset?.id || (typeof row?.all_asset === 'number' ? row.all_asset : null)
        return (
          <YahooActions
            allAssetId={allAssetId}
            allAssetSymbol={row?.all_asset_symbol || row?.all_asset?.symbol}
            onSuccess={async () => {
              // Mise à jour asynchrone sans recharger la page
              if (allAssetId) {
                try {
                  const price = await assetService.getYahooCurrentPrice(allAssetId)
                  setYahooPrices(prev => ({ ...prev, [allAssetId]: price }))
                } catch (error) {
                  console.error('Erreur lors de la mise à jour:', error)
                }
              }
            }}
            compact
          />
        )
      },
    },
    {
      key: 'actions',
      label: 'Actions',
      minWidth: '140px',
      width: '160px',
      align: 'center' as const,
      render: (_value: any, row: Order) => (
        <div className="orders-actions-inline">
          <button
            onClick={() => console.log('Voir', row.id)}
            className="action-btn action-view"
            title="Voir"
          >
            <Eye style={{ width: '16px', height: '16px' }} />
          </button>
          <button
            onClick={() => handleDuplicate(row)}
            className="action-btn action-duplicate"
            title="Dupliquer"
          >
            <Copy style={{ width: '16px', height: '16px' }} />
          </button>
          {['PENDING', 'OPEN', 'PARTIALLY_FILLED'].includes(row.status) && (
            <button
              onClick={() => handleCancel(row.id)}
              className="action-btn action-cancel"
              title="Annuler"
            >
              <XCircle style={{ width: '16px', height: '16px' }} />
            </button>
          )}
          <button
            onClick={() => handleDelete(row.id)}
            className="action-btn action-delete"
            title="Supprimer"
          >
            <Trash2 style={{ width: '16px', height: '16px' }} />
          </button>
        </div>
      ),
    },
  ]

  if (loading && orders.length === 0) {
    return (
      <div className="page-container">
        <Loading />
      </div>
    )
  }

  const pendingOrders = orders.filter((o) => ['PENDING', 'OPEN', 'PARTIALLY_FILLED'].includes(o.status))
  const filledOrders = orders.filter((o) => o.status === 'FILLED')

  return (
    <div className="page-container orders-page">
      <div className="orders-header">
        <h1 className="page-title">Gestion des Ordres</h1>
        <div className="orders-header-actions">
          <ColumnSelector
            columns={allColumnsData}
            visibleColumns={visibleColumns}
            onColumnsChange={setVisibleColumns}
            storageKey="orders_visible_columns"
          />
          {hasUnsavedChanges && (
            <>
              <button
                onClick={saveAllChanges}
                disabled={isSaving}
                className="btn btn-save"
              >
                <Save style={{ width: '16px', height: '16px', marginRight: '8px' }} />
                {isSaving ? 'Enregistrement...' : `Enregistrer (${modifiedOrders.size + newOrders.length})`}
              </button>
              <button
                onClick={cancelAllChanges}
                disabled={isSaving}
                className="btn btn-cancel"
              >
                <X style={{ width: '16px', height: '16px', marginRight: '8px' }} />
                Annuler
              </button>
            </>
          )}
          <Button
            variant="primary"
            onClick={() => {
              setOrderPrefill(null)
              setIsPlaceOrderModalOpen(true)
            }}
          >
            <Plus style={{ width: '16px', height: '16px', marginRight: '8px' }} />
            Nouvel Ordre
          </Button>
          <Button
            variant="outline"
            onClick={() => setIsDiversifyModalOpen(true)}
            title="3 suggestions d’actions pour diversifier (IA Gemini)"
          >
            <Sparkles style={{ width: '16px', height: '16px', marginRight: '8px' }} />
            Suggérer 3 actions (IA)
          </Button>
          <Button
            variant="outline"
            onClick={handleSyncOrders}
            disabled={loading}
          >
            <RefreshCw style={{ width: '16px', height: '16px', marginRight: '8px', animation: loading ? 'spin 1s linear infinite' : 'none' }} />
            Synchroniser
          </Button>
        </div>
      </div>

      {/* Barre d'avertissement si modifications non sauvegardées */}
      {hasUnsavedChanges && (
        <div className="warning-banner">
          ⚠️ Vous avez <strong>{modifiedOrders.size + newOrders.length} modification(s)</strong> non sauvegardée(s). N'oubliez pas d'enregistrer !
        </div>
      )}

      {/* Erreur */}
      {error && (
        <div className="error-banner">
          <Badge variant="danger">Erreur</Badge>
          <span>{error}</span>
          <Button onClick={loadOrders} variant="outline" size="sm">Réessayer</Button>
        </div>
      )}

      {/* Filtres */}
      <div className="orders-filters">
        <div className="filter-search">
          <Search className="search-icon" />
          <input
            type="text"
            placeholder="Rechercher un asset..."
            value={filters.search}
            onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
            className="filter-input"
          />
        </div>

        <select
          value={filters.broker}
          onChange={(e) => setFilters(prev => ({ ...prev, broker: e.target.value }))}
          className="filter-select"
        >
          <option value="">Tous les brokers</option>
          {brokers.map(broker => (
            <option key={broker.id} value={broker.name || broker.broker_type}>
              {broker.name || broker.broker_type}
            </option>
          ))}
        </select>

        <select
          value={filters.status}
          onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value }))}
          className="filter-select"
        >
          <option value="">Tous les statuts</option>
          <option value="PENDING">En attente</option>
          <option value="OPEN">Ouvert</option>
          <option value="FILLED">Exécuté</option>
          <option value="PARTIALLY_FILLED">Partiel</option>
          <option value="CANCELLED">Annulé</option>
          <option value="REJECTED">Rejeté</option>
        </select>

        <select
          value={filters.side}
          onChange={(e) => setFilters(prev => ({ ...prev, side: e.target.value }))}
          className="filter-select"
        >
          <option value="">Achat/Vente</option>
          <option value="BUY">Achat</option>
          <option value="SELL">Vente</option>
        </select>
      </div>

      {/* Stats */}
      <div className="orders-stats">
        <Card>
          <div className="stat-item">
            <span className="stat-label">En attente</span>
            <span className="stat-value">{pendingOrders.length}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Exécutés</span>
            <span className="stat-value">{filledOrders.length}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Total</span>
            <span className="stat-value">{orders.length}</span>
          </div>
        </Card>
      </div>

      {/* Table */}
      <Card>
        {orders.length === 0 ? (
          <div className="empty-state">
            <p>Aucun ordre trouvé</p>
            <Button
              variant="primary"
              onClick={() => {
                setOrderPrefill(null)
                setIsPlaceOrderModalOpen(true)
              }}
            >
              Passer votre premier ordre
            </Button>
          </div>
        ) : (
          <>
            <Table
              columns={columns}
              data={sortedOrders}
              sortConfig={sortConfig}
              onSort={handleSort}
              visibleColumns={visibleColumns.length > 0 ? visibleColumns : undefined}
            />
            {sortedOrders.length === 0 && (
              <div className="empty-state">
                <p>Aucun ordre ne correspond aux filtres</p>
              </div>
            )}
          </>
        )}
      </Card>

      {/* Tableau des Positions */}
      <Card className="positions-card">
        <div className="positions-header">
          <h2 className="positions-title">
            📊 Positions ouvertes
            {positions.length > 0 && (
              <span style={{ marginLeft: '8px', display: 'inline-flex' }}>
                <Badge variant="info">{positions.length}</Badge>
              </span>
            )}
          </h2>
          <Button
            variant="outline"
            size="sm"
            onClick={loadPositions}
            disabled={positionsLoading}
          >
            <RefreshCw style={{
              width: '14px',
              height: '14px',
              marginRight: '6px',
              animation: positionsLoading ? 'spin 1s linear infinite' : 'none'
            }} />
            Actualiser
          </Button>
        </div>

        {positionsLoading ? (
          <div className="positions-loading">
            <Loading size="sm" />
            <span>Chargement des positions...</span>
          </div>
        ) : positions.length === 0 ? (
          <div className="positions-empty">
            <p>Aucune position ouverte</p>
          </div>
        ) : (
          <div className="positions-table-container">
            <table className="positions-table">
              <thead>
                <tr>
                  <th>Symbole (Broker)</th>
                  <th>Symbole (Yahoo)</th>
                  <th>Nom</th>
                  <th>Côté</th>
                  <th>Quantité</th>
                  <th>Prix d'entrée</th>
                  <th>Prix actuel</th>
                  <th>P&L</th>
                  <th>P&L %</th>
                  <th>Qté à vendre</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((position) => {
                  // Utiliser quantity (backend) et fallback à size si nécessaire
                  const positionSize = Number(position.quantity) || Number(position.size) || 0

                  // Calculer le P&L si non disponible directement
                  let positionPnl = Number(position.pnl) || 0
                  let positionPnlPercent = Number(position.pnl_percent) || 0

                  const sellQty = sellQuantities.get(position.id) ?? positionSize
                  const isSelling = sellingPosition === position.id

                  // Déterminer le symbole à afficher
                  const displaySymbol = position.symbol || position.all_asset_symbol || position.asset?.symbol || 'N/A'
                  const yahooSymbol = position.all_asset_yahoo_symbol || position.all_asset?.symbole_yahoo || '-'
                  const displayName = position.all_asset_name || position.asset?.name || '-'

                  // Prix actuel (préférence pour Yahoo si dispo, sinon broker)
                  const currentPrice = position.yahoo_current_price || position.current_price

                  return (
                    <tr key={position.id}>
                      <td className="symbol-cell">
                        <Link to={`/positions/${position.id}`} className="link-symbol">
                          <strong>{displaySymbol}</strong>
                        </Link>
                      </td>
                      <td className="yahoo-symbol-cell">
                        <span className="text-sm text-gray-500">{yahooSymbol}</span>
                      </td>
                      <td className="name-cell">
                        {displayName}
                      </td>
                      <td>
                        <Badge variant={position.side === 'BUY' ? 'success' : 'danger'}>
                          {position.side === 'BUY' ? 'LONG' : position.side === 'SELL' ? 'SHORT' : position.side}
                        </Badge>
                      </td>
                      <td className="number-cell font-mono">{positionSize.toFixed(4)}</td>
                      <td className="number-cell font-mono">
                        {formatCurrency(position.entry_price || 0)}
                      </td>
                      <td className="number-cell font-mono">
                        {currentPrice ? formatCurrency(currentPrice) : '-'}
                      </td>
                      <td className={`number-cell font-mono ${positionPnl >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                        {positionPnl >= 0 ? '+' : ''}{formatCurrency(positionPnl)}
                      </td>
                      <td className={`number-cell font-mono ${positionPnlPercent >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                        {positionPnlPercent >= 0 ? '+' : ''}{positionPnlPercent.toFixed(2)}%
                      </td>
                      <td className="sell-quantity-cell">
                        <input
                          type="number"
                          value={sellQty}
                          onChange={(e) => {
                            const newQty = parseFloat(e.target.value) || 0
                            setSellQuantities(prev => {
                              const newMap = new Map(prev)
                              newMap.set(position.id, newQty)
                              return newMap
                            })
                          }}
                          min="0"
                          max={positionSize}
                          step="any"
                          className="sell-quantity-input"
                          disabled={isSelling}
                        />
                        <button
                          className="sell-max-btn"
                          onClick={() => {
                            setSellQuantities(prev => {
                              const newMap = new Map(prev)
                              newMap.set(position.id, positionSize)
                              return newMap
                            })
                          }}
                          title="Quantité max"
                          disabled={isSelling}
                        >
                          MAX
                        </button>
                      </td>
                      <td>
                        <button
                          className="sell-button"
                          onClick={() => handleSellPosition(position)}
                          disabled={isSelling || sellQty <= 0}
                        >
                          {isSelling ? (
                            <>
                              <RefreshCw style={{ width: '14px', height: '14px', animation: 'spin 1s linear infinite' }} />
                              Vente...
                            </>
                          ) : (
                            <>
                              <TrendingUp style={{ width: '14px', height: '14px' }} />
                              Vendre
                            </>
                          )}
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Footer */}
      <div className="orders-footer">
        <div className="footer-info">
          Total: {sortedOrders.length} ordre(s)
          {hasUnsavedChanges && (
            <span className="footer-warning">
              • {modifiedOrders.size + newOrders.length} modification(s) non sauvegardée(s)
            </span>
          )}
        </div>
        <div className="footer-hint">
          💡 Double-cliquez sur Quantité, Prix ou Stop Prix pour éditer • Les modifications sont automatiquement enregistrées localement
        </div>
      </div>

      {/* Modal de placement d'ordre */}
      <AIDiversifyModal
        isOpen={isDiversifyModalOpen}
        onClose={() => setIsDiversifyModalOpen(false)}
        onPickOrder={(payload) => {
          setIsDiversifyModalOpen(false)
          setOrderPrefill(payload)
          setIsPlaceOrderModalOpen(true)
        }}
      />

      <PlaceOrderModal
        isOpen={isPlaceOrderModalOpen}
        initialAllAssetId={orderPrefill?.allAssetId ?? undefined}
        initialSymbol={orderPrefill?.symbol}
        initialSide={orderPrefill?.side}
        onClose={() => {
          setIsPlaceOrderModalOpen(false)
          setOrderPrefill(null)
        }}
        onSuccess={() => {
          loadOrders()
          setIsPlaceOrderModalOpen(false)
          setOrderPrefill(null)
        }}
      />
    </div>
  )
}
