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
  const [hasValidBalance, setHasValidBalance] = useState(false) // Track if we ever got a valid balance

  const fetchBalance = useCallback(async () => {
    if (!accountId) {
      setBalanceEur(null)
      setAllBalances(null)
      setHasValidBalance(false)
      return
    }

    setLoading(true)
    setError(null)
    
    try {
      const response = await brokerService.getBalanceEur(accountId)
      
      if (response.success) {
        // Ne mettre à jour que si on a une valeur valide
        if (response.balance_eur !== null && response.balance_eur !== undefined) {
          // Protection: Ne pas écraser une valeur valide (> 0) par 0
          // Sauf si c'est vraiment la première fois qu'on charge (hasValidBalance = false)
          const newBalance = response.balance_eur
          
          if (newBalance > 0 || !hasValidBalance) {
            // Toujours accepter une valeur positive ou si on n'a jamais eu de valeur valide
            setBalanceEur(newBalance)
            setAllBalances(response.all_balances || {})
            setError(null) // Clear any previous error
            if (newBalance > 0) {
              setHasValidBalance(true)
            }
          } else {
            // Si on reçoit 0 mais qu'on avait déjà une valeur valide, garder l'ancienne
            console.warn(
              `Received balance_eur = 0 but we had a valid balance (${balanceEur}). ` +
              `This might be a temporary API issue. Keeping previous value.`
            )
            // Ne pas mettre à jour, garder la valeur précédente
          }
        } else {
          // Garder la valeur précédente si la nouvelle est invalide
          console.warn('Received null/undefined balance_eur, keeping previous value')
        }
      } else {
        setError(response.error || 'Erreur lors de la récupération du solde')
        // Ne pas réinitialiser si on avait déjà une valeur valide
        if (!hasValidBalance) {
          setBalanceEur(null)
        }
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.message || 'Erreur de connexion'
      setError(errorMessage)
      // Ne pas réinitialiser si on avait déjà une valeur valide
      if (!hasValidBalance) {
        setBalanceEur(null)
      }
      console.error('Error fetching balance:', errorMessage)
    } finally {
      setLoading(false)
    }
  }, [accountId, hasValidBalance, balanceEur])

  useEffect(() => {
    // Reset hasValidBalance quand accountId change
    if (accountId) {
      setHasValidBalance(false)
      fetchBalance()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accountId]) // Only depend on accountId to avoid multiple fetches

  return {
    balanceEur,
    allBalances,
    loading,
    error,
    refresh: fetchBalance
  }
}

