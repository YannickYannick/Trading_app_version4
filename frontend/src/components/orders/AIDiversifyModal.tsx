/**
 * Modal IA : 3 suggestions d'actions pour diversifier le portefeuille (Orders).
 */
import { useEffect, useState, useCallback, useMemo } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { Modal, Button, Badge, Loading } from '@components/common'
import aiService from '@services/aiService'
import { assetService } from '@services/assets'
import type { AIAnalysis, DiversifySuggestion } from '@types/aiTypes'
import AISuggestionMiniChart from './AISuggestionMiniChart'
import './AISuggestionShared.css'
import './AIDiversifyModal.css'

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

export interface OrderPrefillPayload {
  allAssetId: number | null
  symbol: string
  side: 'BUY' | 'SELL'
}

interface AIDiversifyModalProps {
  isOpen: boolean
  onClose: () => void
  /** Ouvre le PlaceOrderModal avec symbole / AllAsset pré-remplis */
  onPickOrder: (payload: OrderPrefillPayload) => void
}

export default function AIDiversifyModal({ isOpen, onClose, onPickOrder }: AIDiversifyModalProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<AIAnalysis | null>(null)
  const [expandedKey, setExpandedKey] = useState<string | null>(null)
  const [livePrices, setLivePrices] = useState<Record<number, number | null>>({})

  const reset = useCallback(() => {
    setLoading(false)
    setError(null)
    setAnalysis(null)
    setExpandedKey(null)
    setLivePrices({})
  }, [])

  const runSuggest = useCallback(async () => {
    setLoading(true)
    setError(null)
    setAnalysis(null)
    setExpandedKey(null)
    try {
      const raw = await aiService.suggestDiversification({ force_new: true })
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

  const suggestions: DiversifySuggestion[] = useMemo(() => {
    if (!analysis?.recommendations?.length) return []
    return analysis.recommendations as unknown as DiversifySuggestion[]
  }, [analysis?.recommendations])

  useEffect(() => {
    if (!isOpen || !suggestions.length) return
    const ids = [
      ...new Set(suggestions.map((s) => s.all_asset_id).filter((id): id is number => typeof id === 'number')),
    ]
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

  const macroContext =
    (analysis?.insights as { macro_context?: string } | undefined)?.macro_context || ''

  const handlePickOrder = (s: DiversifySuggestion) => {
    const symbol = (s.broker_symbol || s.yahoo_symbol || s.symbol || '').trim()
    onPickOrder({
      allAssetId: s.all_asset_id ?? null,
      symbol,
      side: 'BUY',
    })
  }

  const toggleRow = (key: string) => {
    setExpandedKey((k) => (k === key ? null : key))
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Suggestions IA — diversification (achats)" size="xl">
      <div className="ai-diversify-modal">
        <p className="ai-diversify-disclaimer">
          Informations générées par IA à titre indicatif uniquement — pas un conseil en investissement
          personnalisé. Vérifiez les cours, frais et risques avant tout ordre.
        </p>

        {loading && (
          <div className="ai-diversify-loading">
            <Loading text="Analyse en cours, l'IA scanne le marché et votre portefeuille…" />
          </div>
        )}

        {error && !loading && (
          <div className="ai-diversify-error">
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
              <section className="ai-diversify-summary">
                <h4>Résumé</h4>
                <p>{analysis.summary}</p>
              </section>
            )}
            {macroContext && (
              <section className="ai-diversify-macro">
                <h4>Contexte macro & géopolitique</h4>
                <p>{macroContext}</p>
              </section>
            )}

            <div className="ai-suggest-vertical-list">
              {suggestions.map((s, idx) => {
                const rowKey = `${s.yahoo_symbol || s.symbol || 'row'}-${idx}`
                const expanded = expandedKey === rowKey
                const aid = s.all_asset_id ?? null
                const live =
                  aid != null && livePrices[aid] !== undefined ? livePrices[aid] : null

                return (
                  <div key={rowKey} className={`ai-suggest-row ${expanded ? 'expanded' : ''}`}>
                    <button
                      type="button"
                      className="ai-suggest-row-head"
                      onClick={() => toggleRow(rowKey)}
                      aria-expanded={expanded}
                    >
                      <span className="ai-suggest-row-chevron">
                        {expanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                      </span>
                      <div className="ai-suggest-row-title">
                        <strong className="ai-suggest-ticker">{s.yahoo_symbol || s.symbol || '—'}</strong>
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
                      </div>
                      <div className="ai-suggest-row-badges">
                        {s.tradable ? (
                          <Badge variant="success">Catalogue</Badge>
                        ) : (
                          <Badge variant="secondary">Hors catalogue</Badge>
                        )}
                        {typeof s.confidence === 'number' && (
                          <Badge variant="info">~{Math.round(s.confidence)}%</Badge>
                        )}
                      </div>
                    </button>

                    {expanded && (
                      <div className="ai-suggest-row-body">
                        {aid != null ? (
                          <AISuggestionMiniChart allAssetId={aid} showTradeMarkers={false} />
                        ) : (
                          <p className="ai-suggest-no-chart">
                            Actif non lié au catalogue — graphique et prix en direct indisponibles.
                          </p>
                        )}

                        <details className="ai-diversify-details">
                          <summary>Fondamentaux (PER, valorisation, rentabilité)</summary>
                          <div className="ai-diversify-body">
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

                        <details className="ai-diversify-details">
                          <summary>Avantages compétitifs & barrières à l'entrée</summary>
                          <p className="ai-diversify-body">{s.moat || '—'}</p>
                        </details>

                        <details className="ai-diversify-details">
                          <summary>Contexte économique / politique (titre)</summary>
                          <p className="ai-diversify-body">{s.macro_and_geopolitical || '—'}</p>
                        </details>

                        <details className="ai-diversify-details">
                          <summary>Stratégie de l'entreprise</summary>
                          <p className="ai-diversify-body">{s.company_strategy || '—'}</p>
                        </details>

                        <details className="ai-diversify-details">
                          <summary>Horizon d'investissement suggéré</summary>
                          <p className="ai-diversify-body">{s.investment_horizon || '—'}</p>
                        </details>

                        <details className="ai-diversify-details">
                          <summary>Diversification vs votre portefeuille</summary>
                          <p className="ai-diversify-body">{s.diversification_reason || '—'}</p>
                        </details>

                        {s.risks && s.risks.length > 0 && (
                          <details className="ai-diversify-details">
                            <summary>Risques</summary>
                            <ul className="ai-diversify-body">
                              {s.risks.map((r, i) => (
                                <li key={i}>{r}</li>
                              ))}
                            </ul>
                          </details>
                        )}

                        <div className="ai-diversify-actions">
                          <Button
                            variant="primary"
                            size="sm"
                            disabled={!s.tradable || !(s.broker_symbol || s.yahoo_symbol || s.symbol)}
                            title={
                              !s.tradable
                                ? "Cet actif n'est pas dans votre catalogue AllAssets — recherche manuelle possible dans Passer un ordre"
                                : undefined
                            }
                            onClick={() => handlePickOrder(s)}
                          >
                            Passer un ordre (pré-rempli)
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {suggestions.length === 0 && (
              <p className="ai-diversify-empty">Aucune suggestion structurée reçue. Réessayez plus tard.</p>
            )}
          </>
        )}

        <div className="ai-diversify-footer">
          <Button variant="outline" onClick={onClose}>
            Fermer
          </Button>
        </div>
      </div>
    </Modal>
  )
}
