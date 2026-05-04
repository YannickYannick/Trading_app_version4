/**
 * Sankey portefeuille : SVG custom (rubans cubiques + dégradés), style proche du prototype
 * « Apple revenue » fourni (Test sankey.zip).
 */
import { useCallback, useId, useMemo, useState } from 'react'
import { Card } from '@components/common'
import type { Position } from '@types'
import {
  buildPortfolioBrokerSectorSankey,
  type BrokerBreakdownRow,
  type SankeyChartData,
  type SankeyNodeInput,
} from '@utils/portfolioSankeyFlow'
import { computePortfolioModernLayout } from '@utils/portfolioSankeyModernLayout'
import { formatCurrency } from '@utils/format'
import './PortfolioSankeyFlow.css'

const STUDIO_URL = 'https://github.com/YannickYannick/sankey-flow-studio'

type Hover =
  | { kind: 'node'; index: number }
  | { kind: 'link'; index: number }
  | null

function brokerStrokeFill(paletteIndex: number | undefined): { stroke: string; fill: string } {
  const i = paletteIndex ?? 0
  const h = (198 + i * 53) % 360
  return { stroke: `hsl(${h} 76% 58%)`, fill: `hsl(${h} 76% 34%)` }
}

function sectorStrokeFill(n: SankeyNodeInput): { stroke: string; fill: string } {
  if (n.role === 'liquid' || n.name.startsWith('Liquidités')) {
    return { stroke: 'hsl(46 100% 62%)', fill: 'hsl(46 88% 40%)' }
  }
  let hue = 0
  for (let i = 0; i < n.name.length; i++) hue = (hue * 31 + n.name.charCodeAt(i)) >>> 0
  const h = hue % 360
  return { stroke: `hsl(${h} 68% 56%)`, fill: `hsl(${h} 68% 36%)` }
}

function nodeStrokeFill(n: SankeyNodeInput): { stroke: string; fill: string } {
  if (n.role === 'broker') return brokerStrokeFill(n.brokerPaletteIndex)
  return sectorStrokeFill(n)
}

function relatedFromNode(data: SankeyChartData, hoverIndex: number): { nodes: Set<number>; links: Set<number> } {
  const LINKS = data.links
  const visited = new Set<number>([hoverIndex])
  const linkIds = new Set<number>()

  const queueUp = [hoverIndex]
  while (queueUp.length) {
    const cur = queueUp.shift()!
    LINKS.forEach((l, i) => {
      if (l.target === cur) {
        linkIds.add(i)
        if (!visited.has(l.source)) {
          visited.add(l.source)
          queueUp.push(l.source)
        }
      }
    })
  }

  const queueDown = [hoverIndex]
  while (queueDown.length) {
    const cur = queueDown.shift()!
    LINKS.forEach((l, i) => {
      if (l.source === cur) {
        linkIds.add(i)
        if (!visited.has(l.target)) {
          visited.add(l.target)
          queueDown.push(l.target)
        }
      }
    })
  }

  return { nodes: visited, links: linkIds }
}

function buildHoverRelated(data: SankeyChartData, hover: Hover): { nodes: Set<number>; links: Set<number> } | null {
  if (!hover) return null
  if (hover.kind === 'link') {
    const l = data.links[hover.index]
    const a = relatedFromNode(data, l.source)
    const b = relatedFromNode(data, l.target)
    const nodes = new Set<number>([...a.nodes, ...b.nodes])
    const links = new Set<number>([...a.links, ...b.links])
    return { nodes, links }
  }
  return relatedFromNode(data, hover.index)
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

  const layout = useMemo(() => (data ? computePortfolioModernLayout(data) : null), [data])
  const uid = useId().replace(/:/g, '')
  const [hover, setHover] = useState<Hover>(null)

  const related = useMemo(() => (data && hover ? buildHoverRelated(data, hover) : null), [data, hover])

  const { width: vbW, height: vbH } = layout?.opts ?? { width: 1600, height: 720 }

  const onLeave = useCallback(() => setHover(null), [])

  if (!data || data.nodes.length < 2 || !layout) {
    return (
      <Card title={title} className="portfolio-sankey-card">
        <p className="portfolio-sankey-empty">
          Pas assez de données pour tracer un flux (positions ouvertes liées à un courtier et
          synthèse par compte requises).
        </p>
      </Card>
    )
  }

  const { layoutByIndex, links: linkGeoms, opts } = layout
  const { nodeW } = opts

  return (
    <Card title={title} className="portfolio-sankey-card">
      <p className="portfolio-sankey-note">
        Diagramme type <strong>rubans</strong> (dégradés, fusion douce), calqué sur le prototype
        « revenue waterfall ». Variante Recharts / studio :{' '}
        <a href={STUDIO_URL} target="_blank" rel="noopener noreferrer">
          sankey-flow-studio
        </a>
        .
      </p>
      <div className="portfolio-sankey-chart-wrap portfolio-sankey-modern-wrap">
        <svg
          className="portfolio-sankey-modern-svg"
          viewBox={`0 0 ${vbW} ${vbH}`}
          width="100%"
          height="100%"
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label={title}
          onMouseLeave={onLeave}
        >
          <defs>
            {linkGeoms.map(l => {
              const s = data.nodes[l.source]
              const t = data.nodes[l.target]
              const c0 = nodeStrokeFill(s).fill
              const c1 = nodeStrokeFill(t).fill
              const sx = layoutByIndex[l.source].x + nodeW
              const tx = layoutByIndex[l.target].x
              return (
                <linearGradient
                  key={l.index}
                  id={`${uid}-grad-${l.index}`}
                  gradientUnits="userSpaceOnUse"
                  x1={sx}
                  x2={tx}
                  y1={0}
                  y2={0}
                >
                  <stop offset="0%" stopColor={c0} stopOpacity={0.88} />
                  <stop offset="100%" stopColor={c1} stopOpacity={0.88} />
                </linearGradient>
              )
            })}
          </defs>

          <g className="portfolio-sankey-ribbons">
            {linkGeoms.map(l => {
              const dim = related && !related.links.has(l.index)
              return (
                <path
                  key={l.index}
                  d={l.path}
                  fill={`url(#${uid}-grad-${l.index})`}
                  className="portfolio-sankey-ribbon-path"
                  opacity={dim ? 0.12 : 0.78}
                  data-active={!dim ? '1' : '0'}
                  onMouseEnter={() => setHover({ kind: 'link', index: l.index })}
                >
                  <title>
                    {data.nodes[l.source].name} → {data.nodes[l.target].name} :{' '}
                    {formatCurrency(l.value)}
                  </title>
                </path>
              )
            })}
          </g>

          <g className="portfolio-sankey-nodes">
            {data.nodes.map((n, i) => {
              const geom = layoutByIndex[i]
              if (!geom) return null
              const c = nodeStrokeFill(n)
              const dim = related && !related.nodes.has(i)
              const val = Number(n.value ?? 0)
              const labelX = geom.x + nodeW + 12
              const midY = (geom.y0 + geom.y1) / 2
              const labelTopY = Math.min(geom.y0 + 22, midY)
              const nameShort = n.name.length > 26 ? `${n.name.slice(0, 24)}…` : n.name

              return (
                <g
                  key={i}
                  className="portfolio-sankey-node-g"
                  opacity={dim ? 0.35 : 1}
                  data-active={!dim ? '1' : '0'}
                  onMouseEnter={() => setHover({ kind: 'node', index: i })}
                >
                  <rect
                    x={geom.x}
                    y={geom.y0}
                    width={nodeW}
                    height={Math.max(2, geom.h)}
                    fill={c.stroke}
                    rx={2}
                  />
                  <text
                    x={labelX}
                    y={labelTopY}
                    className="portfolio-sankey-modern-label-name"
                    textAnchor="start"
                  >
                    {nameShort}
                  </text>
                  <text
                    x={labelX}
                    y={labelTopY + 18}
                    className="portfolio-sankey-modern-label-value"
                    textAnchor="start"
                  >
                    {formatCurrency(val)}
                  </text>
                  <title>
                    {n.name} — {formatCurrency(val)}
                  </title>
                </g>
              )
            })}
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
