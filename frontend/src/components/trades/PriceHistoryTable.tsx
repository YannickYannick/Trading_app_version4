/**
 * Composant Tableau pour afficher l'historique des prix d'un AllAsset
 */
import { useState, useEffect } from 'react'
import { Table, Loading, Badge } from '@components/common'
import { assetService } from '@services/assets'
import { formatCurrency, formatDate } from '@utils/format'
import './PriceHistoryTable.css'

export interface PriceHistoryTableProps {
  allAssetId: number | null
  allAssetSymbol?: string
  days?: number
}

interface PriceHistoryPoint {
  date: string
  open: number | null
  high: number | null
  low: number | null
  close: number | null
  volume: number
  source?: string
}

export default function PriceHistoryTable({
  allAssetId,
  allAssetSymbol,
  days = 365,
}: PriceHistoryTableProps) {
  const [priceHistory, setPriceHistory] = useState<PriceHistoryPoint[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!allAssetId) {
      setPriceHistory([])
      return
    }

    const loadHistory = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await assetService.getPriceHistory(allAssetId, days, 'list')
        if (data.results && data.results.length > 0) {
          // Trier par date décroissante (plus récent en premier)
          const sorted = [...data.results].sort((a, b) => {
            return new Date(b.date).getTime() - new Date(a.date).getTime()
          })
          setPriceHistory(sorted)
        } else {
          setPriceHistory([])
        }
      } catch (err: any) {
        console.error('Error loading price history:', err)
        setError(err.message || 'Erreur lors du chargement de l\'historique')
        setPriceHistory([])
      } finally {
        setLoading(false)
      }
    }

    loadHistory()
  }, [allAssetId, days])

  if (!allAssetId) {
    return (
      <div className="price-history-table-empty">
        <p>Sélectionnez un AllAsset pour afficher son historique de prix</p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="price-history-table-loading">
        <Loading text="Chargement de l'historique des prix..." />
      </div>
    )
  }

  if (error) {
    return (
      <div className="price-history-table-error">
        <p>Erreur: {error}</p>
      </div>
    )
  }

  if (priceHistory.length === 0) {
    return (
      <div className="price-history-table-empty">
        <p>
          Aucun historique de prix disponible pour {allAssetSymbol || `l'asset #${allAssetId}`}
        </p>
        <p className="price-history-table-hint">
          Utilisez le bouton "📊 Synchro Historique" pour charger les données
        </p>
      </div>
    )
  }

  const columns = [
    {
      key: 'date',
      label: 'Date',
      align: 'center' as const,
      render: (_value: any, row: PriceHistoryPoint) => formatDate(row.date, 'dd/MM/yyyy'),
    },
    {
      key: 'open',
      label: 'Ouverture',
      align: 'right' as const,
      render: (_value: any, row: PriceHistoryPoint) =>
        row.open !== null && row.open !== undefined ? formatCurrency(row.open) : 'N/A',
    },
    {
      key: 'high',
      label: 'Haut',
      align: 'right' as const,
      render: (_value: any, row: PriceHistoryPoint) =>
        row.high !== null && row.high !== undefined ? formatCurrency(row.high) : 'N/A',
    },
    {
      key: 'low',
      label: 'Bas',
      align: 'right' as const,
      render: (_value: any, row: PriceHistoryPoint) =>
        row.low !== null && row.low !== undefined ? formatCurrency(row.low) : 'N/A',
    },
    {
      key: 'close',
      label: 'Clôture',
      align: 'right' as const,
      render: (_value: any, row: PriceHistoryPoint) =>
        row.close !== null && row.close !== undefined ? (
          <span className="price-close">{formatCurrency(row.close)}</span>
        ) : (
          'N/A'
        ),
    },
    {
      key: 'volume',
      label: 'Volume',
      align: 'right' as const,
      render: (_value: any, row: PriceHistoryPoint) =>
        row.volume ? row.volume.toLocaleString('fr-FR') : '0',
    },
    {
      key: 'source',
      label: 'Source',
      align: 'center' as const,
      render: (_value: any, row: PriceHistoryPoint) =>
        row.source ? (
          <Badge variant={row.source === 'YAHOO' ? 'success' : 'secondary'}>
            {row.source}
          </Badge>
        ) : (
          'N/A'
        ),
    },
  ]

  return (
    <div className="price-history-table-container">
      <div className="price-history-table-header">
        <h3>
          Historique des prix - {allAssetSymbol || `Asset #${allAssetId}`}
        </h3>
        <span className="price-history-table-count">
          {priceHistory.length} jour(s) disponible(s)
        </span>
      </div>
      <Table
        columns={columns}
        data={priceHistory}
        keyExtractor={(row) => row.date}
        className="price-history-table"
      />
    </div>
  )
}

