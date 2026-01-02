/**
 * Composant DataTreeTable - Tableau hiérarchique avec Assets, Positions et Orders
 * 
 * Affiche les assets comme lignes parents avec une flèche déroulante.
 * Quand on clique sur la flèche, les positions et orders de l'asset
 * sont affichés comme lignes enfants indentées.
 */
import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  ChevronRight, 
  ChevronDown, 
  Eye, 
  Trash2, 
  XCircle, 
  Edit2,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Package
} from 'lucide-react'
import { Badge, Button } from '@components/common'
import { formatCurrency } from '@utils/format'
import type { AssetWithChildren, PositionChild, OrderChild } from '@types'
import './DataTreeTable.css'

interface DataTreeTableProps {
  data: AssetWithChildren[]
  onSellPosition?: (positionId: number) => void
  onCancelOrder?: (orderId: number) => void
  onDeleteOrder?: (orderId: number) => void
  onEditOrder?: (orderId: number) => void
  onClosePosition?: (positionId: number) => void
  loading?: boolean
}

export default function DataTreeTable({
  data,
  onSellPosition,
  onCancelOrder,
  onDeleteOrder,
  onEditOrder,
  onClosePosition,
  loading = false,
}: DataTreeTableProps) {
  const navigate = useNavigate()
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())

  // Toggle expand/collapse pour une ligne
  const toggleRow = useCallback((id: string) => {
    setExpandedRows(prev => {
      const newSet = new Set(prev)
      if (newSet.has(id)) {
        newSet.delete(id)
      } else {
        newSet.add(id)
      }
      return newSet
    })
  }, [])

  // Expand/collapse all
  const expandAll = useCallback(() => {
    const allIds = data.filter(a => a.has_children).map(a => a.id)
    setExpandedRows(new Set(allIds))
  }, [data])

  const collapseAll = useCallback(() => {
    setExpandedRows(new Set())
  }, [])

  // Navigation vers les détails
  const handleViewPosition = (positionId: number) => {
    navigate(`/positions/${positionId}`)
  }

  const handleViewOrder = (orderId: number) => {
    navigate(`/orders?order_id=${orderId}`)
  }

  const handleViewAsset = (assetId: number) => {
    navigate(`/assets/${assetId}`)
  }

  // Rendu d'une ligne enfant Position
  const renderPositionRow = (position: PositionChild, assetId: string) => {
    const isOpen = position.status === 'OPEN'
    const pnlClass = position.pnl >= 0 ? 'pnl-positive' : 'pnl-negative'
    
    return (
      <tr 
        key={position.id} 
        className="child-row position-row"
      >
        <td className="toggle-cell"></td>
        <td className="indented-cell">
          <span className="child-icon">📊</span>
          <span className="child-label">Position</span>
        </td>
        <td className="center-cell">
          <Badge variant={position.side === 'LONG' ? 'success' : 'danger'}>
            {position.side}
          </Badge>
        </td>
        <td className="number-cell">{position.size.toFixed(4)}</td>
        <td className="number-cell">{formatCurrency(position.entry_price)}</td>
        <td className="number-cell">
          {position.current_price ? formatCurrency(position.current_price) : '-'}
        </td>
        <td className={`number-cell ${pnlClass}`}>
          {position.pnl >= 0 ? '+' : ''}{formatCurrency(position.pnl)}
          <span className="pnl-percent">
            ({position.pnl_percent >= 0 ? '+' : ''}{position.pnl_percent.toFixed(2)}%)
          </span>
        </td>
        <td className="center-cell">
          <Badge variant={isOpen ? 'success' : 'secondary'}>
            {position.status}
          </Badge>
        </td>
        <td className="actions-cell">
          <button 
            className="action-btn view-btn" 
            onClick={() => handleViewPosition(position.position_id)}
            title="Voir les détails"
          >
            <Eye size={14} />
          </button>
          {isOpen && onSellPosition && (
            <button 
              className="action-btn sell-btn" 
              onClick={() => onSellPosition(position.position_id)}
              title="Vendre la position"
            >
              <TrendingDown size={14} />
            </button>
          )}
          {isOpen && onClosePosition && (
            <button 
              className="action-btn close-btn" 
              onClick={() => onClosePosition(position.position_id)}
              title="Fermer la position"
            >
              <XCircle size={14} />
            </button>
          )}
        </td>
      </tr>
    )
  }

  // Rendu d'une ligne enfant Order
  const renderOrderRow = (order: OrderChild, assetId: string) => {
    const isPending = ['PENDING', 'OPEN'].includes(order.status)
    const canCancel = isPending
    const canEdit = isPending
    
    return (
      <tr 
        key={order.id} 
        className="child-row order-row"
      >
        <td className="toggle-cell"></td>
        <td className="indented-cell">
          <span className="child-icon">📋</span>
          <span className="child-label">Order</span>
        </td>
        <td className="center-cell">
          <Badge variant={order.side === 'BUY' ? 'success' : 'danger'}>
            {order.side}
          </Badge>
        </td>
        <td className="number-cell">
          {order.filled_quantity > 0 
            ? `${order.filled_quantity.toFixed(4)} / ${order.quantity.toFixed(4)}`
            : order.quantity.toFixed(4)
          }
        </td>
        <td className="number-cell">
          {order.price ? formatCurrency(order.price) : 'Market'}
        </td>
        <td className="number-cell">
          {order.stop_price ? formatCurrency(order.stop_price) : '-'}
        </td>
        <td className="center-cell">
          <Badge variant="outline">{order.order_type}</Badge>
        </td>
        <td className="center-cell">
          <Badge 
            variant={
              order.status === 'FILLED' ? 'success' :
              order.status === 'CANCELLED' ? 'secondary' :
              order.status === 'REJECTED' ? 'danger' :
              isPending ? 'warning' : 'outline'
            }
          >
            {order.status}
          </Badge>
        </td>
        <td className="actions-cell">
          <button 
            className="action-btn view-btn" 
            onClick={() => handleViewOrder(order.order_id)}
            title="Voir les détails"
          >
            <Eye size={14} />
          </button>
          {canEdit && onEditOrder && (
            <button 
              className="action-btn edit-btn" 
              onClick={() => onEditOrder(order.order_id)}
              title="Modifier l'ordre"
            >
              <Edit2 size={14} />
            </button>
          )}
          {canCancel && onCancelOrder && (
            <button 
              className="action-btn cancel-btn" 
              onClick={() => onCancelOrder(order.order_id)}
              title="Annuler l'ordre"
            >
              <XCircle size={14} />
            </button>
          )}
          {onDeleteOrder && (
            <button 
              className="action-btn delete-btn" 
              onClick={() => onDeleteOrder(order.order_id)}
              title="Supprimer l'ordre"
            >
              <Trash2 size={14} />
            </button>
          )}
        </td>
      </tr>
    )
  }

  // Rendu d'une ligne parent Asset
  const renderAssetRow = (asset: AssetWithChildren) => {
    const isExpanded = expandedRows.has(asset.id)
    const hasChildren = asset.has_children
    const pnlClass = asset.total_pnl >= 0 ? 'pnl-positive' : 'pnl-negative'

    return (
      <>
        <tr 
          key={asset.id} 
          className={`parent-row ${isExpanded ? 'expanded' : ''}`}
          onClick={() => hasChildren && toggleRow(asset.id)}
        >
          <td className="toggle-cell" onClick={(e) => e.stopPropagation()}>
            {hasChildren ? (
              <span className="toggle-icon" onClick={() => toggleRow(asset.id)}>
                {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              </span>
            ) : (
              <span className="toggle-icon disabled">
                <Package size={14} />
              </span>
            )}
          </td>
          <td className="symbol-cell">
            <strong>{asset.symbol}</strong>
            <span className="asset-name">{asset.name}</span>
          </td>
          <td className="center-cell">
            <Badge variant="info">{asset.asset_type || 'N/A'}</Badge>
          </td>
          <td className="number-cell">
            {asset.total_position_size > 0 ? asset.total_position_size.toFixed(4) : '-'}
          </td>
          <td className="number-cell">
            {asset.current_price ? formatCurrency(asset.current_price) : '-'}
          </td>
          <td className="number-cell">
            {asset.net_position !== 0 ? (
              <span className={asset.net_position > 0 ? 'net-positive' : 'net-negative'}>
                {asset.net_position > 0 ? '+' : ''}{asset.net_position.toFixed(4)}
              </span>
            ) : '-'}
          </td>
          <td className={`number-cell ${asset.total_pnl !== 0 ? pnlClass : ''}`}>
            {asset.total_pnl !== 0 ? (
              <>
                {asset.total_pnl >= 0 ? '+' : ''}{formatCurrency(asset.total_pnl)}
              </>
            ) : '-'}
          </td>
          <td className="center-cell">
            <div className="counts-cell">
              {asset.positions_count > 0 && (
                <Badge variant="success" title="Positions ouvertes">
                  {asset.positions_count} pos
                </Badge>
              )}
              {asset.pending_orders_count > 0 && (
                <Badge variant="warning" title="Orders en attente">
                  {asset.pending_orders_count} ord
                </Badge>
              )}
              {!hasChildren && (
                <span className="no-children">Aucun</span>
              )}
            </div>
          </td>
          <td className="actions-cell" onClick={(e) => e.stopPropagation()}>
            <button 
              className="action-btn view-btn" 
              onClick={() => handleViewAsset(asset.asset_id)}
              title="Voir l'asset"
            >
              <Eye size={14} />
            </button>
          </td>
        </tr>
        
        {/* Lignes enfants (positions + orders) */}
        {isExpanded && asset.children.map(child => {
          if (child.type === 'position') {
            return renderPositionRow(child as PositionChild, asset.id)
          } else {
            return renderOrderRow(child as OrderChild, asset.id)
          }
        })}
      </>
    )
  }

  if (loading) {
    return (
      <div className="datatree-loading">
        <div className="spinner"></div>
        <p>Chargement des données...</p>
      </div>
    )
  }

  if (data.length === 0 && !loading) {
    return (
      <div className="datatree-empty">
        <Package size={48} />
        <p>Aucun asset avec positions ou orders trouvé</p>
        <p className="empty-hint">Les assets apparaîtront ici une fois que vous aurez des positions ou des orders actifs.</p>
      </div>
    )
  }

  const assetsWithChildren = data.filter(a => a.has_children).length

  return (
    <div className="datatree-container">
      {/* Toolbar */}
      <div className="datatree-toolbar">
        <div className="toolbar-info">
          <span>{data.length} assets</span>
          {assetsWithChildren > 0 && (
            <span className="toolbar-separator">•</span>
          )}
          {assetsWithChildren > 0 && (
            <span>{assetsWithChildren} avec positions/orders</span>
          )}
        </div>
        <div className="toolbar-actions">
          <Button variant="outline" size="small" onClick={expandAll}>
            Tout déplier
          </Button>
          <Button variant="outline" size="small" onClick={collapseAll}>
            Tout replier
          </Button>
        </div>
      </div>

      {/* Table */}
      <div className="datatree-table-wrapper">
        <table className="datatree-table">
          <thead>
            <tr>
              <th className="th-toggle"></th>
              <th className="th-symbol">Symbole / Nom</th>
              <th className="th-type">Type / Côté</th>
              <th className="th-quantity">Quantité</th>
              <th className="th-price">Prix</th>
              <th className="th-net">Net / Stop</th>
              <th className="th-pnl">P&L</th>
              <th className="th-status">Statut</th>
              <th className="th-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            {data.map(asset => renderAssetRow(asset))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

