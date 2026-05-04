/**
 * Sankey Recharts (forme d’origine) + couleurs, montants visibles, surbrillance au survol.
 * @see https://github.com/YannickYannick/sankey-flow-studio pour une variante d3 plus « studio ».
 */
import { useCallback, useMemo, useState } from 'react'
import { ResponsiveContainer, Sankey, Tooltip } from 'recharts'
import type { LinkProps, NodeProps } from 'recharts/types/chart/Sankey'
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

type Hover =
  | { kind: 'node'; node: SankeyNodeInput & { depth?: number } }
  | { kind: 'link'; payload: LinkProps['payload'] }
  | null

function brokerColor(paletteIndex: number | undefined): string {
  const i = paletteIndex ?? 0
  const h = (198 + i * 53) % 360
  return `hsl(${h} 72% 52%)`
}

function sectorColor(name: string): string {
  if (name.startsWith('Liquidités')) return 'hsl(43 96% 55%)'
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0
  return `hsl(${h % 360} 62% 50%)`
}

function nodeFill(n: SankeyNodeInput): string {
  if (n.role === 'broker') return brokerColor(n.brokerPaletteIndex)
  if (n.role === 'liquid') return sectorColor(n.name)
  return sectorColor(n.name)
}

function linkStroke(payload: LinkProps['payload']): string {
  const t = payload.target as SankeyNodeInput & { depth?: number }
  if (t.role === 'liquid') return 'hsl(43 90% 50%)'
  return sectorColor(t.name)
}

function linkPathD(p: LinkProps): string {
  const {
    sourceX,
    sourceY,
    sourceControlX,
    targetX,
    targetY,
    targetControlX,
  } = p
  return `M${sourceX},${sourceY} C${sourceControlX},${sourceY} ${targetControlX},${targetY} ${targetX},${targetY}`
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

  const [hover, setHover] = useState<Hover>(null)

  const linkActive = useCallback(
    (payload: LinkProps['payload']) => {
      if (!hover) return true
      if (hover.kind === 'link') return hover.payload === payload
      return payload.source === hover.node || payload.target === hover.node
    },
    [hover]
  )

  const nodeActive = useCallback(
    (node: SankeyNodeInput & { depth?: number }) => {
      if (!hover) return true
      if (hover.kind === 'node') return hover.node === node
      return hover.payload.source === node || hover.payload.target === node
    },
    [hover]
  )

  const renderLink = useCallback(
    (props: LinkProps) => {
      const { payload, linkWidth, index } = props
      const active = linkActive(payload)
      const dim = hover !== null && !active
      return (
        <path
          className="portfolio-sankey-recharts-link"
          d={linkPathD(props)}
          fill="none"
          stroke={linkStroke(payload)}
          strokeWidth={Math.max(2, linkWidth)}
          strokeOpacity={dim ? 0.09 : 0.48}
          strokeLinecap="round"
          style={{ transition: 'stroke-opacity 140ms ease' }}
          data-link-index={index}
        />
      )
    },
    [hover, linkActive]
  )

  const renderNode = useCallback(
    (props: NodeProps) => {
      const { x, y, width, height, payload } = props
      const p = payload as SankeyNodeInput & { depth?: number }
      const active = nodeActive(p)
      const dim = hover !== null && !active
      const isLeft = p.depth === 0
      const lx = isLeft ? x + width + 8 : x - 8
      const anchor = isLeft ? 'start' : 'end'
      const cy = y + height / 2
      const val = Number(p.value ?? 0)

      return (
        <g className="portfolio-sankey-recharts-node" opacity={dim ? 0.22 : 1}>
          <rect
            x={x}
            y={y}
            width={width}
            height={height}
            rx={2}
            fill={nodeFill(p)}
            stroke="rgba(255,255,255,0.18)"
            strokeWidth={1}
          />
          <text
            x={lx}
            y={cy - 5}
            textAnchor={anchor}
            className="portfolio-sankey-recharts-label-name"
          >
            {p.name.length > 24 ? `${p.name.slice(0, 22)}…` : p.name}
          </text>
          <text
            x={lx}
            y={cy + 11}
            textAnchor={anchor}
            className="portfolio-sankey-recharts-label-value"
          >
            {formatCurrency(val)}
          </text>
        </g>
      )
    },
    [hover, nodeActive]
  )

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

  return (
    <Card title={title} className="portfolio-sankey-card">
      <p className="portfolio-sankey-note">
        Forme du graphe : <strong>Recharts</strong> (comme la première version). Couleurs, montants
        et surbrillance au survol sont conservés. Variante plus « rubans » :{' '}
        <a href={STUDIO_URL} target="_blank" rel="noopener noreferrer">
          sankey-flow-studio
        </a>
        .
      </p>
      <div className="portfolio-sankey-chart-wrap">
        <ResponsiveContainer width="100%" height={460}>
          <Sankey
            data={data}
            nodePadding={18}
            nodeWidth={12}
            linkCurvature={0.55}
            iterations={40}
            margin={{ top: 16, right: 120, bottom: 16, left: 28 }}
            sort
            node={renderNode}
            link={renderLink}
            onMouseEnter={(item, type) => {
              if (type === 'node') {
                const np = item as NodeProps
                setHover({ kind: 'node', node: np.payload as SankeyNodeInput & { depth?: number } })
              } else {
                const lp = item as LinkProps
                setHover({ kind: 'link', payload: lp.payload })
              }
            }}
            onMouseLeave={() => setHover(null)}
          >
            <Tooltip
              formatter={(value: number | string) => formatCurrency(Number(value))}
              contentStyle={{
                background: 'rgba(15, 23, 42, 0.95)',
                border: '1px solid rgba(148,163,184,0.25)',
                borderRadius: 8,
                fontSize: 12,
                color: '#f1f5f9',
              }}
            />
          </Sankey>
        </ResponsiveContainer>
      </div>
      <div className="portfolio-sankey-legend">
        <span className="portfolio-sankey-legend-left">Entrées : comptes / courtiers</span>
        <span className="portfolio-sankey-legend-right">Sorties : secteurs & liquidités</span>
      </div>
    </Card>
  )
}
