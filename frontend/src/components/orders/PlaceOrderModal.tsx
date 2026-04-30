/**
 * Modal pour placer un ordre
 */
import { useState, useEffect, useRef } from 'react'
import Button from '@components/common/Button'
import Input from '@components/common/Input'
import Loading from '@components/common/Loading'
import Badge from '@components/common/Badge'
import { orderService, brokerService, assetService } from '@services'
import { formatCurrency } from '@utils/format'
import type { BrokerAccount } from '@types'
import './PlaceOrderModal.css'

type OrderType = 'MARKET' | 'LIMIT' | 'STOP' | 'STOP_LIMIT'
type OrderSide = 'BUY' | 'SELL'

interface PlaceOrderModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  /** Pré-remplissage (ex. suggestion IA diversification) */
  initialAllAssetId?: number | null
  initialSymbol?: string
  initialSide?: OrderSide
}

export default function PlaceOrderModal({
  isOpen,
  onClose,
  onSuccess,
  initialAllAssetId,
  initialSymbol,
  initialSide,
}: PlaceOrderModalProps) {
  const [loading, setLoading] = useState(false)
  const [brokerAccounts, setBrokerAccounts] = useState<BrokerAccount[]>([])
  const [loadingAccounts, setLoadingAccounts] = useState(true)
  
  // Formulaire
  const [brokerAccountId, setBrokerAccountId] = useState<number | ''>('')
  const [symbol, setSymbol] = useState('')
  const [allAssetId, setAllAssetId] = useState<number | null>(null)  // ID AllAssets sélectionné
  const [side, setSide] = useState<OrderSide>('BUY')
  const [orderType, setOrderType] = useState<OrderType>('MARKET')
  const [quantity, setQuantity] = useState('')
  const [price, setPrice] = useState('')
  const [stopPrice, setStopPrice] = useState('')
  
  // Autocomplétion
  const [autocompleteResults, setAutocompleteResults] = useState<any[]>([])
  const [showAutocomplete, setShowAutocomplete] = useState(false)
  const [loadingAutocomplete, setLoadingAutocomplete] = useState(false)
  const autocompleteTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const symbolInputRef = useRef<HTMLInputElement>(null)
  /** Évite d'effacer symbole/AllAsset quand le 1er compte broker est auto-sélectionné au chargement */
  const skipNextBrokerClearRef = useRef(false)
  const prefillKeyRef = useRef<string | null>(null)
  
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [orderResult, setOrderResult] = useState<any>(null)
  
  // Prix actuel (broker + Yahoo)
  const [priceData, setPriceData] = useState<{
    broker: { price: number; currency: string; source: string } | null
    yahoo: { price: number; symbol: string } | null
  } | null>(null)
  const [loadingPrice, setLoadingPrice] = useState(false)
  const [priceError, setPriceError] = useState<string | null>(null)

  // Charger les broker accounts
  useEffect(() => {
    if (isOpen) {
      loadBrokerAccounts()
    }
  }, [isOpen])

  const loadBrokerAccounts = async () => {
    try {
      setLoadingAccounts(true)
      const response = await brokerService.getAccounts()
      const accounts = response.results || []
      setBrokerAccounts(accounts)
      if (accounts.length > 0 && !brokerAccountId) {
        skipNextBrokerClearRef.current = true
        setBrokerAccountId(accounts[0].id)
      }
    } catch (err: any) {
      console.error('Erreur lors du chargement des comptes:', err)
    } finally {
      setLoadingAccounts(false)
    }
  }

  // Autocomplétion
  const handleSymbolChange = async (value: string) => {
    setSymbol(value)
    setAllAssetId(null)  // Réinitialiser l'ID AllAssets
    
    if (value.length < 2) {
      setShowAutocomplete(false)
      setAutocompleteResults([])
      return
    }

    // Debounce: annuler la requête précédente
    if (autocompleteTimeoutRef.current) {
      clearTimeout(autocompleteTimeoutRef.current)
    }

    autocompleteTimeoutRef.current = setTimeout(async () => {
      try {
        setLoadingAutocomplete(true)
        
        // Récupérer la plateforme du broker sélectionné
        const selectedAccount = brokerAccounts.find(acc => acc.id === brokerAccountId)
        const platform = selectedAccount?.broker?.broker_type || selectedAccount?.broker_type
        
        // Si un broker est sélectionné, filtrer par sa plateforme
        // Sinon, rechercher dans tous les assets
        const results = await assetService.autocompleteAllAssets(value, platform || undefined)
        setAutocompleteResults(results)
        setShowAutocomplete(results.length > 0)
      } catch (err: any) {
        console.error('Erreur autocomplétion:', err)
        setAutocompleteResults([])
      } finally {
        setLoadingAutocomplete(false)
      }
    }, 300)  // Debounce de 300ms
  }

  const handleSelectAsset = (asset: any) => {
    setSymbol(asset.symbol)
    setAllAssetId(asset.id)  // Stocker l'ID AllAssets
    setShowAutocomplete(false)
    setAutocompleteResults([])
  }

  // Réinitialiser symbole quand l'utilisateur change de compte broker (pas au 1er auto-select)
  useEffect(() => {
    if (!brokerAccountId) return
    if (skipNextBrokerClearRef.current) {
      skipNextBrokerClearRef.current = false
      return
    }
    setSymbol('')
    setAllAssetId(null)
    setAutocompleteResults([])
    setShowAutocomplete(false)
    setPriceData(null)
    setPriceError(null)
  }, [brokerAccountId])

  // Pré-remplissage (IA / deep link) une fois les comptes chargés
  useEffect(() => {
    if (!isOpen) {
      prefillKeyRef.current = null
      return
    }
    if (loadingAccounts) return
    const hasPrefill =
      (initialSymbol != null && String(initialSymbol).trim() !== '') ||
      (initialAllAssetId != null && initialAllAssetId > 0)
    if (!hasPrefill) return
    const key = `${initialAllAssetId ?? ''}|${initialSymbol ?? ''}|${initialSide ?? ''}`
    if (prefillKeyRef.current === key) return
    prefillKeyRef.current = key
    if (initialSymbol != null && String(initialSymbol).trim() !== '') {
      setSymbol(String(initialSymbol).trim())
    }
    if (initialAllAssetId != null && initialAllAssetId > 0) {
      setAllAssetId(initialAllAssetId)
    }
    if (initialSide === 'BUY' || initialSide === 'SELL') {
      setSide(initialSide)
    }
    setQuantity('')
  }, [isOpen, loadingAccounts, initialSymbol, initialAllAssetId, initialSide])
  
  // Fonction pour récupérer les prix (broker + Yahoo)
  const fetchAssetPrice = async () => {
    if (!brokerAccountId || !symbol.trim() || !allAssetId) {
      return
    }
    
    setLoadingPrice(true)
    setPriceError(null)
    setPriceData(null)
    
    try {
      const result = await orderService.getAssetPrice({
        broker_account_id: brokerAccountId as number,
        symbol: symbol.trim().toUpperCase(),
        all_asset_id: allAssetId
      })
      
      if (result.success && result.broker_price.price) {
        setPriceData({
          broker: {
            price: result.broker_price.price,
            currency: result.broker_price.currency,
            source: result.broker_price.source
          },
          yahoo: result.yahoo_data.available && result.yahoo_data.price ? {
            price: result.yahoo_data.price,
            symbol: result.yahoo_data.symbol || symbol
          } : null
        })
        
        // Pré-remplir le prix pour les ordres LIMIT
        if (orderType === 'LIMIT' && !price) {
          setPrice(result.broker_price.price.toString())
        }
      } else {
        setPriceError(result.broker_price.error || 'Impossible de récupérer le prix')
      }
    } catch (err: any) {
      setPriceError(err.error || 'Erreur lors de la récupération du prix')
      console.error('Erreur récupération prix:', err)
    } finally {
      setLoadingPrice(false)
    }
  }
  
  // Récupérer automatiquement les prix quand l'asset est sélectionné
  useEffect(() => {
    if (allAssetId && brokerAccountId && symbol) {
      fetchAssetPrice()
    } else {
      setPriceData(null)
      setPriceError(null)
    }
  }, [allAssetId, brokerAccountId, symbol])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(false)
    setOrderResult(null)

    // Validation
    if (!brokerAccountId) {
      setError('Veuillez sélectionner un compte broker')
      return
    }
    if (!symbol.trim()) {
      setError('Veuillez saisir un symbole')
      return
    }
    if (!quantity || parseFloat(quantity) <= 0) {
      setError('Veuillez saisir une quantité valide')
      return
    }
    if (orderType === 'LIMIT' && (!price || parseFloat(price) <= 0)) {
      setError('Les ordres LIMIT nécessitent un prix')
      return
    }
    if (orderType === 'STOP' && (!stopPrice || parseFloat(stopPrice) <= 0)) {
      setError('Les ordres STOP nécessitent un prix stop')
      return
    }
    if (orderType === 'STOP_LIMIT' && ((!price || parseFloat(price) <= 0) || (!stopPrice || parseFloat(stopPrice) <= 0))) {
      setError('Les ordres STOP_LIMIT nécessitent un prix et un prix stop')
      return
    }

    setLoading(true)
    try {
      const orderData: any = {
        broker_account_id: brokerAccountId as number,
        symbol: symbol.trim().toUpperCase(),
        side,
        quantity,
        order_type: orderType,
        price: price || undefined,
        stop_price: stopPrice || undefined,
      }
      
      // Si all_asset_id est disponible, l'envoyer directement
      if (allAssetId) {
        orderData.all_asset_id = allAssetId
      }
      
      const result = await orderService.placeOrder(orderData)
      
      setOrderResult(result)
      setSuccess(true)
      setTimeout(() => {
        onSuccess()
        handleClose()
      }, 2000)
    } catch (err: any) {
      setError(err.error || err.message || 'Erreur lors du placement de l\'ordre')
      console.error('Erreur:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    // Reset form
    setSymbol('')
    setAllAssetId(null)
    setQuantity('')
    setPrice('')
    setStopPrice('')
    setError(null)
    setSuccess(false)
    setOrderResult(null)
    setAutocompleteResults([])
    setShowAutocomplete(false)
    setPriceData(null)
    setPriceError(null)
    if (autocompleteTimeoutRef.current) {
      clearTimeout(autocompleteTimeoutRef.current)
    }
    onClose()
  }

  const requiresPrice = orderType === 'LIMIT' || orderType === 'STOP_LIMIT'
  const requiresStopPrice = orderType === 'STOP' || orderType === 'STOP_LIMIT'

  if (!isOpen) return null

  return (
    <div className="place-order-modal-overlay" onClick={handleClose}>
      <div className="place-order-modal" onClick={(e) => e.stopPropagation()}>
        <div className="place-order-modal-header">
          <h2>Passer un ordre</h2>
          <button className="place-order-modal-close" onClick={handleClose} aria-label="Fermer">
            ×
          </button>
        </div>

        <div className="place-order-modal-body">
          {loadingAccounts ? (
            <Loading text="Chargement des comptes broker..." />
          ) : (
            <form onSubmit={handleSubmit} className="place-order-form">
              {/* Compte Broker */}
              <div className="form-group">
                <label htmlFor="broker-account">Compte Broker *</label>
                <select
                  id="broker-account"
                  value={brokerAccountId}
                  onChange={(e) => setBrokerAccountId(Number(e.target.value) || '')}
                  className="form-input"
                  required
                  disabled={loading}
                >
                  <option value="">-- Sélectionner un compte --</option>
                  {brokerAccounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.broker?.name || account.broker_type || 'Broker'}
                    </option>
                  ))}
                </select>
              </div>

              {/* Symbole avec autocomplétion */}
              <div className="form-group" style={{ position: 'relative' }}>
                <label htmlFor="symbol">Symbole *</label>
                <div style={{ position: 'relative' }}>
                  <Input
                    ref={symbolInputRef}
                    id="symbol"
                    type="text"
                    value={symbol}
                    onChange={(e) => handleSymbolChange(e.target.value)}
                    onFocus={() => {
                      if (autocompleteResults.length > 0) {
                        setShowAutocomplete(true)
                      }
                    }}
                    onBlur={() => {
                      // Délai pour permettre le clic sur les résultats
                      setTimeout(() => setShowAutocomplete(false), 200)
                    }}
                    placeholder="Ex: BTCUSDT, AAPL, EURUSD"
                    required
                    disabled={loading}
                    autoFocus
                  />
                  {brokerAccountId && (
                    <p className="form-hint" style={{ marginTop: '0.25rem', fontSize: '0.75rem' }}>
                      Recherche limitée aux assets {(() => {
                        const selectedAccount = brokerAccounts.find(acc => acc.id === brokerAccountId)
                        const platform = selectedAccount?.broker?.broker_type || selectedAccount?.broker_type
                        return platform || 'du broker sélectionné'
                      })()}
                    </p>
                  )}
                  
                  {/* Résultats autocomplétion */}
                  {showAutocomplete && autocompleteResults.length > 0 && (
                    <div className="autocomplete-dropdown">
                      {loadingAutocomplete ? (
                        <div className="autocomplete-item">Chargement...</div>
                      ) : (
                        autocompleteResults.map((asset) => (
                          <div
                            key={asset.id}
                            className="autocomplete-item"
                            onClick={() => handleSelectAsset(asset)}
                            onMouseDown={(e) => e.preventDefault()} // Empêcher le blur
                          >
                            <div className="autocomplete-symbol">{asset.symbol}</div>
                            <div className="autocomplete-name">{asset.name}</div>
                            <div className="autocomplete-platform">{asset.platform}</div>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Prix actuel - Broker + Yahoo */}
              {(priceData || loadingPrice || priceError) && (
                <div className="form-group">
                  <label>Prix actuel</label>
                  {loadingPrice ? (
                    <div className="price-loading">
                      <Loading size="sm" /> Chargement des prix...
                    </div>
                  ) : priceError ? (
                    <div className="price-error">
                      <Badge variant="warning">⚠️ {priceError}</Badge>
                    </div>
                  ) : priceData ? (
                    <div className="price-comparison">
                      {/* Prix Broker */}
                      {priceData.broker && (
                        <div className="price-item broker-price">
                          <div className="price-label">
                            <Badge variant="primary">{priceData.broker.source}</Badge>
                          </div>
                          <div className="price-value">
                            {formatCurrency(priceData.broker.price)} {priceData.broker.currency}
                          </div>
                        </div>
                      )}
                      
                      {/* Prix Yahoo */}
                      {priceData.yahoo ? (
                        <div className="price-item yahoo-price">
                          <div className="price-label">
                            <Badge variant="info">Yahoo</Badge>
                            <span className="yahoo-symbol">{priceData.yahoo.symbol}</span>
                          </div>
                          <div className="price-value">
                            {formatCurrency(priceData.yahoo.price)} USD
                          </div>
                          {/* Différence de prix */}
                          {priceData.broker && (
                            <div className="price-diff">
                              {(() => {
                                const diff = Math.abs(priceData.yahoo.price - priceData.broker.price)
                                const diffPercent = ((diff / priceData.broker.price) * 100).toFixed(2)
                                const isClose = parseFloat(diffPercent) < 1
                                return (
                                  <span className={isClose ? 'diff-close' : 'diff-far'}>
                                    {parseFloat(diffPercent) > 0.01 ? `±${diffPercent}%` : '≈'}
                                  </span>
                                )
                              })()}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="price-item yahoo-unavailable">
                          <Badge variant="secondary">Yahoo: Non disponible</Badge>
                        </div>
                      )}
                      
                      <Button
                        type="button"
                        variant="outline"
                        size="small"
                        onClick={fetchAssetPrice}
                        style={{ marginTop: '0.5rem', width: '100%' }}
                      >
                        🔄 Actualiser
                      </Button>
                    </div>
                  ) : null}
                </div>
              )}

              {/* Sens */}
              <div className="form-group">
                <label htmlFor="side">Sens *</label>
                <div className="side-buttons">
                  <button
                    type="button"
                    className={`side-button ${side === 'BUY' ? 'active buy' : ''}`}
                    onClick={() => setSide('BUY')}
                    disabled={loading}
                  >
                    Achat (BUY)
                  </button>
                  <button
                    type="button"
                    className={`side-button ${side === 'SELL' ? 'active sell' : ''}`}
                    onClick={() => setSide('SELL')}
                    disabled={loading}
                  >
                    Vente (SELL)
                  </button>
                </div>
              </div>

              {/* Type d'ordre */}
              <div className="form-group">
                <label htmlFor="order-type">Type d'ordre *</label>
                <select
                  id="order-type"
                  value={orderType}
                  onChange={(e) => setOrderType(e.target.value as OrderType)}
                  className="form-input"
                  required
                  disabled={loading}
                >
                  <option value="MARKET">Market (au marché)</option>
                  <option value="LIMIT">Limit (à cours limité)</option>
                  <option value="STOP">Stop</option>
                  <option value="STOP_LIMIT">Stop Limit</option>
                </select>
                <p className="form-hint">
                  {orderType === 'MARKET' && 'Exécuté immédiatement au meilleur prix disponible'}
                  {orderType === 'LIMIT' && 'Exécuté uniquement au prix spécifié ou meilleur'}
                  {orderType === 'STOP' && 'Déclenché quand le prix atteint le niveau stop'}
                  {orderType === 'STOP_LIMIT' && 'Stop avec prix limite'}
                </p>
              </div>

              {/* Quantité */}
              <div className="form-group">
                <label htmlFor="quantity">Quantité *</label>
                <Input
                  id="quantity"
                  type="number"
                  step="any"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  placeholder="0.0000"
                  required
                  disabled={loading}
                  min="0.0001"
                />
              </div>

              {/* Prix (si LIMIT ou STOP_LIMIT) */}
              {requiresPrice && (
                <div className="form-group">
                  <label htmlFor="price">Prix limite *</label>
                  <Input
                    id="price"
                    type="number"
                    step="any"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    placeholder="0.00"
                    required
                    disabled={loading}
                    min="0.0001"
                  />
                </div>
              )}

              {/* Prix Stop (si STOP ou STOP_LIMIT) */}
              {requiresStopPrice && (
                <div className="form-group">
                  <label htmlFor="stop-price">Prix stop *</label>
                  <Input
                    id="stop-price"
                    type="number"
                    step="any"
                    value={stopPrice}
                    onChange={(e) => setStopPrice(e.target.value)}
                    placeholder="0.00"
                    required
                    disabled={loading}
                    min="0.0001"
                  />
                </div>
              )}

              {/* Erreur */}
              {error && (
                <div className="place-order-error">
                  <Badge variant="danger">Erreur</Badge>
                  <p>{error}</p>
                </div>
              )}

              {/* Succès */}
              {success && orderResult && (
                <div className="place-order-success">
                  <Badge variant="success">Succès</Badge>
                  <p>Ordre placé avec succès !</p>
                  {orderResult.order && (
                    <div className="order-details">
                      <p><strong>ID Ordre:</strong> {orderResult.order.id}</p>
                      {orderResult.broker_result?.order_id && (
                        <p><strong>ID Broker:</strong> {orderResult.broker_result.order_id}</p>
                      )}
                      <p><strong>Statut:</strong> {orderResult.order.status}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Actions */}
              <div className="place-order-actions">
                <Button
                  type="submit"
                  variant="primary"
                  fullWidth
                  disabled={loading || loadingAccounts}
                >
                  {loading ? <Loading size="sm" /> : 'Placer l\'ordre'}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  fullWidth
                  onClick={handleClose}
                  disabled={loading}
                >
                  Annuler
                </Button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}

