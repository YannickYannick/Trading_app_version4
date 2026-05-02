/**
 * Modal IA : suggestions d'actions à vendre (analyse portefeuille).
 */
import { useEffect, useState, useCallback } from 'react'
import { Modal, Button, Badge, Loading } from '@components/common'
import aiService from '@services/aiService'
import type { AIAnalysis } from '@types/aiTypes'
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

  const reset = useCallback(() => {
    setLoading(false)
    setError(null)
    setAnalysis(null)
  }, [])

  const runSuggest = useCallback(async () => {
    setLoading(true)
    setError(null)
    setAnalysis(null)
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

  const suggestions: SellSuggestion[] = (() => {
    if (!analysis?.recommendations?.length) return []
    return analysis.recommendations as unknown as SellSuggestion[]
  })()

  const macroContext =
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

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Suggestions IA — actions à vendre"
      size="xl"
    >
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

            <div className="ai-sell-cards">
              {suggestions.map((s, idx) => (
                <article key={`${s.yahoo_symbol || s.symbol}-${idx}`} className="ai-sell-card">
                  <header className="ai-sell-card-head">
                    <div>
                      <strong className="ai-sell-ticker">
                        {s.yahoo_symbol || s.symbol || '—'}
                      </strong>
                      {s.name && <div className="ai-sell-name">{s.name}</div>}
                      {(s.sector || s.industry) && (
                        <div className="ai-sell-sector">
                          {[s.sector, s.industry].filter(Boolean).join(' · ')}
                        </div>
                      )}
                    </div>
                    <div className="ai-sell-badges">
                      {s.urgency && (
                        <Badge variant={getUrgencyVariant(s.urgency)}>
                          {getUrgencyLabel(s.urgency)}
                        </Badge>
                      )}
                      {typeof s.confidence === 'number' && (
                        <Badge variant="secondary">Confiance ~{Math.round(s.confidence)}%</Badge>
                      )}
                    </div>
                  </header>

                  {s.current_position && (
                    <div className="ai-sell-position">
                      <div className="position-row">
                        <span>Quantité:</span>
                        <strong>{s.current_position.quantity?.toFixed(2) || '—'}</strong>
                      </div>
                      <div className="position-row">
                        <span>Prix entrée:</span>
                        <strong>{s.current_position.entry_price?.toFixed(2) || '—'}</strong>
                      </div>
                      <div className="position-row">
                        <span>Prix actuel:</span>
                        <strong>{s.current_position.current_price?.toFixed(2) || '—'}</strong>
                      </div>
                      <div className={`position-row pnl ${(s.current_position.pnl_percent || 0) >= 0 ? 'positive' : 'negative'}`}>
                        <span>PnL:</span>
                        <strong>
                          {(s.current_position.pnl_percent || 0) >= 0 ? '+' : ''}
                          {s.current_position.pnl_percent?.toFixed(1) || '0'}%
                        </strong>
                      </div>
                    </div>
                  )}

                  <details className="ai-sell-details" open>
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
                          ? 'Cet actif n'est pas dans votre catalogue AllAssets'
                          : undefined
                      }
                      onClick={() => handlePickOrder(s)}
                    >
                      Passer un ordre de vente
                    </Button>
                  </div>
                </article>
              ))}
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
