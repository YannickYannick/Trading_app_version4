/**
 * Route protégée - Vérifie l'authentification avant d'afficher les routes
 */
import { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { authService } from '@services'

interface ProtectedRouteProps {
  children: ReactNode
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const location = useLocation()
  const isAuthenticated = authService.isAuthenticated()

  // Si l'utilisateur n'est pas authentifié, rediriger vers login
  // et sauvegarder la page d'origine pour y revenir après connexion
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}

