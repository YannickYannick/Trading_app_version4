/**
 * Flux broker / comptes → secteurs (+ liquidités), type Sankey Flow.
 * Inspiré visuellement par https://github.com/YannickYannick/sankey-flow-studio (d3-sankey côté studio).
 */
import { useMemo } from 'react'
import { ResponsiveContainer, Sankey, Tooltip } from 'recharts'
import { Card } from '@components/common'
import type { Position } from '@types'
import {
  buildPortfolioBrokerSectorSankey,
  type BrokerBreakdownRow,
} from '@utils/portfolioSankeyFlow'
import { formatCurrency } from '@utils/format'
import './PortfolioSankeyFlow.css'

const STUDIO_URL = 'https://github.com/YannickYannick/sankey-flow-studio'

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
        Montants basés sur le <strong>cash par compte</strong> et la <strong>valorisation actuelle</strong>{' '}
        des lignes par courtier (pas l’historique des virements). Pour un graphe calibré sur les
        dépôts réels, une intégration des relevés (ex. transactions Saxo « Funding ») pourra
        compléter ce flux. Référence design :{' '}
        <a href={STUDIO_URL} target="_blank" rel="noopener noreferrer">
          sankey-flow-studio
        </a>
        .
      </p>
      <div className="portfolio-sankey-chart-wrap">
        <ResponsiveContainer width="100%" height={460}>
          <Sankey
            data={data}
            nodePadding={20}
            nodeWidth={14}
            linkCurvature={0.52}
            iterations={48}
            margin={{ top: 12, right: 140, bottom: 12, left: 32 }}
            sort
          >
            <Tooltip
              formatter={(value: number | string) => formatCurrency(Number(value))}
              contentStyle={{
                background: 'rgba(15, 23, 42, 0.92)',
                border: 'none',
                borderRadius: 6,
                fontSize: 12,
              }}
              labelStyle={{ color: '#e2e8f0' }}
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
