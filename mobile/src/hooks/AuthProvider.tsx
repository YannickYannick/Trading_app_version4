import React, { useState, useEffect } from 'react'
import { AuthContext } from './useAuth'
import { authService } from '../services/auth'
import type { LoginCredentials, User } from '@trading-app/shared'

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [isAuthenticated, setIsAuthenticated] = useState(false)

    // Vérifier l'auth au chargement
    useEffect(() => {
        checkAuth()
    }, [])

    const checkAuth = async () => {
        try {
            const isAuth = await authService.isAuthenticated()
            setIsAuthenticated(isAuth)
            if (isAuth) {
                // Optionnel : charger le profil utilisateur ici
                // const profile = await authService.getProfile()
                // setUser(profile)
            }
        } catch (e) {
            console.error('Auth check failed', e)
        } finally {
            setIsLoading(false)
        }
    }

    const login = async (credentials: LoginCredentials) => {
        setIsLoading(true)
        try {
            await authService.loginJWT(credentials)
            setIsAuthenticated(true)
            // await loadProfile()
        } catch (e) {
            throw e
        } finally {
            setIsLoading(false)
        }
    }

    const logout = async () => {
        setIsLoading(true)
        try {
            await authService.logout()
            setUser(null)
            setIsAuthenticated(false)
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <AuthContext.Provider value={{ user, isLoading, login, logout, isAuthenticated }}>
            {children}
        </AuthContext.Provider>
    )
}
