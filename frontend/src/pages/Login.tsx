/**
 * Page Login - Authentification
 */
import { useState, FormEvent } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Button, Card, Input, Loading } from '@components/common'
import { authService } from '@services'
import type { LoginCredentials } from '@types'
import './Login.css'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [credentials, setCredentials] = useState<LoginCredentials>({
    username: '',
    password: '',
  })

  // Récupérer la page d'origine depuis l'état de navigation
  const from = (location.state as any)?.from?.pathname || '/'

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      // Utiliser JWT par défaut
      await authService.loginJWT(credentials)
      
      // Rediriger vers la page d'origine ou le dashboard
      navigate(from, { replace: true })
    } catch (err: any) {
      setError(err.error || err.message || 'Erreur de connexion')
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (field: keyof LoginCredentials) => (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    setCredentials((prev) => ({
      ...prev,
      [field]: e.target.value,
    }))
  }

  return (
    <div className="login-page">
      <Card className="login-card">
        <div className="login-header">
          <h1 className="login-title">Trading App</h1>
          <p className="login-subtitle">Connectez-vous à votre compte</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {error && (
            <div className="login-error">
              <p>{error}</p>
            </div>
          )}

          <Input
            label="Nom d'utilisateur"
            type="text"
            value={credentials.username}
            onChange={handleChange('username')}
            required
            autoComplete="username"
            disabled={loading}
            fullWidth
          />

          <Input
            label="Mot de passe"
            type="password"
            value={credentials.password}
            onChange={handleChange('password')}
            required
            autoComplete="current-password"
            disabled={loading}
            fullWidth
          />

          <Button
            type="submit"
            variant="primary"
            fullWidth
            isLoading={loading}
            loadingText="Connexion..."
            disabled={loading}
          >
            Se connecter
          </Button>
        </form>
      </Card>
    </div>
  )
}

