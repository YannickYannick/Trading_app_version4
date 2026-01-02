/**
 * Utilitaires pour calculer les performances et gains potentiels d'une stratégie
 */
import type { Signal } from './strategySignals'

export interface TradeSimulation {
  entryTime: string
  entryPrice: number
  exitTime: string | null
  exitPrice: number | null
  side: 'BUY' | 'SELL'
  quantity: number
  pnl: number | null
  pnlPercent: number | null
  status: 'OPEN' | 'CLOSED'
}

export interface StrategyPerformanceMetrics {
  totalTrades: number
  winningTrades: number
  losingTrades: number
  winRate: number
  totalPnL: number
  totalPnLPercent: number
  averageWin: number
  averageLoss: number
  maxDrawdown: number
  maxDrawdownPercent: number
  currentPosition: TradeSimulation | null
  openTrades: TradeSimulation[]
  closedTrades: TradeSimulation[]
}

/**
 * Simule les trades basés sur les signaux
 */
export function simulateTradesFromSignals(
  signals: Signal[],
  prices: number[],
  dates: string[],
  orderSize: number = 1.0,
  stopLoss?: number
): TradeSimulation[] {
  const trades: TradeSimulation[] = []
  let currentPosition: TradeSimulation | null = null

  // Créer un map pour accéder rapidement aux prix par date
  const priceMap = new Map<string, number>()
  dates.forEach((date, i) => {
    priceMap.set(date, prices[i])
  })

  for (let i = 0; i < signals.length; i++) {
    const signal = signals[i]
    const price = priceMap.get(signal.time) || signal.price

    // Si on a une position ouverte, vérifier le stop-loss
    if (currentPosition && currentPosition.status === 'OPEN') {
      if (stopLoss && stopLoss > 0) {
        const pnlPercent = currentPosition.side === 'BUY'
          ? ((price - currentPosition.entryPrice) / currentPosition.entryPrice) * 100
          : ((currentPosition.entryPrice - price) / currentPosition.entryPrice) * 100

        if (pnlPercent <= -stopLoss * 100) {
          // Stop-loss déclenché
          currentPosition.exitTime = signal.time
          currentPosition.exitPrice = price
          currentPosition.status = 'CLOSED'
          currentPosition.pnl = currentPosition.side === 'BUY'
            ? (price - currentPosition.entryPrice) * currentPosition.quantity
            : (currentPosition.entryPrice - price) * currentPosition.quantity
          currentPosition.pnlPercent = pnlPercent
          trades.push({ ...currentPosition })
          currentPosition = null
        }
      }
    }

    // Gérer les nouveaux signaux
    if (signal.signal === 'BUY' && (!currentPosition || currentPosition.side === 'SELL')) {
      // Fermer la position SELL si elle existe
      if (currentPosition && currentPosition.status === 'OPEN') {
        currentPosition.exitTime = signal.time
        currentPosition.exitPrice = price
        currentPosition.status = 'CLOSED'
        currentPosition.pnl = (currentPosition.entryPrice - price) * currentPosition.quantity
        currentPosition.pnlPercent = ((currentPosition.entryPrice - price) / currentPosition.entryPrice) * 100
        trades.push({ ...currentPosition })
        currentPosition = null
      }

      // Ouvrir une position BUY
      currentPosition = {
        entryTime: signal.time,
        entryPrice: price,
        exitTime: null,
        exitPrice: null,
        side: 'BUY',
        quantity: orderSize,
        pnl: null,
        pnlPercent: null,
        status: 'OPEN',
      }
    } else if (signal.signal === 'SELL' && (!currentPosition || currentPosition.side === 'BUY')) {
      // Fermer la position BUY si elle existe
      if (currentPosition && currentPosition.status === 'OPEN') {
        currentPosition.exitTime = signal.time
        currentPosition.exitPrice = price
        currentPosition.status = 'CLOSED'
        currentPosition.pnl = (price - currentPosition.entryPrice) * currentPosition.quantity
        currentPosition.pnlPercent = ((price - currentPosition.entryPrice) / currentPosition.entryPrice) * 100
        trades.push({ ...currentPosition })
        currentPosition = null
      }

      // Ouvrir une position SELL (short)
      currentPosition = {
        entryTime: signal.time,
        entryPrice: price,
        exitTime: null,
        exitPrice: null,
        side: 'SELL',
        quantity: orderSize,
        pnl: null,
        pnlPercent: null,
        status: 'OPEN',
      }
    }
  }

  // Ajouter la position ouverte finale si elle existe
  if (currentPosition && currentPosition.status === 'OPEN') {
    const lastPrice = prices[prices.length - 1]
    const lastDate = dates[dates.length - 1]
    currentPosition.exitTime = lastDate
    currentPosition.exitPrice = lastPrice
    currentPosition.status = 'CLOSED'
    currentPosition.pnl = currentPosition.side === 'BUY'
      ? (lastPrice - currentPosition.entryPrice) * currentPosition.quantity
      : (currentPosition.entryPrice - lastPrice) * currentPosition.quantity
    currentPosition.pnlPercent = currentPosition.side === 'BUY'
      ? ((lastPrice - currentPosition.entryPrice) / currentPosition.entryPrice) * 100
      : ((currentPosition.entryPrice - lastPrice) / currentPosition.entryPrice) * 100
    trades.push(currentPosition)
  }

  return trades
}

/**
 * Calcule les métriques de performance
 */
export function calculatePerformanceMetrics(
  trades: TradeSimulation[],
  initialCapital: number = 10000
): StrategyPerformanceMetrics {
  const closedTrades = trades.filter(t => t.status === 'CLOSED' && t.pnl !== null)
  const openTrades = trades.filter(t => t.status === 'OPEN')

  const winningTrades = closedTrades.filter(t => (t.pnl || 0) > 0)
  const losingTrades = closedTrades.filter(t => (t.pnl || 0) <= 0)

  const totalPnL = closedTrades.reduce((sum, t) => sum + (t.pnl || 0), 0)
  const totalPnLPercent = closedTrades.reduce((sum, t) => sum + (t.pnlPercent || 0), 0) / closedTrades.length || 0

  const averageWin = winningTrades.length > 0
    ? winningTrades.reduce((sum, t) => sum + (t.pnl || 0), 0) / winningTrades.length
    : 0

  const averageLoss = losingTrades.length > 0
    ? losingTrades.reduce((sum, t) => sum + (t.pnl || 0), 0) / losingTrades.length
    : 0

  // Calculer le drawdown
  let maxDrawdown = 0
  let maxDrawdownPercent = 0
  let peak = initialCapital

  let currentCapital = initialCapital
  for (const trade of closedTrades) {
    currentCapital += trade.pnl || 0
    if (currentCapital > peak) {
      peak = currentCapital
    }
    const drawdown = peak - currentCapital
    const drawdownPercent = (drawdown / peak) * 100
    if (drawdown > maxDrawdown) {
      maxDrawdown = drawdown
      maxDrawdownPercent = drawdownPercent
    }
  }

  return {
    totalTrades: closedTrades.length,
    winningTrades: winningTrades.length,
    losingTrades: losingTrades.length,
    winRate: closedTrades.length > 0 ? (winningTrades.length / closedTrades.length) * 100 : 0,
    totalPnL,
    totalPnLPercent,
    averageWin,
    averageLoss,
    maxDrawdown,
    maxDrawdownPercent,
    currentPosition: openTrades[openTrades.length - 1] || null,
    openTrades,
    closedTrades,
  }
}

