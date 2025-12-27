/**
 * Hook pour gérer les brokers et comptes broker
 */
import { useState, useEffect, useCallback } from 'react'
import { brokerService } from '@services'
import type { Broker, BrokerAccount, BrokerSyncLog, ApiError } from '@types'

export interface UseBrokersOptions {
  autoFetch?: boolean
  brokerType?: 'SAXO' | 'BINANCE' | 'IB' | 'OTHER'
  isActive?: boolean
}

export function useBrokers(options: UseBrokersOptions = {}) {
  const { autoFetch = true, brokerType, isActive } = options
  const [brokers, setBrokers] = useState<Broker[]>([])
  const [accounts, setAccounts] = useState<BrokerAccount[]>([])
  const [loading, setLoading] = useState(autoFetch)
  const [error, setError] = useState<string | null>(null)

  const fetchBrokers = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await brokerService.getAll()
      let filteredBrokers = response.results

      if (brokerType) {
        filteredBrokers = filteredBrokers.filter((b) => b.broker_type === brokerType)
      }

      setBrokers(filteredBrokers)
    } catch (err: any) {
      const apiError = err as ApiError
      setError(apiError.error || apiError.message || 'Erreur lors du chargement des brokers')
      setBrokers([])
    } finally {
      setLoading(false)
    }
  }, [brokerType])

  const fetchAccounts = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await brokerService.getAccounts()
      let filteredAccounts = response.results

      if (isActive !== undefined) {
        filteredAccounts = filteredAccounts.filter((a) => a.is_active === isActive)
      }

      setAccounts(filteredAccounts)
    } catch (err: any) {
      const apiError = err as ApiError
      setError(apiError.error || apiError.message || 'Erreur lors du chargement des comptes')
      setAccounts([])
    } finally {
      setLoading(false)
    }
  }, [isActive])

  useEffect(() => {
    if (autoFetch) {
      fetchBrokers()
      fetchAccounts()
    }
  }, [autoFetch, fetchBrokers, fetchAccounts])

  return {
    brokers,
    accounts,
    loading,
    error,
    refetch: () => {
      fetchBrokers()
      fetchAccounts()
    },
  }
}

export function useBrokerAccount(accountId: number | null) {
  const [account, setAccount] = useState<BrokerAccount | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchAccount = useCallback(async () => {
    if (!accountId) {
      setAccount(null)
      return
    }

    try {
      setLoading(true)
      setError(null)
      const data = await brokerService.getAccountById(accountId)
      setAccount(data)
    } catch (err: any) {
      const apiError = err as ApiError
      setError(apiError.error || apiError.message || 'Erreur lors du chargement du compte')
      setAccount(null)
    } finally {
      setLoading(false)
    }
  }, [accountId])

  useEffect(() => {
    fetchAccount()
  }, [fetchAccount])

  return {
    account,
    loading,
    error,
    refetch: fetchAccount,
  }
}

export function useBrokerSyncLogs(accountId?: number) {
  const [logs, setLogs] = useState<BrokerSyncLog[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await brokerService.getSyncLogs(accountId)
      setLogs(response.results)
    } catch (err: any) {
      const apiError = err as ApiError
      setError(apiError.error || apiError.message || 'Erreur lors du chargement des logs')
      setLogs([])
    } finally {
      setLoading(false)
    }
  }, [accountId])

  useEffect(() => {
    fetchLogs()
  }, [fetchLogs])

  return {
    logs,
    loading,
    error,
    refetch: fetchLogs,
  }
}
