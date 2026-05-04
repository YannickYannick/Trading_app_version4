/**
 * Flux broker → secteurs (+ liquidités) avec d3-sankey (courbes, couleurs, survol type studio).
 * @see https://github.com/YannickYannick/sankey-flow-studio
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { sankey, sankeyLinkHorizontal } from 'd3-sankey'
import { Card } from '@components/common'
import type { Position } from '@types'
import {
  buildPortfolioBrokerSectorSankey,
  type BrokerBreakdownRow,
  type SankeyNodeInput,
} from '@utils/portfolioSankeyFlow'
import { formatCurrency } from '@utils/format'
import './PortfolioSankeyFlow.css'

const STUDIO_URL = 'https://github.com/YannickYannick/sankey-flow-studio'

const MARGIN = { top: 28, right: 12, bottom: 36, left: 12 }

type LayoutNode = SankeyNodeInput & {
  index?: number
  x0?: number
  x1?: number
  y0?: number
  y1?: number
  value?: number
}

type LayoutLink = {
  index: number
  source: LayoutNode
  target: LayoutNode
  value: number
  width?: number
  y0?: number
  y1?: number
}

function brokerColor(paletteIndex: number | undefined): string {
  const i = paletteIndex ?? 0
  const h = (198 + i * 53) % 360
  return `hsl(${h} 72% 56%)`
}

function sectorColor(name: string): string {
  if (name.startsWith('Liquidités')) return 'hsl(43 96% 58%)'
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0
  return `hsl(${h % 360} 62% 52%)`
}

function nodeFill(n: LayoutNode): string {
  if (n.role === 'broker') return brokerColor(n.brokerPaletteIndex)
  if (n.role === 'liquid') return sectorColor(n.name)
  return sectorColor(n.name)
}

function linkStroke(link: LayoutLink): string {
  const t = link.target
  if (t.role === 'liquid') return 'hsl(43 90% 52%)'
  return sectorColor(t.name)
}

export function PortfolioSankeyFlow({
  breakdown,
  positions,
  title = 'Flux portefeuille (comptes → secteurs)',
}: {
  breakdown: BrokerBreakdownRow[]
  positions: Position[]
  title?: string
}) {
  const data = useMemo(
    () => buildPortfolioBrokerSectorSankey(breakdown, positions),
    [breakdown, positions]
  )

  const wrapRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ width: 900, height: 480 })

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const ro = new ResizeObserver(() => {
      const w = Math.max(480, el.clientWidth)
      setSize({ width: w, height: Math.min(560, Math.max(420, Math.round(w * 0.48))) })
    })
    ro.observe(el)
    const w = Math.max(480, el.clientWidth)
    setSize({ width: w, height: Math.min(560, Math.max(420, Math.round(w * 0.48))) })
    return () => ro.disconnect()
  }, [])

  const [hoverLink, setHoverLink] = useState<number | null>(null)
  const [hoverNode, setHoverNode] = useState<number | null>(null)

  const graph = useMemo(() => {
    if (!data) return null
    const { width, height } = size
    const innerW = width - MARGIN.left - MARGIN.right
    const innerH = height - MARGIN.top - MARGIN.bottom

    const layout = sankey<LayoutNode, { source: number; target: number; value: number }>()
      .nodeWidth(20)
      .nodePadding(14)
      .iterations(32)
      .extent([
        [MARGIN.left, MARGIN.top],
        [MARGIN.left + innerW, MARGIN.top + innerH],
      ])

    const nodes = data.nodes.map((n) => ({ ...n }))
    const links = data.links.map((l) => ({ ...l }))
    return layout({ nodes, links }) as { nodes: LayoutNode[]; links: LayoutLink[] }
  }, [data, size])

  const linkPath = useMemo(() => sankeyLinkHorizontal(), [])

  if (!data || data.nodes.length < 2) {
    return (
      <Card title={title} className="portfolio-sankey-card">
        <p className="portfolio-sankey-empty">
          Pas assez de données pour tracer un flux (positions ouvertes liées à un courtier et
          synthèse par compte requises).
        </p>
      </Card>
    )
  }

  if (!graph) return null

  const { width, height } = size
  const dimmed = hoverLink !== null || hoverNode !== null

  const linkHighlighted = (link: LayoutLink, linkIndex: number) => {
    if (hoverLink === linkIndex) return true
    if (
      hoverNode != null &&
      (link.source.index === hoverNode || link.target.index === hoverNode)
    ) {
      return true
    }
    return false
  }

  const nodeHighlighted = (nodeIndex: number) => {
    if (hoverNode === nodeIndex) return true
    if (hoverLink != null) {
      const l = graph.links[hoverLink]
      if (l && (l.source.index === nodeIndex || l.target.index === nodeIndex)) return true
    }
    return false
  }

  return (
    <Card title={title} className="portfolio-sankey-card">
      <p className="portfolio-sankey-note">
        Montants basés sur le <strong>cash par compte</strong> et la <strong>valorisation actuelle</strong>{' '}
        des lignes par courtier (pas l’historique des virements). Référence courbes et interaction :{' '}
        <a href={STUDIO_URL} target="_blank" rel="noopener noreferrer">
          sankey-flow-studio
        </a>
        .
      </p>
      <div ref={wrapRef} className="portfolio-sankey-chart-wrap">
        <svg
          className="portfolio-sankey-svg"
          width={width}
          height={height}
          role="img"
          aria-label="Diagramme de flux portefeuille"
        >
          <defs>
            <filter id="portfolio-sankey-glow" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          <g className="portfolio-sankey-main">
            <g className="portfolio-sankey-nodes-rects">
              {graph.nodes.map((n, i) => {
                const x0 = n.x0 ?? 0
                const x1 = n.x1 ?? 0
                const y0 = n.y0 ?? 0
                const y1 = n.y1 ?? 0
                const w = Math.max(x1 - x0, 1)
                const h = Math.max(y1 - y0, 1)
                const hi = nodeHighlighted(i)
                return (
                  <rect
                    key={`nr-${i}`}
                    x={x0}
                    y={y0}
                    width={w}
                    height={h}
                    rx={3}
                    fill={nodeFill(n)}
                    stroke="rgba(255,255,255,0.22)"
                    strokeWidth={1}
                    opacity={dimmed ? (hi ? 1 : 0.22) : 1}
                    style={{ cursor: 'pointer', transition: 'opacity 160ms ease' }}
                    onMouseEnter={() => setHoverNode(i)}
                    onMouseLeave={() => setHoverNode(null)}
                  />
                )
              })}
            </g>
            <g className="portfolio-sankey-links-layer">
              {graph.links.map((link, i) => {
                const d = linkPath(link as Parameters<typeof linkPath>[0])
                if (!d) return null
                const hi = linkHighlighted(link, i)
                const strokeW = Math.max(3, Math.min((link.width ?? 3) * 1.15, 28))
                return (
                  <path
                    key={`l-${i}`}
                    className="portfolio-sankey-link"
                    d={d}
                    fill="none"
                    stroke={linkStroke(link)}
                    strokeWidth={strokeW}
                    strokeLinecap="round"
                    strokeOpacity={dimmed ? (hi ? 0.95 : 0.07) : 0.5}
                    filter={hi && dimmed ? 'url(#portfolio-sankey-glow)' : undefined}
                    onMouseEnter={() => setHoverLink(i)}
                    onMouseLeave={() => setHoverLink(null)}
                    style={{ cursor: 'pointer', transition: 'stroke-opacity 160ms ease' }}
                  >
                    <title>
                      {link.source.name} → {link.target.name} : {formatCurrency(link.value)}
                    </title>
                  </path>
                )
              })}
            </g>
            <g className="portfolio-sankey-labels-layer" pointerEvents="none">
              {graph.nodes.map((n, i) => {
                const x0 = n.x0 ?? 0
                const x1 = n.x1 ?? 0
                const y0 = n.y0 ?? 0
                const y1 = n.y1 ?? 0
                const hi = nodeHighlighted(i)
                const isLeft = (x0 + x1) / 2 < width / 2
                const labelX = isLeft ? x1 + 10 : x0 - 10
                const textAnchor = isLeft ? 'start' : 'end'
                const labelY = (y0 + y1) / 2
                const val = n.value ?? 0
                return (
                  <g key={`nl-${i}`}>
                    <text
                      x={labelX}
                      y={labelY - 6}
                      textAnchor={textAnchor}
                      className="portfolio-sankey-label-name"
                      opacity={dimmed ? (hi ? 1 : 0.28) : 0.95}
                    >
                      {n.name.length > 22 ? `${n.name.slice(0, 20)}…` : n.name}
                    </text>
                    <text
                      x={labelX}
                      y={labelY + 10}
                      textAnchor={textAnchor}
                      className="portfolio-sankey-label-value"
                      opacity={dimmed ? (hi ? 1 : 0.32) : 1}
                    >
                      {formatCurrency(val)}
                    </text>
                  </g>
                )
              })}
            </g>
          </g>
        </svg>
      </div>
      <div className="portfolio-sankey-legend">
        <span className="portfolio-sankey-legend-left">Entrées : comptes / courtiers</span>
        <span className="portfolio-sankey-legend-right">Sorties : secteurs & liquidités</span>
      </div>
    </Card>
  )
}
