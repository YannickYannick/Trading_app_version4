/**
 * Utilitaires pour calculer les indicateurs techniques
 */

/**
 * Calcule le RSI (Relative Strength Index)
 * @param prices Tableau des prix de clôture
 * @param period Période (par défaut 14)
 * @returns Tableau des valeurs RSI
 */
export function calculateRSI(prices: number[], period: number = 14): number[] {
    if (prices.length < period + 1) {
        return new Array(prices.length).fill(50) // RSI neutre si pas assez de données
    }

    const rsi: number[] = new Array(prices.length).fill(50)

    // Calculer les gains et pertes
    const gains: number[] = []
    const losses: number[] = []

    for (let i = 1; i < prices.length; i++) {
        const change = prices[i] - prices[i - 1]
        gains.push(change > 0 ? change : 0)
        losses.push(change < 0 ? Math.abs(change) : 0)
    }

    // Calculer la moyenne mobile exponentielle (EMA) des gains et pertes
    let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period
    let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period

    // Premier RSI
    if (avgLoss === 0) {
        rsi[period] = 100
    } else {
        const rs = avgGain / avgLoss
        rsi[period] = 100 - (100 / (1 + rs))
    }

    // Calculer les RSI suivants avec smoothing
    for (let i = period + 1; i < prices.length; i++) {
        const gain = gains[i - 1]
        const loss = losses[i - 1]

        avgGain = (avgGain * (period - 1) + gain) / period
        avgLoss = (avgLoss * (period - 1) + loss) / period

        if (avgLoss === 0) {
            rsi[i] = 100
        } else {
            const rs = avgGain / avgLoss
            rsi[i] = 100 - (100 / (1 + rs))
        }
    }

    return rsi
}

/**
 * Calcule la moyenne mobile simple (SMA)
 * @param prices Tableau des prix
 * @param period Période
 * @returns Tableau des valeurs MA
 */
export function calculateMA(prices: number[], period: number): number[] {
    const ma: number[] = []

    for (let i = 0; i < prices.length; i++) {
        if (i < period - 1) {
            ma.push(NaN) // Pas assez de données
        } else {
            const sum = prices.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0)
            ma.push(sum / period)
        }
    }

    return ma
}

/**
 * Calcule la moyenne mobile exponentielle (EMA)
 * @param prices Tableau des prix
 * @param period Période
 * @returns Tableau des valeurs EMA
 */
export function calculateEMA(prices: number[], period: number): number[] {
    if (prices.length === 0) return []

    const ema: number[] = []
    const multiplier = 2 / (period + 1)

    // Premier EMA = prix
    ema[0] = prices[0]

    // Calculer les EMA suivants
    for (let i = 1; i < prices.length; i++) {
        ema[i] = (prices[i] - ema[i - 1]) * multiplier + ema[i - 1]
    }

    return ema
}

/**
 * Calcule les bandes de Bollinger
 * @param prices Tableau des prix
 * @param period Période (par défaut 20)
 * @param stdDev Écart-type (par défaut 2)
 * @returns Objet avec upper, middle, lower
 */
export function calculateBollingerBands(
    prices: number[],
    period: number = 20,
    stdDev: number = 2
): { upper: number[]; middle: number[]; lower: number[] } {
    const middle = calculateMA(prices, period)
    const upper: number[] = []
    const lower: number[] = []

    for (let i = 0; i < prices.length; i++) {
        if (i < period - 1) {
            upper.push(NaN)
            lower.push(NaN)
        } else {
            // Calculer l'écart-type
            const slice = prices.slice(i - period + 1, i + 1)
            const mean = middle[i]
            const variance = slice.reduce((sum, price) => sum + Math.pow(price - mean, 2), 0) / period
            const standardDeviation = Math.sqrt(variance)

            upper.push(mean + stdDev * standardDeviation)
            lower.push(mean - stdDev * standardDeviation)
        }
    }

    return { upper, middle, lower }
}

/**
 * Calcule le MACD (Moving Average Convergence Divergence)
 * @param prices Tableau des prix
 * @param fastPeriod Période EMA rapide (par défaut 12)
 * @param slowPeriod Période EMA lente (par défaut 26)
 * @param signalPeriod Période signal (par défaut 9)
 * @returns Objet avec macd, signal, histogram
 */
export function calculateMACD(
    prices: number[],
    fastPeriod: number = 12,
    slowPeriod: number = 26,
    signalPeriod: number = 9
): { macd: number[]; signal: number[]; histogram: number[] } {
    const fastEMA = calculateEMA(prices, fastPeriod)
    const slowEMA = calculateEMA(prices, slowPeriod)

    // MACD = EMA rapide - EMA lente
    const macd: number[] = []
    const maxLength = Math.max(fastEMA.length, slowEMA.length)

    for (let i = 0; i < maxLength; i++) {
        if (i < Math.max(fastPeriod, slowPeriod) - 1) {
            macd.push(NaN)
        } else {
            macd.push(fastEMA[i] - slowEMA[i])
        }
    }

    // Signal = EMA du MACD
    // Filtrer les NaN pour le calcul EMA
    const macdValues = macd.filter(v => !isNaN(v))
    const signalEMA = calculateEMA(macdValues, signalPeriod)

    // Aligner les indices
    const signal: number[] = new Array(macd.length).fill(NaN)
    const firstSignalIndex = macd.findIndex(v => !isNaN(v)) + signalPeriod - 1
    for (let i = 0; i < signalEMA.length; i++) {
        if (firstSignalIndex + i < signal.length) {
            signal[firstSignalIndex + i] = signalEMA[i]
        }
    }

    // Histogram = MACD - Signal
    const histogram: number[] = []
    for (let i = 0; i < macd.length; i++) {
        if (isNaN(macd[i]) || isNaN(signal[i])) {
            histogram.push(NaN)
        } else {
            histogram.push(macd[i] - signal[i])
        }
    }

    return { macd, signal, histogram }
}

/**
 * Calcule le standard deviation pour une série
 */
export function calculateStdDev(values: number[], period: number): number[] {
    const stdDev: number[] = []

    for (let i = 0; i < values.length; i++) {
        if (i < period - 1) {
            stdDev.push(NaN)
        } else {
            const slice = values.slice(i - period + 1, i + 1)
            const mean = slice.reduce((a, b) => a + b, 0) / period
            const variance = slice.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / period
            stdDev.push(Math.sqrt(variance))
        }
    }

    return stdDev
}
