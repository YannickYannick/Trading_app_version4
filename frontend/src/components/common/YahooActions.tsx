/**
 * Composant YahooActions - Boutons pour validation Yahoo et synchronisation historique
 */
import { useState } from 'react'
import Button from './Button'
import { assetService } from '@services/assets'
import './YahooActions.css'

export interface YahooActionsProps {
  allAssetId?: number | null
  allAssetSymbol?: string
  onSuccess?: () => void
  compact?: boolean // Mode compact pour les colonnes de table
}

export default function YahooActions({
  allAssetId,
  allAssetSymbol,
  onSuccess,
  compact = false,
}: YahooActionsProps) {
  const [validating, setValidating] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null)
  const [duration, setDuration] = useState('365')
  const [interval, setInterval] = useState('1d')

  if (!allAssetId) {
    return <span className="yahoo-actions-empty">N/A</span>
  }

  const handleValidate = async () => {
    if (!allAssetId) return
    
    setValidating(true)
    setMessage(null)
    
    try {
      const result = await assetService.validateYahoo(allAssetId)
      
      if (result.success) {
        setMessage({
          text: result.message || `Symbole Yahoo validé: ${result.yahoo_symbol || 'OK'}`,
          type: 'success',
        })
        if (onSuccess) {
          setTimeout(() => {
            onSuccess()
            setMessage(null)
          }, 2000)
        } else {
          setTimeout(() => setMessage(null), 5000)
        }
      } else {
        setMessage({
          text: result.error || result.message || 'Validation échouée',
          type: 'error',
        })
        setTimeout(() => setMessage(null), 5000)
      }
    } catch (error: any) {
      setMessage({
        text: error.message || 'Erreur lors de la validation',
        type: 'error',
      })
      setTimeout(() => setMessage(null), 5000)
    } finally {
      setValidating(false)
    }
  }

  const handleSync = async () => {
    if (!allAssetId) return
    
    setSyncing(true)
    setMessage(null)
    
    try {
      const result = await assetService.syncPriceHistory(
        allAssetId,
        parseInt(duration),
        interval
      )
      
      if (result.success) {
        setMessage({
          text: `${result.records || 0} enregistrements synchronisés avec succès`,
          type: 'success',
        })
        if (onSuccess) {
          setTimeout(() => {
            onSuccess()
            setMessage(null)
          }, 2000)
        } else {
          setTimeout(() => setMessage(null), 5000)
        }
      } else {
        setMessage({
          text: result.error || result.message || 'Synchronisation échouée',
          type: 'error',
        })
        setTimeout(() => setMessage(null), 5000)
      }
    } catch (error: any) {
      setMessage({
        text: error.message || 'Erreur lors de la synchronisation',
        type: 'error',
      })
      setTimeout(() => setMessage(null), 5000)
    } finally {
      setSyncing(false)
    }
  }

  if (compact) {
    return (
      <div className="yahoo-actions-compact">
        <Button
          size="sm"
          variant="outline"
          onClick={handleValidate}
          disabled={validating}
          isLoading={validating}
          loadingText="⏳"
          title="Valider symbole Yahoo"
        >
          🔍
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={handleSync}
          disabled={syncing}
          isLoading={syncing}
          loadingText="⏳"
          title="Charger l'historique"
        >
          📊
        </Button>
        {message && (
          <div className={`yahoo-message yahoo-message-${message.type}`}>
            {message.text}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="yahoo-actions">
      <div className="yahoo-actions-header">
        <span className="yahoo-asset-symbol">{allAssetSymbol || 'Asset'}</span>
      </div>
      
      <div className="yahoo-actions-buttons">
        <Button
          size="sm"
          variant="primary"
          onClick={handleValidate}
          disabled={validating}
          isLoading={validating}
          loadingText="Validation..."
          fullWidth
        >
          🔍 Valider symbole Yahoo
        </Button>
      </div>

      <div className="yahoo-actions-sync">
        <div className="yahoo-sync-controls">
          <select
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            className="yahoo-select"
          >
            <option value="30">1 mois</option>
            <option value="90">3 mois</option>
            <option value="180">6 mois</option>
            <option value="365">1 an</option>
            <option value="730">2 ans</option>
            <option value="1825">5 ans</option>
          </select>
          <select
            value={interval}
            onChange={(e) => setInterval(e.target.value)}
            className="yahoo-select"
          >
            <option value="1d">1 jour</option>
            <option value="1wk">1 semaine</option>
            <option value="1mo">1 mois</option>
          </select>
        </div>
        <Button
          size="sm"
          variant="success"
          onClick={handleSync}
          disabled={syncing}
          isLoading={syncing}
          loadingText="Chargement..."
          fullWidth
        >
          📊 Charger l'historique
        </Button>
      </div>

      {message && (
        <div className={`yahoo-message yahoo-message-${message.type}`}>
          {message.text}
        </div>
      )}
    </div>
  )
}

