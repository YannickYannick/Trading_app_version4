import type { Position } from '@types'

export type PortfolioCategory =
  | `Actions:${string}`
  | `ETF:${string}`
  | `Commodity:${string}`
  | `Crypto:${string}`
  | 'Cash'
  | 'FX'
  | 'Other'

const OVERRIDES_KEY = 'portfolio_category_overrides_v1'

export type CategoryOverrides = Record<string, PortfolioCategory>

export function loadCategoryOverrides(): CategoryOverrides {
  try {
    const raw = localStorage.getItem(OVERRIDES_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== 'object') return {}
    return parsed as CategoryOverrides
  } catch {
    return {}
  }
}

export function saveCategoryOverrides(overrides: CategoryOverrides) {
  localStorage.setItem(OVERRIDES_KEY, JSON.stringify(overrides))
}

export function getPositionValueEURish(p: Position): number {
  // On reste “monnaie de référence” côté UI (déjà le cas ailleurs).
  const qty = Number((p as any).quantity ?? (p as any).size ?? 0) || 0
  const px =
    Number((p as any).yahoo_current_price ?? p.current_price ?? p.entry_price ?? 0) || 0
  return qty * px
}

function norm(s: string): string {
  return (s || '').toLowerCase()
}

function containsAny(haystack: string, needles: string[]) {
  const h = norm(haystack)
  return needles.some((n) => h.includes(norm(n)))
}

function isStablecoinSymbol(sym: string): boolean {
  const s = sym.toUpperCase().replace(/[^A-Z0-9]/g, '')
  return (
    s === 'USDT' ||
    s === 'USDC' ||
    s === 'DAI' ||
    s === 'BUSD' ||
    s === 'TUSD' ||
    s === 'USDP' ||
    s === 'FDUSD'
  )
}

export function categorizePosition(
  p: Position,
  overrides: CategoryOverrides
): PortfolioCategory {
  const symbol = (p.all_asset_symbol || p.all_asset?.symbol || (p as any).symbol || '').trim()
  const override = overrides[symbol]
  if (override) return override

  const platform = (p as any).all_asset_platform || p.all_asset?.platform || ''
  const assetType = (p as any).all_asset_asset_type || p.all_asset?.asset_type || ''
  const name = (p.all_asset_name || p.all_asset?.name || '').trim()
  const sector = (p as any).all_asset_sector || p.all_asset?.sector || ''

  // Binance → Crypto (avec stablecoins séparés)
  if (String(platform).toUpperCase() === 'BINANCE') {
    if (isStablecoinSymbol(symbol)) return 'Crypto:Stablecoin'
    return 'Crypto:Other'
  }

  // Si Yahoo sector existe → Actions:{sector}
  if (sector && String(sector).trim().length > 0) {
    return `Actions:${String(sector).trim()}`
  }

  // Détecter ETF/ETC/ETN via name / asset_type
  const etfHints = ['etf', 'ucits', 'etc', 'etn', 'index', 'tracker']
  const equityHints = ['s&p', 'sp 500', 'nasdaq', 'msci', 'ftse', 'stoxx', 'cac', 'dax']
  const bondHints = ['bond', 'treasury', 'gov', 'government', 'corporate', 't-bill', 'fixed income']
  const worldHints = ['world', 'all-world', 'all world', 'global']
  const europeHints = ['europe', 'euro', 'eurostoxx', 'stoxx', 'cac']
  const goldHints = ['gold', 'or', 'xau']
  const oilHints = ['oil', 'brent', 'wti']

  const etfLike = containsAny(assetType, ['etf', 'etc', 'etn']) || containsAny(name, etfHints)
  if (etfLike) {
    if (containsAny(name, goldHints)) return 'Commodity:Gold'
    if (containsAny(name, oilHints)) return 'Commodity:Oil'
    if (containsAny(name, bondHints)) return 'ETF:Bond'
    if (containsAny(name, worldHints)) return 'ETF:Equity_World'
    if (containsAny(name, europeHints)) return 'ETF:Equity_Europe'
    if (containsAny(name, equityHints)) return 'ETF:Equity'
    return 'ETF:Other'
  }

  // FX / cash-like (ex: EURUSD=X ou symbol EUR/USD)
  if (containsAny(assetType, ['fx', 'fxspot']) || containsAny(symbol, ['=x']) || symbol.includes('/')) {
    return 'FX'
  }

  // Currency “cash” (ex: EUR / USD) -> Cash
  if (/^[A-Z]{3}$/.test(symbol.toUpperCase())) {
    return 'Cash'
  }

  return 'Other'
}

export interface CategorySlice {
  name: PortfolioCategory
  value: number
}

export function buildCategoryBreakdown(
  positions: Position[],
  totalCash: number,
  overrides: CategoryOverrides
): CategorySlice[] {
  const map = new Map<PortfolioCategory, number>()
  for (const p of positions) {
    const cat = categorizePosition(p, overrides)
    const val = getPositionValueEURish(p)
    map.set(cat, (map.get(cat) ?? 0) + val)
  }
  if (totalCash && totalCash > 0) {
    map.set('Cash', (map.get('Cash') ?? 0) + totalCash)
  }

  return Array.from(map.entries())
    .map(([name, value]) => ({ name, value }))
    .filter((x) => x.value > 0)
    .sort((a, b) => b.value - a.value)
}

