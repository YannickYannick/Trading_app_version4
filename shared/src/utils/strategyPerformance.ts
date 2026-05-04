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
 * Simule les trades basés sur les signaux.
 * Les signaux BUY successifs sur un long ouvert augmentent la position (prix de revient moyen),
 * jusqu'au plafond portfolioMaxHeld si défini.
 */
export function simulateTradesFromSignals(
    signals: Signal[],
    prices: number[],
    dates: string[],
    orderSize: number = 1.0,
    stopLoss?: number,
    minQuantity: number = 0,
    maxQuantity?: number,
    budget?: number,
    portfolioMinHeld: number = 0,
    portfolioMaxHeld?: number
): TradeSimulation[] {
    const trades: TradeSimulation[] = []
    let currentPosition: TradeSimulation | null = null
    let hasHadPosition = false
    const allowShortSelling = minQuantity < 0

    const priceMap = new Map<string, number>()
    dates.forEach((date, i) => {
        priceMap.set(date, prices[i])
    })

    for (let i = 0; i < signals.length; i++) {
        const signal = signals[i]
        const price = priceMap.get(signal.time) || signal.price

        if (currentPosition && currentPosition.status === 'OPEN') {
            if (stopLoss && stopLoss > 0) {
                const pnlPercent = currentPosition.side === 'BUY'
                    ? ((price - currentPosition.entryPrice) / currentPosition.entryPrice) * 100
                    : ((currentPosition.entryPrice - price) / currentPosition.entryPrice) * 100

                if (pnlPercent <= -stopLoss * 100) {
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

        if (signal.signal === 'BUY') {
            if (currentPosition && currentPosition.status === 'OPEN' && currentPosition.side === 'SELL') {
                currentPosition.exitTime = signal.time
                currentPosition.exitPrice = price
                currentPosition.status = 'CLOSED'
                currentPosition.pnl = (currentPosition.entryPrice - price) * currentPosition.quantity
                currentPosition.pnlPercent = ((currentPosition.entryPrice - price) / currentPosition.entryPrice) * 100
                trades.push({ ...currentPosition })
                currentPosition = null
            }

            const longHeld =
                currentPosition?.side === 'BUY' && currentPosition.status === 'OPEN'
                    ? currentPosition.quantity
                    : 0

            let buyQuantity = Math.max(orderSize, minQuantity)
            if (maxQuantity && buyQuantity > maxQuantity) {
                buyQuantity = maxQuantity
            }
            if (portfolioMaxHeld != null && Number.isFinite(portfolioMaxHeld)) {
                const room = portfolioMaxHeld - longHeld
                buyQuantity = Math.min(buyQuantity, Math.max(0, room))
            }
            if (budget && budget > 0) {
                const maxQuantityFromBudget = budget / price
                if (maxQuantityFromBudget < buyQuantity) {
                    buyQuantity = Math.max(minQuantity, maxQuantityFromBudget)
                }
            }
            if (buyQuantity <= 0) {
                continue
            }

            if (longHeld > 0 && currentPosition && currentPosition.side === 'BUY') {
                const oldQ = currentPosition.quantity
                const oldP = currentPosition.entryPrice
                const addQ = buyQuantity
                const newQ = oldQ + addQ
                currentPosition.quantity = newQ
                currentPosition.entryPrice = (oldP * oldQ + price * addQ) / newQ
                hasHadPosition = true
            } else {
                currentPosition = {
                    entryTime: signal.time,
                    entryPrice: price,
                    exitTime: null,
                    exitPrice: null,
                    side: 'BUY',
                    quantity: buyQuantity,
                    pnl: null,
                    pnlPercent: null,
                    status: 'OPEN',
                }
                hasHadPosition = true
            }
        } else if (signal.signal === 'SELL' && (!currentPosition || currentPosition.side === 'BUY')) {
            const canOpenShort = hasHadPosition || allowShortSelling

            if (currentPosition && currentPosition.status === 'OPEN' && currentPosition.side === 'BUY') {
                const Q = currentPosition.quantity
                const minH = Math.max(0, portfolioMinHeld || 0)
                let sellQty = Math.max(orderSize, Math.abs(minQuantity))
                if (maxQuantity && sellQty > maxQuantity) {
                    sellQty = maxQuantity
                }
                const maxSellable = Math.max(0, Q - minH)
                sellQty = Math.min(sellQty, maxSellable)
                if (sellQty <= 0) {
                    continue
                }
                if (sellQty >= Q) {
                    currentPosition.exitTime = signal.time
                    currentPosition.exitPrice = price
                    currentPosition.status = 'CLOSED'
                    currentPosition.pnl = (price - currentPosition.entryPrice) * currentPosition.quantity
                    currentPosition.pnlPercent = ((price - currentPosition.entryPrice) / currentPosition.entryPrice) * 100
                    trades.push({ ...currentPosition })
                    currentPosition = null
                } else {
                    const closed: TradeSimulation = {
                        entryTime: currentPosition.entryTime,
                        entryPrice: currentPosition.entryPrice,
                        exitTime: signal.time,
                        exitPrice: price,
                        side: 'BUY',
                        quantity: sellQty,
                        pnl: (price - currentPosition.entryPrice) * sellQty,
                        pnlPercent: ((price - currentPosition.entryPrice) / currentPosition.entryPrice) * 100,
                        status: 'CLOSED',
                    }
                    trades.push(closed)
                    currentPosition.quantity = Q - sellQty
                }
                hasHadPosition = true
            }

            if (canOpenShort && !currentPosition) {
                let sellQuantity = Math.max(orderSize, Math.abs(minQuantity))
                if (maxQuantity && sellQuantity > maxQuantity) {
                    sellQuantity = maxQuantity
                }
                if (budget && budget > 0) {
                    const maxQuantityFromBudget = budget / price
                    if (maxQuantityFromBudget < sellQuantity) {
                        sellQuantity = Math.max(Math.abs(minQuantity), maxQuantityFromBudget)
                    }
                }
                currentPosition = {
                    entryTime: signal.time,
                    entryPrice: price,
                    exitTime: null,
                    exitPrice: null,
                    side: 'SELL',
                    quantity: sellQuantity,
                    pnl: null,
                    pnlPercent: null,
                    status: 'OPEN',
                }
            }
        }
    }

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
