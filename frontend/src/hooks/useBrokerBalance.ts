/**
 * Hook pour récupérer et gérer le solde EUR d'un compte broker
 */
import { useState, useEffect, useCallback } from 'react'
import { brokerService } from '@services'

interface BrokerBalance {
  balance_eur: number
  currency: string
  all_balances: Record<string, number>
  timestamp?: string
}

interface UseBrokerBalanceReturn {
  balanceEur: number | null
  allBalances: Record<string, number> | null
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
}

export const useBrokerBalance = (accountId: number | null): UseBrokerBalanceReturn => {
  const [balanceEur, setBalanceEur] = useState<number | null>(null)
  const [allBalances, setAllBalances] = useState<Record<string, number> | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchBalance = useCallback(async () => {
    if (!accountId) {
      setBalanceEur(null)
      setAllBalances(null)
      return
    }

    setLoading(true)
    setError(null)
    
    try {
      const response = await brokerService.getBalanceEur(accountId)
      
      if (response.success) {
        setBalanceEur(response.balance_eur)
        setAllBalances(response.all_balances)
      } else {
        setError(response.error || 'Erreur lors de la récupération du solde')
        setBalanceEur(0)
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.message || 'Erreur de connexion'
      setError(errorMessage)
      setBalanceEur(0)
      setAllBalances(null)
    } finally {
      setLoading(false)
    }
  }, [accountId])

  useEffect(() => {
    fetchBalance()
  }, [fetchBalance])

  return {
    balanceEur,
    allBalances,
    loading,
    error,
    refresh: fetchBalance
  }
}

