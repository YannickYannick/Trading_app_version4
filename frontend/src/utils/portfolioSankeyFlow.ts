/**
 * Données Sankey : comptes / brokers (entrée) → secteurs + liquidités (sortie).
 * Montants = situation actuelle (cash broker + valorisation des positions), pas l’historique des virements.
 */
import type { Position } from '@types'

export interface BrokerBreakdownRow {
  broker_name: string
  broker_id?: number
  broker_account_id?: number
  cash?: number
  invested?: number
  total?: number
}

export type SankeyNodeRole = 'broker' | 'liquid' | 'sector'

export interface SankeyNodeInput {
  name: string
  value: number
  role: SankeyNodeRole
  /** Index du courtier pour palette (0..n-1) */
  brokerPaletteIndex?: number
}

export interface SankeyChartData {
  nodes: SankeyNodeInput[]
  links: { source: number; target: number; value: number }[]
}

const LIQUIDITES = 'Liquidités (cash)'
const EPS = 0.5

function positionMarketValueEUR(p: Position): number {
  const qty = Number(p.quantity ?? p.size ?? 0) || 0
  const px =
    Number(p.yahoo_current_price ?? p.current_price ?? p.entry_price ?? 0) || 0
  return Math.max(0, qty * px)
}

function sectorBucket(p: Position): string {
  const assetType = (p.all_asset_asset_type || '').toUpperCase()
  if (assetType.includes('CRYPTO') || (p.all_asset_platform || '').toUpperCase() === 'BINANCE') {
    return 'Crypto'
  }
  const s = (p.all_asset_sector || '').trim()
  return s || 'Sans secteur'
}

export function buildPortfolioBrokerSectorSankey(
  breakdown: BrokerBreakdownRow[],
  positions: Position[]
): SankeyChartData | null {
  const cashByBroker = new Map<number, number>()
  const labelsByBroker = new Map<number, string>()

  for (const row of breakdown) {
    const id = row.broker_id
    if (id == null || Number.isNaN(Number(id))) continue
    const cash = Number(row.cash ?? 0) || 0
    cashByBroker.set(id, (cashByBroker.get(id) || 0) + cash)
    const label = (row.broker_name || '').trim() || `Courtier #${id}`
    if (!labelsByBroker.has(id)) labelsByBroker.set(id, label)
  }

  const investedByBrokerSector = new Map<string, number>()

  for (const p of positions) {
    if (p.status && p.status !== 'OPEN') continue
    const bid = p.broker_id
    if (bid == null || Number.isNaN(Number(bid))) continue
    const sector = sectorBucket(p)
    const key = `${bid}::${sector}`
    investedByBrokerSector.set(key, (investedByBrokerSector.get(key) || 0) + positionMarketValueEUR(p))
  }

  const brokerIds = new Set<number>()
  cashByBroker.forEach((_, id) => brokerIds.add(id))
  investedByBrokerSector.forEach((_, key) => brokerIds.add(Number(key.split('::')[0])))

  if (brokerIds.size === 0) return null

  const sectors = new Set<string>([LIQUIDITES])
  investedByBrokerSector.forEach((_, key) => {
    sectors.add(key.split('::')[1] || 'Sans secteur')
  })

  const sortedBrokers = [...brokerIds].sort((a, b) => a - b)
  const sortedSectors = [...sectors].filter(s => s !== LIQUIDITES).sort((a, b) => a.localeCompare(b, 'fr'))
  const targetOrder = [LIQUIDITES, ...sortedSectors]

  type BrokerAgg = { bid: number; cash: number; invested: number; label: string }
  const brokerAggs: BrokerAgg[] = []

  for (const bid of sortedBrokers) {
    const cash = cashByBroker.get(bid) || 0
    let inv = 0
    investedByBrokerSector.forEach((v, key) => {
      if (Number(key.split('::')[0]) === bid) inv += v
    })
    const total = cash + inv
    if (total < EPS) continue
    brokerAggs.push({
      bid,
      cash,
      invested: inv,
      label: labelsByBroker.get(bid) || `Courtier #${bid}`,
    })
  }

  if (brokerAggs.length === 0) return null

  const nodes: SankeyNodeInput[] = []
  const brokerNodeIndex = new Map<number, number>()

  brokerAggs.forEach((b, paletteIdx) => {
    brokerNodeIndex.set(b.bid, nodes.length)
    nodes.push({
      name: b.label,
      value: b.cash + b.invested,
      role: 'broker',
      brokerPaletteIndex: paletteIdx,
    })
  })

  const sectorNodeIndex = new Map<string, number>()
  for (const sec of targetOrder) {
    sectorNodeIndex.set(sec, nodes.length)
    nodes.push({
      name: sec,
      value: 0,
      role: sec === LIQUIDITES ? 'liquid' : 'sector',
    })
  }

  const links: { source: number; target: number; value: number }[] = []

  for (const b of brokerAggs) {
    const src = brokerNodeIndex.get(b.bid)
    if (src === undefined) continue
    if (b.cash >= EPS) {
      const tgt = sectorNodeIndex.get(LIQUIDITES)
      if (tgt !== undefined) links.push({ source: src, target: tgt, value: b.cash })
    }
    investedByBrokerSector.forEach((val, key) => {
      const [bidStr, sec] = key.split('::')
      if (Number(bidStr) !== b.bid || val < EPS) return
      const tgt = sectorNodeIndex.get(sec)
      if (tgt !== undefined) links.push({ source: src, target: tgt, value: val })
    })
  }

  for (const sec of targetOrder) {
    const idx = sectorNodeIndex.get(sec)
    if (idx === undefined) continue
    const sumIn = links.filter(l => l.target === idx).reduce((s, l) => s + l.value, 0)
    nodes[idx].value = sumIn
  }

  if (links.length === 0) return null

  return { nodes, links }
}
