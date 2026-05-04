/**
 * Layout Sankey 2 colonnes (courtiers → secteurs) aligné en haut, rubans cubiques.
 * Inspiré du prototype « Apple revenue » / Test sankey.zip (chemins fermés + dégradés).
 */
import type { SankeyChartData } from './portfolioSankeyFlow'

export interface ModernSankeyPadding {
  top: number
  right: number
  bottom: number
  left: number
}

export interface ModernSankeyLayoutOpts {
  width: number
  height: number
  padding: ModernSankeyPadding
  nodeW: number
  nodePad: number
}

export interface ModernLayoutNode {
  index: number
  col: 0 | 1
  x: number
  y0: number
  y1: number
  h: number
}

export interface ModernLayoutLink {
  index: number
  source: number
  target: number
  value: number
  path: string
  sy0: number
  sy1: number
  ty0: number
  ty1: number
}

const DEFAULT_OPTS: ModernSankeyLayoutOpts = {
  width: 1600,
  height: 720,
  padding: { top: 32, right: 200, bottom: 28, left: 72 },
  nodeW: 12,
  nodePad: 16,
}

/** Premier index d’un nœud non-courtier = début colonne droite. */
function brokerTargetSplit(nodes: SankeyNodeInput[]): number {
  const i = nodes.findIndex(n => n.role !== 'broker')
  return i === -1 ? nodes.length : i
}

export function computePortfolioModernLayout(
  data: SankeyChartData,
  opts: Partial<ModernSankeyLayoutOpts> = {}
): {
  layoutByIndex: ModernLayoutNode[]
  links: ModernLayoutLink[]
  opts: ModernSankeyLayoutOpts
} {
  const o = { ...DEFAULT_OPTS, ...opts, padding: { ...DEFAULT_OPTS.padding, ...opts.padding } }
  const { width, height, padding, nodeW, nodePad } = o
  const innerW = width - padding.left - padding.right
  const innerH = height - padding.top - padding.bottom
  const nodes = data.nodes
  const split = brokerTargetSplit(nodes)

  const col0Indices = nodes.slice(0, split).map((_, i) => i)
  const col1Indices = nodes.slice(split).map((_, j) => j + split)

  const colX = (col: 0 | 1) => padding.left + (innerW * col) / 1

  const colTotals = [
    col0Indices.reduce((s, i) => s + Math.max(0, nodes[i].value), 0),
    col1Indices.reduce((s, i) => s + Math.max(0, nodes[i].value), 0),
  ]
  const padTotals = [
    Math.max(0, col0Indices.length - 1) * nodePad,
    Math.max(0, col1Indices.length - 1) * nodePad,
  ]

  let scale = Infinity
  for (let c = 0; c < 2; c++) {
    const total = colTotals[c]
    if (total <= 0) continue
    const avail = innerH - padTotals[c]
    scale = Math.min(scale, avail / total)
  }
  if (!Number.isFinite(scale) || scale <= 0) scale = 1

  const layoutByIndex: ModernLayoutNode[] = new Array(nodes.length)

  const placeColumn = (indices: number[], col: 0 | 1) => {
    const x = colX(col)
    let y = padding.top
    for (const idx of indices) {
      const n = nodes[idx]
      const h = Math.max(2, n.value * scale)
      layoutByIndex[idx] = { index: idx, col, x, y0: y, y1: y + h, h }
      y += h + nodePad
    }
  }

  placeColumn(col0Indices, 0)
  placeColumn(col1Indices, 1)

  const outBySource: number[][] = new Array(nodes.length).fill(0).map(() => [])
  const inByTarget: number[][] = new Array(nodes.length).fill(0).map(() => [])
  data.links.forEach((l, i) => {
    outBySource[l.source].push(i)
    inByTarget[l.target].push(i)
  })
  for (let i = 0; i < nodes.length; i++) {
    outBySource[i].sort((a, b) => layoutByIndex[data.links[a].target].y0 - layoutByIndex[data.links[b].target].y0)
    inByTarget[i].sort((a, b) => layoutByIndex[data.links[a].source].y0 - layoutByIndex[data.links[b].source].y0)
  }

  const linkGeoms: ModernLayoutLink[] = data.links.map((l, i) => {
    const s = layoutByIndex[l.source]
    const t = layoutByIndex[l.target]
    const sList = outBySource[l.source]
    const tList = inByTarget[l.target]
    const sIdx = sList.indexOf(i)
    const tIdx = tList.indexOf(i)
    const sOff = sList.slice(0, sIdx).reduce((acc, li) => acc + data.links[li].value * scale, 0)
    const tOff = tList.slice(0, tIdx).reduce((acc, li) => acc + data.links[li].value * scale, 0)
    const thickness = l.value * scale
    const x0 = s.x + nodeW
    const x1 = t.x
    const sy0 = s.y0 + sOff
    const sy1 = sy0 + thickness
    const ty0 = t.y0 + tOff
    const ty1 = ty0 + thickness
    const cx = (x0 + x1) / 2
    const path =
      `M ${x0} ${sy0} C ${cx} ${sy0}, ${cx} ${ty0}, ${x1} ${ty0} ` +
      `L ${x1} ${ty1} C ${cx} ${ty1}, ${cx} ${sy1}, ${x0} ${sy1} Z`
    return { index: i, source: l.source, target: l.target, value: l.value, path, sy0, sy1, ty0, ty1 }
  })

  return { layoutByIndex, links: linkGeoms, opts: o }
}
