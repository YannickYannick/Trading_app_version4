/**
 * Modal IA : lance achats + ventes en parallèle, avec onglets.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { Badge, Button, Loading, Modal } from '@components/common'
import aiService from '@services/aiService'
import { assetService } from '@services/assets'
import type { AIAnalysis, DiversifySuggestion } from '@types/aiTypes'
import AISuggestionMiniChart from './AISuggestionMiniChart'
import './AISuggestionShared.css'
import './AIDiversifyModal.css'
import './AISellModal.css'

function isWrappedResponse(data: unknown): data is { message: string; analysis: AIAnalysis } {
  return (
    typeof data === 'object' &&
    data !== null &&
    'analysis' in data &&
    typeof (data as { analysis: unknown }).analysis === 'object'
  )
}

function unwrapAnalysis(data: AIAnalysis | { message: string; analysis: AIAnalysis }): AIAnalysis {
  if (isWrappedResponse(data)) return data.analysis
  return data as AIAnalysis
}

type Tab = 'BUY' | 'SELL'

export interface BothOrderPayload {
  allAssetId: number | null
  symbol: string
  side: 'BUY' | 'SELL'
}

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
  sell_rationale?: string
  urgency?: 'HIGH' | 'MEDIUM' | 'LOW'
  confidence?: number
  all_asset_id?: number | null
  tradable?: boolean
  broker_symbol?: string | null
}

function urgencyVariant(urgency?: string): 'danger' | 'warning' | 'info' {
  switch (urgency) {
    case 'HIGH':
      return 'danger'
    case 'MEDIUM':
      return 'warning'
    default:
      return 'info'
  }
}

function urgencyLabel(urgency?: string): string {
  switch (urgency) {
    case 'HIGH':
      return 'Urgent'
    case 'MEDIUM':
      return 'À surveiller'
    default:
      return 'Optionnel'
  }
}

export default function AIBothModal({
  isOpen,
  onClose,
  onPickOrder,
}: {
  isOpen: boolean
  onClose: () => void
  onPickOrder: (payload: BothOrderPayload) => void
}) {
  const [tab, setTab] = useState<Tab>('BUY')

  const [buyLoading, setBuyLoading] = useState(false)
  const [buyError, setBuyError] = useState<string | null>(null)
  const [buyAnalysis, setBuyAnalysis] = useState<AIAnalysis | null>(null)
  const [buyExpanded, setBuyExpanded] = useState<string | null>(null)
  const [buyLivePrices, setBuyLivePrices] = useState<Record<number, number | null>>({})

  const [sellLoading, setSellLoading] = useState(false)
  const [sellError, setSellError] = useState<string | null>(null)
  const [sellAnalysis, setSellAnalysis] = useState<AIAnalysis | null>(null)
  const [sellExpanded, setSellExpanded] = useState<string | null>(null)
  const [sellLivePrices, setSellLivePrices] = useState<Record<number, number | null>>({})

  const reset = useCallback(() => {
    setTab('BUY')
    setBuyLoading(false)
    setBuyError(null)
    setBuyAnalysis(null)
    setBuyExpanded(null)
    setBuyLivePrices({})
    setSellLoading(false)
    setSellError(null)
    setSellAnalysis(null)
    setSellExpanded(null)
    setSellLivePrices({})
  }, [])

  const runBoth = useCallback(async () => {
    setBuyLoading(true)
    setSellLoading(true)
    setBuyError(null)
    setSellError(null)
    setBuyAnalysis(null)
    setSellAnalysis(null)
    setBuyExpanded(null)
    setSellExpanded(null)
    try {
      const [buyRes, sellRes] = await Promise.allSettled([
        aiService.suggestDiversification({ force_new: true }),
        aiService.suggestSell({ force_new: true }),
      ])

      if (buyRes.status === 'fulfilled') {
        const a = unwrapAnalysis(buyRes.value as AIAnalysis | { message: string; analysis: AIAnalysis })
        setBuyAnalysis(a)
        if (a.status === 'FAILED' && a.error_message) setBuyError(a.error_message)
      } else {
        const msg =
          (buyRes.reason as { response?: { data?: { error?: string } } })?.response?.data?.error ||
          (buyRes.reason as Error)?.message ||
          'Impossible de contacter le service IA (achats)'
        setBuyError(msg)
      }

      if (sellRes.status === 'fulfilled') {
        const a = unwrapAnalysis(sellRes.value as AIAnalysis | { message: string; analysis: AIAnalysis })
        setSellAnalysis(a)
        if (a.status === 'FAILED' && a.error_message) setSellError(a.error_message)
      } else {
        const msg =
          (sellRes.reason as { response?: { data?: { error?: string } } })?.response?.data?.error ||
          (sellRes.reason as Error)?.message ||
          'Impossible de contacter le service IA (ventes)'
        setSellError(msg)
      }
    } finally {
      setBuyLoading(false)
      setSellLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!isOpen) {
      reset()
      return
    }
    void runBoth()
  }, [isOpen, reset, runBoth])

  const buySuggestions: DiversifySuggestion[] = useMemo(() => {
    if (!buyAnalysis?.recommendations?.length) return []
    return buyAnalysis.recommendations as unknown as DiversifySuggestion[]
  }, [buyAnalysis?.recommendations])

  const sellSuggestions: SellSuggestion[] = useMemo(() => {
    if (!sellAnalysis?.recommendations?.length) return []
    return sellAnalysis.recommendations as unknown as SellSuggestion[]
  }, [sellAnalysis?.recommendations])

  useEffect(() => {
    if (!isOpen || !buySuggestions.length) return
    const ids = [...new Set(buySuggestions.map(s => s.all_asset_id).filter((id): id is number => typeof id === 'number'))]
    if (!ids.length) return
    let cancelled = false
    ;(async () => {
      const entries = await Promise.all(ids.map(async id => [id, await assetService.getYahooCurrentPrice(id)] as const))
      if (cancelled) return
      setBuyLivePrices(prev => {
        const next = { ...prev }
        for (const [id, price] of entries) next[id] = price
        return next
      })
    })()
    return () => {
      cancelled = true
    }
  }, [isOpen, buySuggestions])

  useEffect(() => {
    if (!isOpen || !sellSuggestions.length) return
    const ids = [...new Set(sellSuggestions.map(s => s.all_asset_id).filter((id): id is number => typeof id === 'number'))]
    if (!ids.length) return
    let cancelled = false
    ;(async () => {
      const entries = await Promise.all(ids.map(async id => [id, await assetService.getYahooCurrentPrice(id)] as const))
      if (cancelled) return
      setSellLivePrices(prev => {
        const next = { ...prev }
        for (const [id, price] of entries) next[id] = price
        return next
      })
    })()
    return () => {
      cancelled = true
    }
  }, [isOpen, sellSuggestions])

  const pickBuy = (s: DiversifySuggestion) => {
    const symbol = (s.broker_symbol || s.yahoo_symbol || s.symbol || '').trim()
    onPickOrder({ allAssetId: s.all_asset_id ?? null, symbol, side: 'BUY' })
  }

  const pickSell = (s: SellSuggestion) => {
    const symbol = (s.broker_symbol || s.yahoo_symbol || s.symbol || '').trim()
    onPickOrder({ allAssetId: s.all_asset_id ?? null, symbol, side: 'SELL' })
  }

  const macroBuy = (buyAnalysis?.insights as { macro_context?: string } | undefined)?.macro_context || ''
  const macroSell = (sellAnalysis?.insights as { macro_context?: string } | undefined)?.macro_context || ''

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Suggestions IA — achats + ventes" size="xl">
      <div className="ai-diversify-modal">
        <p className="ai-diversify-disclaimer">
          Informations générées par IA à titre indicatif uniquement — pas un conseil en investissement
          personnalisé. Vérifiez les cours, frais et risques avant tout ordre.
        </p>

        <div style={{ display: 'flex', gap: 10, marginBottom: 12, flexWrap: 'wrap' }}>
          <Button
            variant={tab === 'BUY' ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setTab('BUY')}
            title="Voir les suggestions d'achat"
          >
            Achats
          </Button>
          <Button
            variant={tab === 'SELL' ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setTab('SELL')}
            title="Voir les suggestions de vente"
          >
            Ventes
          </Button>
          <div style={{ marginLeft: 'auto' }}>
            <Button variant="outline" size="sm" onClick={() => void runBoth()}>
              Relancer
            </Button>
          </div>
        </div>

        {tab === 'BUY' && (
          <>
            {buyLoading && (
              <div className="ai-diversify-loading">
                <Loading text="Analyse achats en cours…" />
              </div>
            )}
            {buyError && !buyLoading && (
              <div className="ai-diversify-error">
                <Badge variant="danger">Erreur</Badge>
                <span>{buyError}</span>
              </div>
            )}

            {!buyLoading && buyAnalysis && buyAnalysis.status === 'COMPLETED' && (
              <>
                {buyAnalysis.summary && (
                  <section className="ai-diversify-summary">
                    <h4>Résumé</h4>
                    <p>{buyAnalysis.summary}</p>
                  </section>
                )}
                {macroBuy && (
                  <section className="ai-diversify-macro">
                    <h4>Contexte macro & géopolitique</h4>
                    <p>{macroBuy}</p>
                  </section>
                )}

                <div className="ai-suggest-vertical-list">
                  {buySuggestions.map((s, idx) => {
                    const rowKey = `${s.yahoo_symbol || s.symbol || 'row'}-${idx}`
                    const expanded = buyExpanded === rowKey
                    const aid = s.all_asset_id ?? null
                    const live = aid != null && buyLivePrices[aid] !== undefined ? buyLivePrices[aid] : null
                    const titleSym = (s.yahoo_symbol || s.symbol || '—').trim()
                    return (
                      <div key={rowKey} className={`ai-suggest-row ${expanded ? 'expanded' : ''}`}>
                        <button
                          type="button"
                          className="ai-suggest-row-head"
                          onClick={() => setBuyExpanded(k => (k === rowKey ? null : rowKey))}
                          aria-expanded={expanded}
                        >
                          <span className="ai-suggest-row-chevron">
                            {expanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                          </span>
                          <div className="ai-suggest-row-title">
                            <strong className="ai-suggest-ticker">{titleSym}</strong>
                            {s.name && <span className="ai-suggest-sub">{s.name}</span>}
                            {(s.sector || s.industry) && (
                              <span className="ai-suggest-sector">
                                {[s.sector, s.industry].filter(Boolean).join(' · ')}
                              </span>
                            )}
                          </div>
                          <div className="ai-suggest-row-right">
                            <div className="ai-suggest-live">
                              <span className="ai-suggest-live-lbl">Cours</span>
                              <span className="ai-suggest-live-val">
                                {live != null ? `${live}` : '—'}
                              </span>
                            </div>
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={(e) => {
                                e.preventDefault()
                                e.stopPropagation()
                                pickBuy(s)
                              }}
                            >
                              Pré-remplir achat
                            </Button>
                          </div>
                        </button>

                        {expanded && (
                          <div className="ai-suggest-row-body">
                            <div className="ai-suggest-grid">
                              <div className="ai-suggest-card">
                                <h5>Pourquoi maintenant</h5>
                                <p>{s.rationale || s.thesis || '—'}</p>
                              </div>
                              <div className="ai-suggest-card">
                                <h5>Mini-chart</h5>
                                <AISuggestionMiniChart allAssetId={aid ?? undefined} />
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </>
            )}
          </>
        )}

        {tab === 'SELL' && (
          <>
            {sellLoading && (
              <div className="ai-diversify-loading">
                <Loading text="Analyse ventes en cours…" />
              </div>
            )}
            {sellError && !sellLoading && (
              <div className="ai-diversify-error">
                <Badge variant="danger">Erreur</Badge>
                <span>{sellError}</span>
              </div>
            )}

            {!sellLoading && sellAnalysis && sellAnalysis.status === 'COMPLETED' && (
              <>
                {sellAnalysis.summary && (
                  <section className="ai-diversify-summary">
                    <h4>Résumé</h4>
                    <p>{sellAnalysis.summary}</p>
                  </section>
                )}
                {macroSell && (
                  <section className="ai-diversify-macro">
                    <h4>Contexte macro & géopolitique</h4>
                    <p>{macroSell}</p>
                  </section>
                )}

                <div className="ai-suggest-vertical-list">
                  {sellSuggestions.map((s, idx) => {
                    const rowKey = `${s.yahoo_symbol || s.symbol || 'row'}-${idx}`
                    const expanded = sellExpanded === rowKey
                    const aid = s.all_asset_id ?? null
                    const live = aid != null && sellLivePrices[aid] !== undefined ? sellLivePrices[aid] : null
                    const titleSym = (s.yahoo_symbol || s.symbol || '—').trim()
                    return (
                      <div key={rowKey} className={`ai-suggest-row ${expanded ? 'expanded' : ''}`}>
                        <button
                          type="button"
                          className="ai-suggest-row-head"
                          onClick={() => setSellExpanded(k => (k === rowKey ? null : rowKey))}
                          aria-expanded={expanded}
                        >
                          <span className="ai-suggest-row-chevron">
                            {expanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                          </span>
                          <div className="ai-suggest-row-title">
                            <strong className="ai-suggest-ticker">{titleSym}</strong>
                            {s.name && <span className="ai-suggest-sub">{s.name}</span>}
                            {(s.sector || s.industry) && (
                              <span className="ai-suggest-sector">
                                {[s.sector, s.industry].filter(Boolean).join(' · ')}
                              </span>
                            )}
                            {s.urgency && (
                              <span style={{ marginLeft: 8 }}>
                                <Badge variant={urgencyVariant(s.urgency)}>{urgencyLabel(s.urgency)}</Badge>
                              </span>
                            )}
                          </div>
                          <div className="ai-suggest-row-right">
                            <div className="ai-suggest-live">
                              <span className="ai-suggest-live-lbl">Cours</span>
                              <span className="ai-suggest-live-val">{live != null ? `${live}` : '—'}</span>
                            </div>
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={(e) => {
                                e.preventDefault()
                                e.stopPropagation()
                                pickSell(s)
                              }}
                            >
                              Pré-remplir vente
                            </Button>
                          </div>
                        </button>

                        {expanded && (
                          <div className="ai-suggest-row-body">
                            <div className="ai-suggest-grid">
                              <div className="ai-suggest-card">
                                <h5>Raison</h5>
                                <p>{s.sell_rationale || '—'}</p>
                              </div>
                              <div className="ai-suggest-card">
                                <h5>Mini-chart</h5>
                                <AISuggestionMiniChart allAssetId={aid ?? undefined} />
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </Modal>
  )
}

