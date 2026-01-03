import { useState, useEffect, useCallback } from 'react'
import { tradesService, positionsService, brokersService } from '../services/api'
import type { Trade, BrokerAccount } from '@trading-app/shared'

export interface DashboardData {
    summary: {
        total_pnl: number
        open_positions_count: number
        win_rate: number
        total_trades: number
        total_capital: number
    }
    recentTrades: Trade[]
    brokerAccounts: BrokerAccount[]
}

export const useDashboardData = () => {
    const [data, setData] = useState<DashboardData | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const fetchData = useCallback(async () => {
        try {
            setIsLoading(true)
            setError(null)

            // 1. Fetch initial data
            const [stats, positionsSummary, recentTrades, brokersRes] = await Promise.all([
                tradesService.getStatistics(),
                positionsService.getSummary(),
                tradesService.getRecent(5),
                brokersService.getAccounts()
            ])

            let accounts = brokersRes.results || []

            // 2. Refresh balances for each account (parallel)
            // This ensures we have the latest balance from the broker (API)
            const updatedAccountsPromises = accounts.map(async (account) => {
                try {
                    // Only refresh if active
                    if (account.is_active) {
                        const balanceRes = await brokersService.refreshBalance(account.id)
                        if (balanceRes.success) {
                            return {
                                ...account,
                                balance_eur: balanceRes.balance_eur,
                                currency: balanceRes.currency
                            }
                        }
                    }
                    return account
                } catch (err) {
                    console.warn(`Failed to refresh balance for account ${account.id}`, err)
                    return account
                }
            })

            const updatedAccounts = await Promise.all(updatedAccountsPromises)

            // 3. Calculate total capital from FRESH balances
            const totalCapital = updatedAccounts.reduce((sum: number, acc: any) => sum + (Number(acc.balance_eur) || 0), 0)

            setData({
                summary: {
                    total_pnl: positionsSummary.total_pnl,
                    open_positions_count: positionsSummary.total_positions || 0,
                    win_rate: stats.win_rate || 0,
                    total_trades: stats.total_trades || 0,
                    total_capital: totalCapital
                },
                recentTrades: recentTrades,
                brokerAccounts: updatedAccounts
            })
        } catch (e: any) {
            console.error('Error fetching dashboard data:', e)
            setError('Impossible de charger les données')
        } finally {
            setIsLoading(false)
        }
    }, [])

    useEffect(() => {
        fetchData()
    }, [fetchData])

    return { data, isLoading, error, refresh: fetchData }
}
