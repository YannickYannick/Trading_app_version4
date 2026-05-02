/**
 * Modal IA : suggestions d'actions à vendre (analyse portefeuille).
 */
import { useEffect, useState, useCallback, useMemo } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { Modal, Button, Badge, Loading } from '@components/common'
import aiService from '@services/aiService'
import { tradeService } from '@services'
import { assetService } from '@services/assets'
import type { AIAnalysis } from '@types/aiTypes'
import type { Trade } from '@types'
import AISuggestionMiniChart from './AISuggestionMiniChart'
import './AISuggestionShared.css'
import './AISellModal.css'

interface SellSuggestion {
  symbol?: string
  yahoo_symbol?: string
  name?: string
  sector?: string
  industry?: string
  current_position?: {
    quantity?: number
    entry_price?: number
    current_price?: number
    pnl_percent?: number
  }
  fundamentals?: {
    per?: number | null
    valuation?: string
    profitability?: string
  }
  weakness_analysis?: string
  sector_outlook?: string
  macro_and_geopolitical?: string
  sell_rationale?: string
  alternative_use_of_capital?: string
  urgency?: 'HIGH' | 'MEDIUM' | 'LOW'
  confidence?: number
  all_asset_id?: number | null
  tradable?: boolean
  broker_symbol?: string | null
}

function isWrappedResponse(
  data: unknown
): data is { message: string; analysis: AIAnalysis } {
  return (
    typeof data === 'object' &&
    data !== null &&
    'analysis' in data &&
    typeof (data as { analysis: unknown }).analysis === 'object'
  )
}

function unwrapAnalysis(data: AIAnalysis | { message: string; analysis: AIAnalysis }): AIAnalysis {
  if (isWrappedResponse(data)) {
    return data.analysis
  }
  return data as AIAnalysis
}

function tradeMatchesAllAsset(t: Trade, allAssetId: number): boolean {
  const aid =
    (t as { all_asset_id?: number }).all_asset_id ??
    (typeof t.all_asset === 'object' && t.all_asset ? t.all_asset.id : null) ??
    (typeof t.all_asset === 'number' ? t.all_asset : null) ??
    (typeof t.asset === 'object' && t.asset ? t.asset.id : null)
  return aid === allAssetId
}

export interface SellOrderPayload {
  allAssetId: number | null
  symbol: string
  side: 'SELL'
}

interface AISellModalProps {
  isOpen: boolean
  onClose: () => void
  onPickOrder: (payload: SellOrderPayload) => void
}

export default function AISellModal({ isOpen, onClose, onPickOrder }: AISellModalProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<AIAnalysis | null>(null)
  const [expandedKey, setExpandedKey] = useState<string | null>(null)
  const [livePrices, setLivePrices] = useState<Record<number, number | null>>({})
  const [brokerTrades, setBrokerTrades] = useState<Trade[]>([])

  const reset = useCallback(() => {
    setLoading(false)
    setError(null)
    setAnalysis(null)
    setExpandedKey(null)
    setLivePrices({})
    setBrokerTrades([])
  }, [])

  const runSuggest = useCallback(async () => {
    setLoading(true)
    setError(null)
    setAnalysis(null)
    setExpandedKey(null)
    try {
      const raw = await aiService.suggestSell({ force_new: true })
      const a = unwrapAnalysis(raw as AIAnalysis | { message: string; analysis: AIAnalysis })
      setAnalysis(a)
      if (a.status === 'FAILED' && a.error_message) {
        setError(a.error_message)
      }
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { error?: string } } })?.response?.data?.error ||
        (e as Error)?.message ||
        'Impossible de contacter le service IA'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!isOpen) {
      reset()
      return
    }
    void runSuggest()
  }, [isOpen, reset, runSuggest])

  const suggestions: SellSuggestion[] = useMemo(() => {
    if (!analysis?.recommendations?.length) return []
    return analysis.recommendations as unknown as SellSuggestion[]
  }, [analysis?.recommendations])

  useEffect(() => {
    if (!isOpen || !suggestions.length) return
    let cancelled = false
    ;(async () => {
      try {
        const res = await tradeService.getAll({ page_size: 500 })
        const list = res.results || []
        if (!cancelled) setBrokerTrades(list)
      } catch {
        if (!cancelled) setBrokerTrades([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [isOpen, suggestions.length])

  useEffect(() => {
    if (!isOpen || !suggestions.length) return
    const ids = [...new Set(suggestions.map((s) => s.all_asset_id).filter((id): id is number => typeof id === 'number'))]
    if (ids.length === 0) return
    let cancelled = false
    ;(async () => {
      const entries = await Promise.all(
        ids.map(async (id) => [id, await assetService.getYahooCurrentPrice(id)] as const)
      )
      if (cancelled) return
      setLivePrices((prev) => {
        const next = { ...prev }
        for (const [id, price] of entries) next[id] = price
        return next
      })
    })()
    return () => {
      cancelled = true
    }
  }, [isOpen, suggestions])

    (analysis?.insights as { macro_context?: string } | undefined)?.macro_context || ''

  const handlePickOrder = (s: SellSuggestion) => {
    const symbol = (s.broker_symbol || s.yahoo_symbol || s.symbol || '').trim()
    onPickOrder({
      allAssetId: s.all_asset_id ?? null,
      symbol,
      side: 'SELL',
    })
  }

  const getUrgencyVariant = (urgency?: string): 'danger' | 'warning' | 'info' => {
    switch (urgency) {
      case 'HIGH':
        return 'danger'
      case 'MEDIUM':
        return 'warning'
      default:
        return 'info'
    }
  }

  const getUrgencyLabel = (urgency?: string): string => {
    switch (urgency) {
      case 'HIGH':
        return 'Urgent'
      case 'MEDIUM':
        return 'Modéré'
      default:
        return 'À considérer'
    }
  }

  const toggleRow = (key: string) => {
    setExpandedKey((k) => (k === key ? null : key))
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Suggestions IA — actions à vendre" size="xl">
      <div className="ai-sell-modal">
        <p className="ai-sell-disclaimer">
          Informations générées par IA à titre indicatif uniquement — pas un conseil en investissement
          personnalisé. Vérifiez les cours, frais et risques avant tout ordre de vente.
        </p>

        {loading && (
          <div className="ai-sell-loading">
            <Loading text="Analyse en cours, l'IA évalue vos positions..." />
          </div>
        )}

        {error && !loading && (
          <div className="ai-sell-error">
            <Badge variant="danger">Erreur</Badge>
            <span>{error}</span>
            <Button variant="outline" size="sm" onClick={() => void runSuggest()}>
              Réessayer
            </Button>
          </div>
        )}

        {!loading && analysis && analysis.status === 'COMPLETED' && (
          <>
            {analysis.summary && (
              <section className="ai-sell-summary">
                <h4>Résumé de l'analyse</h4>
                <p>{analysis.summary}</p>
              </section>
            )}
            {macroContext && (
              <section className="ai-sell-macro">
                <h4>Contexte macro & géopolitique</h4>
                <p>{macroContext}</p>
              </section>
            )}

            <div className="ai-suggest-vertical-list">
              {suggestions.map((s, idx) => {
                const rowKey = `${s.yahoo_symbol || s.symbol || 'row'}-${idx}`
                const expanded = expandedKey === rowKey
                const aid = s.all_asset_id ?? null
                const entry = s.current_position?.entry_price
                const live =
                  aid != null && livePrices[aid] !== undefined ? livePrices[aid] : null
                const qty = s.current_position?.quantity
                let pnlPct: number | null = null
                if (live != null && entry != null && entry > 0) {
                  pnlPct = ((live - entry) / entry) * 100
                } else if (s.current_position?.pnl_percent != null) {
                  pnlPct = s.current_position.pnl_percent
                }
                const rowTrades =
                  aid != null ? brokerTrades.filter((t) => tradeMatchesAllAsset(t, aid)) : []

                return (
                  <div key={rowKey} className={`ai-suggest-row ${expanded ? 'expanded' : ''}`}>
                    <button
                      type="button"
                      className="ai-suggest-row-head"
                      onClick={() => toggleRow(rowKey)}
                      aria-expanded={expanded}
                    >
                      <span className="ai-suggest-row-chevron">
                        {expanded ? (
                          <ChevronDown size={20} />
                        ) : (
                          <ChevronRight size={20} />
                        )}
                      </span>
                      <div className="ai-suggest-row-title">
                        <strong className="ai-suggest-ticker">
                          {s.yahoo_symbol || s.symbol || '—'}
                        </strong>
                        {s.name && <span className="ai-suggest-sub">{s.name}</span>}
                        {(s.sector || s.industry) && (
                          <span className="ai-suggest-sector">
                            {[s.sector, s.industry].filter(Boolean).join(' · ')}
                          </span>
                        )}
                      </div>
                      <div className="ai-suggest-row-metrics">
                        {live != null && (
                          <span className="ai-suggest-live">
                            Prix Yahoo&nbsp;: <strong>{live.toFixed(2)}</strong>
                          </span>
                        )}
                        {live == null && aid != null && (
                          <span className="ai-suggest-live muted">Prix Yahoo…</span>
                        )}
                        {pnlPct != null && (
                          <span
                            className={`ai-suggest-pnl ${pnlPct >= 0 ? 'pos' : 'neg'}`}
                          >
                            PnL&nbsp;: {pnlPct >= 0 ? '+' : ''}
                            {pnlPct.toFixed(1)}%
                          </span>
                        )}
                        {qty != null && (
                          <span className="ai-suggest-qty">Qté {Number(qty).toFixed(2)}</span>
                        )}
                      </div>
                      <div className="ai-suggest-row-badges">
                        {s.urgency && (
                          <Badge variant={getUrgencyVariant(s.urgency)}>
                            {getUrgencyLabel(s.urgency)}
                          </Badge>
                        )}
                        {typeof s.confidence === 'number' && (
                          <Badge variant="secondary">~{Math.round(s.confidence)}%</Badge>
                        )}
                      </div>
                    </button>

                    {expanded && (
                      <div className="ai-suggest-row-body">
                        {aid != null ? (
                          <AISuggestionMiniChart
                            allAssetId={aid}
                            trades={rowTrades}
                            showTradeMarkers
                            entryPrice={entry ?? null}
                          />
                        ) : (
                          <p className="ai-suggest-no-chart">
                            Actif non lié au catalogue — graphique et prix en direct indisponibles.
                          </p>
                        )}

                        <details className="ai-sell-details">
                          <summary>Analyse des faiblesses</summary>
                          <p className="ai-sell-body">{s.weakness_analysis || '—'}</p>
                        </details>

                        <details className="ai-sell-details">
                          <summary>Fondamentaux (PER, valorisation, rentabilité)</summary>
                          <div className="ai-sell-body">
                            {s.fundamentals ? (
                              <ul>
                                <li>
                                  <strong>PER :</strong>{' '}
                                  {s.fundamentals.per === null || s.fundamentals.per === undefined
                                    ? 'N/A'
                                    : String(s.fundamentals.per)}
                                </li>
                                {s.fundamentals.valuation && (
                                  <li>
                                    <strong>Valorisation :</strong> {s.fundamentals.valuation}
                                  </li>
                                )}
                                {s.fundamentals.profitability && (
                                  <li>
                                    <strong>Rentabilité :</strong> {s.fundamentals.profitability}
                                  </li>
                                )}
                              </ul>
                            ) : (
                              <p>—</p>
                            )}
                          </div>
                        </details>

                        <details className="ai-sell-details">
                          <summary>Perspectives du secteur</summary>
                          <p className="ai-sell-body">{s.sector_outlook || '—'}</p>
                        </details>

                        <details className="ai-sell-details">
                          <summary>Contexte macro/géopolitique</summary>
                          <p className="ai-sell-body">{s.macro_and_geopolitical || '—'}</p>
                        </details>

                        <details className="ai-sell-details">
                          <summary>Argumentaire de vente</summary>
                          <p className="ai-sell-body">{s.sell_rationale || '—'}</p>
                        </details>

                        <details className="ai-sell-details">
                          <summary>Utilisation alternative du capital</summary>
                          <p className="ai-sell-body">{s.alternative_use_of_capital || '—'}</p>
                        </details>

                        <div className="ai-sell-actions">
                          <Button
                            variant="danger"
                            size="sm"
                            disabled={!s.tradable || !(s.broker_symbol || s.yahoo_symbol || s.symbol)}
                            title={
                              !s.tradable
                                ? "Cet actif n'est pas dans votre catalogue AllAssets"
                                : undefined
                            }
                            onClick={() => handlePickOrder(s)}
                          >
                            Passer un ordre de vente
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {suggestions.length === 0 && (
              <div className="ai-sell-empty">
                <Badge variant="success">Portefeuille sain</Badge>
                <p>Aucune suggestion de vente — votre portefeuille semble bien positionné.</p>
              </div>
            )}
          </>
        )}

        <div className="ai-sell-footer">
          <Button variant="outline" onClick={onClose}>
            Fermer
          </Button>
        </div>
      </div>
    </Modal>
  )
}
