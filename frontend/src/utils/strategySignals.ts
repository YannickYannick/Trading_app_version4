/**
 * Utilitaires pour calculer les signaux de trading selon les stratégies
 */
import { calculateRSI, calculateMA, calculateBollingerBands, calculateMACD, calculateEMA } from './technicalIndicators'

export type SignalType = 'BUY' | 'SELL' | 'HOLD'

export interface Signal {
  time: string // Format YYYY-MM-DD
  signal: SignalType
  price: number
  indicator?: {
    name: string
    value: number
  }
}

export interface StrategyParameters {
  // RSI
  rsi_period?: number
  rsi_low?: number
  rsi_high?: number
  
  // MA Crossover
  ma1_period?: number
  ma2_period?: number
  
  // Bollinger Bands
  bb_period?: number
  bb_std?: number
  
  // MACD
  macd_fast?: number
  macd_slow?: number
  macd_signal?: number
  
  // Threshold
  threshold_low?: number
  threshold_high?: number
  
  // Grid
  grid_min?: number
  grid_max?: number
  grid_levels?: number
  
  // Common
  order_size?: number
  stop_loss?: number
}

/**
 * Calcule les signaux pour une stratégie RSI
 */
export function calculateRSISignals(
  prices: number[],
  dates: string[],
  params: StrategyParameters
): Signal[] {
  const period = params.rsi_period || 14
  const rsiLow = params.rsi_low || 30
  const rsiHigh = params.rsi_high || 70

  const rsiValues = calculateRSI(prices, period)
  const signals: Signal[] = []

  for (let i = 0; i < prices.length; i++) {
    if (i < period) {
      signals.push({
        time: dates[i],
        signal: 'HOLD',
        price: prices[i],
      })
      continue
    }

    const rsi = rsiValues[i]
    let signalType: SignalType = 'HOLD'

    if (!isNaN(rsi)) {
      if (rsi < rsiLow) {
        signalType = 'BUY'
      } else if (rsi > rsiHigh) {
        signalType = 'SELL'
      }
    }

    signals.push({
      time: dates[i],
      signal: signalType,
      price: prices[i],
      indicator: {
        name: 'RSI',
        value: rsi,
      },
    })
  }

  return signals
}

/**
 * Calcule les signaux pour une stratégie MA Crossover
 */
export function calculateMACrossoverSignals(
  prices: number[],
  dates: string[],
  params: StrategyParameters
): Signal[] {
  const ma1Period = params.ma1_period || 20
  const ma2Period = params.ma2_period || 50

  const ma1 = calculateMA(prices, ma1Period)
  const ma2 = calculateMA(prices, ma2Period)
  const signals: Signal[] = []

  let previousSignal: SignalType = 'HOLD'

  for (let i = Math.max(ma1Period, ma2Period) - 1; i < prices.length; i++) {
    if (i === Math.max(ma1Period, ma2Period) - 1) {
      signals.push({
        time: dates[i],
        signal: 'HOLD',
        price: prices[i],
      })
      previousSignal = 'HOLD'
      continue
    }

    const ma1Current = ma1[i]
    const ma1Prev = ma1[i - 1]
    const ma2Current = ma2[i]
    const ma2Prev = ma2[i - 1]

    let signalType: SignalType = previousSignal

    if (!isNaN(ma1Current) && !isNaN(ma2Current) && !isNaN(ma1Prev) && !isNaN(ma2Prev)) {
      // Croisement haussier (BUY): MA1 passe au-dessus de MA2
      if (ma1Prev <= ma2Prev && ma1Current > ma2Current) {
        signalType = 'BUY'
      }
      // Croisement baissier (SELL): MA1 passe en-dessous de MA2
      else if (ma1Prev >= ma2Prev && ma1Current < ma2Current) {
        signalType = 'SELL'
      }
    }

    previousSignal = signalType

    signals.push({
      time: dates[i],
      signal: signalType,
      price: prices[i],
      indicator: {
        name: 'MA Crossover',
        value: ma1Current - ma2Current,
      },
    })
  }

  // Remplir le début avec HOLD
  const startSignals: Signal[] = new Array(Math.max(ma1Period, ma2Period) - 1)
    .fill(null)
    .map((_, i) => ({
      time: dates[i],
      signal: 'HOLD' as SignalType,
      price: prices[i],
    }))

  return [...startSignals, ...signals]
}

/**
 * Calcule les signaux pour une stratégie Bollinger Bands
 */
export function calculateBollingerSignals(
  prices: number[],
  dates: string[],
  params: StrategyParameters
): Signal[] {
  const period = params.bb_period || 20
  const stdDev = params.bb_std || 2

  const bands = calculateBollingerBands(prices, period, stdDev)
  const signals: Signal[] = []

  for (let i = 0; i < prices.length; i++) {
    if (i < period - 1) {
      signals.push({
        time: dates[i],
        signal: 'HOLD',
        price: prices[i],
      })
      continue
    }

    const price = prices[i]
    const upper = bands.upper[i]
    const lower = bands.lower[i]
    const middle = bands.middle[i]

    let signalType: SignalType = 'HOLD'

    if (!isNaN(upper) && !isNaN(lower) && !isNaN(middle)) {
      // Prix touche la bande inférieure = signal d'achat
      if (price <= lower) {
        signalType = 'BUY'
      }
      // Prix touche la bande supérieure = signal de vente
      else if (price >= upper) {
        signalType = 'SELL'
      }
    }

    signals.push({
      time: dates[i],
      signal: signalType,
      price: prices[i],
      indicator: {
        name: 'BB',
        value: price - middle,
      },
    })
  }

  return signals
}

/**
 * Calcule les signaux pour une stratégie MACD
 */
export function calculateMACDSignals(
  prices: number[],
  dates: string[],
  params: StrategyParameters
): Signal[] {
  const fastPeriod = params.macd_fast || 12
  const slowPeriod = params.macd_slow || 26
  const signalPeriod = params.macd_signal || 9

  const macdData = calculateMACD(prices, fastPeriod, slowPeriod, signalPeriod)
  const signals: Signal[] = []

  const firstValidIndex = Math.max(fastPeriod, slowPeriod) + signalPeriod - 1

  for (let i = 0; i < prices.length; i++) {
    if (i < firstValidIndex) {
      signals.push({
        time: dates[i],
        signal: 'HOLD',
        price: prices[i],
      })
      continue
    }

    const macd = macdData.macd[i]
    const signal = macdData.signal[i]
    const histogram = macdData.histogram[i]

    let signalType: SignalType = 'HOLD'

    if (!isNaN(macd) && !isNaN(signal) && !isNaN(histogram)) {
      // Croisement haussier: MACD passe au-dessus de la ligne de signal
      if (i > firstValidIndex) {
        const prevHistogram = macdData.histogram[i - 1]
        if (!isNaN(prevHistogram) && prevHistogram < 0 && histogram > 0) {
          signalType = 'BUY'
        } else if (!isNaN(prevHistogram) && prevHistogram > 0 && histogram < 0) {
          signalType = 'SELL'
        }
      }
    }

    signals.push({
      time: dates[i],
      signal: signalType,
      price: prices[i],
      indicator: {
        name: 'MACD',
        value: histogram,
      },
    })
  }

  return signals
}

/**
 * Calcule les signaux pour une stratégie Threshold (seuils)
 */
export function calculateThresholdSignals(
  prices: number[],
  dates: string[],
  params: StrategyParameters
): Signal[] {
  const thresholdLow = params.threshold_low || 100
  const thresholdHigh = params.threshold_high || 200

  const signals: Signal[] = []

  for (let i = 0; i < prices.length; i++) {
    const price = prices[i]
    let signalType: SignalType = 'HOLD'

    if (price <= thresholdLow) {
      signalType = 'BUY'
    } else if (price >= thresholdHigh) {
      signalType = 'SELL'
    }

    signals.push({
      time: dates[i],
      signal: signalType,
      price: prices[i],
    })
  }

  return signals
}

/**
 * Calcule les signaux pour une stratégie Grid
 */
export function calculateGridSignals(
  prices: number[],
  dates: string[],
  params: StrategyParameters
): Signal[] {
  const gridMin = params.grid_min || 100
  const gridMax = params.grid_max || 200
  const gridLevels = params.grid_levels || 10

  const signals: Signal[] = []
  const step = (gridMax - gridMin) / gridLevels

  for (let i = 0; i < prices.length; i++) {
    const price = prices[i]
    let signalType: SignalType = 'HOLD'

    // Calculer le niveau de grille le plus proche
    const level = Math.round((price - gridMin) / step)
    
    if (level === 0) {
      signalType = 'BUY' // Prix au minimum
    } else if (level >= gridLevels) {
      signalType = 'SELL' // Prix au maximum
    }

    signals.push({
      time: dates[i],
      signal: signalType,
      price: prices[i],
    })
  }

  return signals
}

/**
 * Calcule les signaux selon le type d'algorithme
 */
export function calculateStrategySignals(
  algorithmType: string,
  prices: number[],
  dates: string[],
  params: StrategyParameters
): Signal[] {
  switch (algorithmType) {
    case 'rsi':
      return calculateRSISignals(prices, dates, params)
    case 'ma_crossover':
      return calculateMACrossoverSignals(prices, dates, params)
    case 'bollinger':
      return calculateBollingerSignals(prices, dates, params)
    case 'macd':
      return calculateMACDSignals(prices, dates, params)
    case 'threshold':
      return calculateThresholdSignals(prices, dates, params)
    case 'grid':
      return calculateGridSignals(prices, dates, params)
    default:
      return dates.map((date, i) => ({
        time: date,
        signal: 'HOLD' as SignalType,
        price: prices[i] || 0,
      }))
  }
}

