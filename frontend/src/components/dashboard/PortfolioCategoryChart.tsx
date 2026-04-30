import { useMemo, useState } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { Card, Button, Modal, Input, Badge } from '@components/common'
import type { Position } from '@types'
import {
  buildCategoryBreakdown,
  loadCategoryOverrides,
  saveCategoryOverrides,
  type CategoryOverrides,
  type PortfolioCategory,
} from '@utils/portfolioCategory'
import { formatCurrency } from '@utils/format'

const COLORS = [
  '#0088FE',
  '#00C49F',
  '#FFBB28',
  '#FF8042',
  '#8884d8',
  '#82ca9d',
  '#a4de6c',
  '#d0ed57',
  '#ffc658',
]

function uniqueSymbols(positions: Position[]): string[] {
  const s = new Set<string>()
  for (const p of positions) {
    const sym = (p.all_asset_symbol || p.all_asset?.symbol || (p as any).symbol || '').trim()
    if (sym) s.add(sym)
  }
  return Array.from(s).sort((a, b) => a.localeCompare(b))
}

const CATEGORY_OPTIONS: PortfolioCategory[] = [
  'Cash',
  'FX',
  'Crypto:Stablecoin',
  'Crypto:Other',
  'ETF:Equity',
  'ETF:Equity_World',
  'ETF:Equity_Europe',
  'ETF:Bond',
  'ETF:Other',
  'Commodity:Gold',
  'Commodity:Oil',
  'Other',
]

export function PortfolioCategoryChart({
  positions,
  totalCash,
}: {
  positions: Position[]
  totalCash: number
}) {
  const [isOverrideOpen, setIsOverrideOpen] = useState(false)
  const [overrides, setOverrides] = useState<CategoryOverrides>(() => loadCategoryOverrides())
  const [filter, setFilter] = useState('')

  const data = useMemo(
    () => buildCategoryBreakdown(positions, totalCash, overrides),
    [positions, totalCash, overrides]
  )

  const symbols = useMemo(() => uniqueSymbols(positions), [positions])
  const filteredSymbols = useMemo(() => {
    const f = filter.trim().toLowerCase()
    if (!f) return symbols
    return symbols.filter((s) => s.toLowerCase().includes(f))
  }, [symbols, filter])

  const total = data.reduce((acc, x) => acc + x.value, 0)

  return (
    <Card className="h-full">
      <div style={{ padding: '20px', minHeight: '420px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
          <div>
            <h3 style={{ marginBottom: '6px', fontSize: '1.1rem', fontWeight: 600 }}>
              Allocation par catégories (heuristiques + overrides)
            </h3>
            <div style={{ fontSize: '0.85rem', color: '#999' }}>
              Total: {formatCurrency(total)}
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={() => setIsOverrideOpen(true)}>
            Overrides
          </Button>
        </div>

        <div style={{ width: '100%', height: 320, marginTop: 16 }}>
          <ResponsiveContainer>
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={110}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {data.map((_entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
                formatter={(value: number) => [`${value.toFixed(2)} €`, '']}
              />
              <Legend verticalAlign="bottom" height={36} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <Modal
        isOpen={isOverrideOpen}
        onClose={() => setIsOverrideOpen(false)}
        title="Overrides manuels (prioritaires)"
        size="lg"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <p style={{ margin: 0, fontSize: '0.9rem', color: '#999' }}>
            Les overrides sont stockés dans ton navigateur (localStorage). Ils remplacent les heuristiques auto.
          </p>

          <Input
            label="Filtrer (symbole)"
            value={filter}
            onChange={(e) => setFilter((e.target as HTMLInputElement).value)}
            placeholder="Ex: VUSA, VWCE, GOLD…"
          />

          <div style={{ maxHeight: 360, overflow: 'auto', border: '1px solid #333', borderRadius: 8 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ textAlign: 'left' }}>
                  <th style={{ padding: '10px 12px', borderBottom: '1px solid #333' }}>Symbole</th>
                  <th style={{ padding: '10px 12px', borderBottom: '1px solid #333' }}>Override</th>
                  <th style={{ padding: '10px 12px', borderBottom: '1px solid #333' }} />
                </tr>
              </thead>
              <tbody>
                {filteredSymbols.map((sym) => {
                  const current = overrides[sym]
                  return (
                    <tr key={sym}>
                      <td style={{ padding: '8px 12px', borderBottom: '1px solid #222' }}>
                        <strong>{sym}</strong>
                      </td>
                      <td style={{ padding: '8px 12px', borderBottom: '1px solid #222' }}>
                        <select
                          value={current || ''}
                          onChange={(e) => {
                            const val = (e.target.value || '') as PortfolioCategory | ''
                            const next = { ...overrides }
                            if (!val) {
                              delete next[sym]
                            } else {
                              next[sym] = val
                            }
                            setOverrides(next)
                            saveCategoryOverrides(next)
                          }}
                          style={{
                            width: '100%',
                            background: '#111',
                            color: '#fff',
                            border: '1px solid #333',
                            borderRadius: 6,
                            padding: '6px 8px',
                          }}
                        >
                          <option value="">(auto)</option>
                          {CATEGORY_OPTIONS.map((c) => (
                            <option key={c} value={c}>
                              {c}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td style={{ padding: '8px 12px', borderBottom: '1px solid #222', textAlign: 'right' }}>
                        {current ? <Badge variant="info">manuel</Badge> : <Badge variant="secondary">auto</Badge>}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <Button variant="outline" onClick={() => setIsOverrideOpen(false)}>
              Fermer
            </Button>
          </div>
        </div>
      </Modal>
    </Card>
  )
}

