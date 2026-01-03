import { useState, useEffect, useCallback, createContext, useContext } from 'react'
import { authService } from '../services/auth'
import type { User, LoginCredentials } from '@trading-app/shared'

interface AuthContextType {
    user: User | null
    isLoading: boolean
    login: (credentials: LoginCredentials) => Promise<void>
    logout: () => Promise<void>
    isAuthenticated: boolean
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
    const context = useContext(AuthContext)
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}

// Note: Le Provider sera implémenté dans App.tsx ou un composant dédié
// Pour l'instant on prépare la structure
