/**
 * Hook pour gérer l'authentification
 */
import { useState, useEffect, useCallback } from 'react'
import { authService } from '@services'
import type { User, LoginCredentials, ApiError } from '@types'

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Vérifier l'authentification au chargement
  useEffect(() => {
    const checkAuth = async () => {
      try {
        setLoading(true)
        const authenticated = authService.isAuthenticated()
        setIsAuthenticated(authenticated)

        // Si authentifié, charger les infos utilisateur
        if (authenticated) {
          try {
            const userData = await authService.getCurrentUser()
            setUser(userData)
          } catch (err) {
            // Si erreur, l'utilisateur n'est peut-être plus authentifié
            console.warn('Erreur lors du chargement de l\'utilisateur:', err)
            setIsAuthenticated(false)
            setUser(null)
          }
        } else {
          setUser(null)
        }
      } catch (err) {
        console.error('Erreur lors de la vérification de l\'authentification:', err)
        setIsAuthenticated(false)
        setUser(null)
      } finally {
        setLoading(false)
      }
    }

    checkAuth()
  }, [])

  const login = useCallback(async (credentials: LoginCredentials) => {
    try {
      setLoading(true)
      setError(null)
      const response = await authService.loginJWT(credentials)
      setUser(response.user)
      setIsAuthenticated(true)
      return response
    } catch (err: any) {
      const apiError = err as ApiError
      const errorMessage = apiError.error || apiError.message || 'Erreur de connexion'
      setError(errorMessage)
      setIsAuthenticated(false)
      setUser(null)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      setLoading(true)
      await authService.logout()
      setUser(null)
      setIsAuthenticated(false)
      setError(null)
    } catch (err: any) {
      const apiError = err as ApiError
      setError(apiError.error || apiError.message || 'Erreur lors de la déconnexion')
      // Déconnecter quand même localement
      setUser(null)
      setIsAuthenticated(false)
    } finally {
      setLoading(false)
    }
  }, [])

  const refreshUser = useCallback(async () => {
    if (!isAuthenticated) return

    try {
      const userData = await authService.getCurrentUser()
      setUser(userData)
    } catch (err) {
      console.error('Erreur lors du rafraîchissement de l\'utilisateur:', err)
      // Si erreur, déconnecter
      setIsAuthenticated(false)
      setUser(null)
    }
  }, [isAuthenticated])

  return {
    user,
    isAuthenticated,
    loading,
    error,
    login,
    logout,
    refreshUser,
  }
}

