/**
 * Page Orders - Liste et gestion des ordres
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Card, Button, Table, Badge, Loading } from '@components/common'
import PlaceOrderModal from '@components/orders/PlaceOrderModal'
import { orderService } from '@services'
import { formatCurrency, formatDate } from '@utils/format'
import type { Order } from '@types'
import './Orders.css'

export default function Orders() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isPlaceOrderModalOpen, setIsPlaceOrderModalOpen] = useState(false)

  const loadOrders = async () => {
    try {
      setLoading(true)
      setError(null)
      const filters: any = {}
      if (statusFilter) {
        filters.status = statusFilter
      }
      const response = await orderService.getAll(filters)
      setOrders(response.results || [])
    } catch (err: any) {
      setError(err.error || 'Erreur lors du chargement des ordres')
      console.error('Erreur:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadOrders()
  }, [statusFilter])

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'FILLED':
        return 'success'
      case 'OPEN':
      case 'PENDING':
        return 'info'
      case 'PARTIALLY_FILLED':
        return 'warning'
      case 'CANCELLED':
      case 'REJECTED':
      case 'EXPIRED':
        return 'error'
      default:
        return 'default'
    }
  }

  const getOrderTypeLabel = (type: string) => {
    switch (type) {
      case 'MARKET':
        return 'Market'
      case 'LIMIT':
        return 'Limit'
      case 'STOP':
        return 'Stop'
      case 'STOP_LIMIT':
        return 'Stop Limit'
      default:
        return type
    }
  }

  const handleCancel = async (id: number) => {
    if (!confirm('Êtes-vous sûr de vouloir annuler cet ordre ?')) {
      return
    }

    try {
      await orderService.cancel(id)
      loadOrders()
    } catch (err: any) {
      alert(err.error || 'Erreur lors de l\'annulation')
      console.error('Erreur:', err)
    }
  }

  const columns = [
    {
      key: 'symbol',
      label: 'Symbole',
      render: (_value: any, row: Order) => (
        <Link to={`/assets/${row?.asset?.id || ''}`} className="link-symbol">
          {row?.asset?.symbol || 'N/A'}
        </Link>
      ),
    },
    {
      key: 'side',
      label: 'Sens',
      render: (value: string) => (
        <Badge variant={value === 'BUY' ? 'success' : 'error'}>
          {value}
        </Badge>
      ),
    },
    {
      key: 'order_type',
      label: 'Type',
      render: (value: string) => getOrderTypeLabel(value),
    },
    {
      key: 'quantity',
      label: 'Quantité',
      render: (value: any) => {
        const numValue = typeof value === 'string' ? parseFloat(value) : (value || 0)
        return isNaN(numValue) ? '0.0000' : numValue.toFixed(4)
      },
    },
    {
      key: 'filled_quantity',
      label: 'Exécuté',
      render: (value: any, row: Order) => {
        const numValue = typeof value === 'string' ? parseFloat(value) : (value || 0)
        const numQuantity = typeof row.quantity === 'string' ? parseFloat(row.quantity) : (row.quantity || 0)
        const percentage = numQuantity > 0 ? ((numValue / numQuantity) * 100).toFixed(1) : '0'
        const formattedValue = isNaN(numValue) ? '0.0000' : numValue.toFixed(4)
        return `${formattedValue} (${percentage}%)`
      },
    },
    {
      key: 'price',
      label: 'Prix',
      render: (value: any) => {
        if (!value) return 'Market'
        const numValue = typeof value === 'string' ? parseFloat(value) : value
        return isNaN(numValue) ? 'Market' : formatCurrency(numValue)
      },
    },
    {
      key: 'status',
      label: 'Statut',
      render: (value: string) => (
        <Badge variant={getStatusBadgeVariant(value)}>
          {value}
        </Badge>
      ),
    },
    {
      key: 'created_at',
      label: 'Créé le',
      render: (value: string) => formatDate(value),
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (_value: any, row: Order) => (
        <div className="table-actions">
          {['PENDING', 'OPEN', 'PARTIALLY_FILLED'].includes(row.status) && (
            <Button
              variant="outline"
              size="small"
              onClick={() => handleCancel(row.id)}
            >
              Annuler
            </Button>
          )}
        </div>
      ),
    },
  ]

  if (loading) {
    return (
      <div className="page-container">
        <Loading />
      </div>
    )
  }

  if (error) {
    return (
      <div className="page-container">
        <Card>
          <div className="error-message">{error}</div>
          <Button onClick={loadOrders}>Réessayer</Button>
        </Card>
      </div>
    )
  }

  const pendingOrders = orders.filter((o) => ['PENDING', 'OPEN', 'PARTIALLY_FILLED'].includes(o.status))
  const filledOrders = orders.filter((o) => o.status === 'FILLED')

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Ordres</h1>
        <div className="page-actions">
          <Button 
            variant="primary" 
            onClick={() => setIsPlaceOrderModalOpen(true)}
          >
            Passer un ordre
          </Button>
        </div>
      </div>

      <div className="filters-section">
        <div className="filter-buttons">
          <Button
            variant={statusFilter === undefined ? 'primary' : 'outline'}
            onClick={() => setStatusFilter(undefined)}
          >
            Tous
          </Button>
          <Button
            variant={statusFilter === 'PENDING' ? 'primary' : 'outline'}
            onClick={() => setStatusFilter('PENDING')}
          >
            En attente
          </Button>
          <Button
            variant={statusFilter === 'OPEN' ? 'primary' : 'outline'}
            onClick={() => setStatusFilter('OPEN')}
          >
            Ouverts
          </Button>
          <Button
            variant={statusFilter === 'FILLED' ? 'primary' : 'outline'}
            onClick={() => setStatusFilter('FILLED')}
          >
            Exécutés
          </Button>
        </div>
      </div>

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

      <Card>
        {orders.length === 0 ? (
          <div className="empty-state">
            <p>Aucun ordre trouvé</p>
            <Button variant="primary" onClick={() => setIsPlaceOrderModalOpen(true)}>
              Passer votre premier ordre
            </Button>
          </div>
        ) : (
          <Table columns={columns} data={orders} />
        )}
      </Card>

      <PlaceOrderModal
        isOpen={isPlaceOrderModalOpen}
        onClose={() => setIsPlaceOrderModalOpen(false)}
        onSuccess={() => {
          loadOrders()
          setIsPlaceOrderModalOpen(false)
        }}
      />
    </div>
  )
}

