/**
 * Modal pour gérer l'authentification OAuth2 Saxo
 */
import { useState } from 'react'
import Button from '@components/common/Button'
import Input from '@components/common/Input'
import Loading from '@components/common/Loading'
import Badge from '@components/common/Badge'
import { brokerService } from '@services'
import type { BrokerAccount } from '@types'
import './SaxoOAuthModal.css'

interface SaxoOAuthModalProps {
  account: BrokerAccount
  onSuccess: () => void
  onClose: () => void
}

export default function SaxoOAuthModal({ account, onSuccess, onClose }: SaxoOAuthModalProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [step, setStep] = useState<'start' | 'code' | 'success'>('start')
  const [authUrl, setAuthUrl] = useState<string | null>(null)
  const [code, setCode] = useState('')
  const [state, setState] = useState<string | null>(null)

  const handleGetAuthUrl = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await brokerService.getSaxoAuthUrl(account.id)
      if (response.auth_url) {
        setAuthUrl(response.auth_url)
        setState(response.state || null)
        setStep('code')
        // Ouvrir l'URL dans un nouvel onglet
        window.open(response.auth_url, '_blank')
      } else {
        setError('Impossible d\'obtenir l\'URL d\'authentification')
      }
    } catch (err: any) {
      setError(err.error || err.message || 'Erreur lors de la récupération de l\'URL')
    } finally {
      setLoading(false)
    }
  }

  const handleExchangeCode = async () => {
    if (!code.trim()) {
      setError('Veuillez entrer le code d\'autorisation')
      return
    }

    setLoading(true)
    setError(null)

    try {
      await brokerService.exchangeSaxoAuthCode(account.id, code, state || undefined)
      setStep('success')
      setTimeout(() => {
        onSuccess()
        onClose()
      }, 2000)
    } catch (err: any) {
      setError(err.error || err.message || 'Erreur lors de l\'échange du code')
    } finally {
      setLoading(false)
    }
  }

  const hasTokens = account.saxo_access_token || account.saxo_refresh_token

  return (
    <div className="saxo-oauth-modal">
      <div className="saxo-oauth-header">
        <h3>Authentification OAuth2 Saxo Bank</h3>
        {hasTokens && (
          <Badge variant="success">Tokens présents</Badge>
        )}
      </div>

      {step === 'start' && (
        <div className="saxo-oauth-content">
          <div className="saxo-oauth-info">
            <p>
              <strong>Étape 1 :</strong> Obtenir l'URL d'authentification
            </p>
            <p className="saxo-oauth-hint">
              Cliquez sur le bouton ci-dessous pour obtenir l'URL d'authentification Saxo.
              Vous serez redirigé vers la page de connexion Saxo Bank.
            </p>
          </div>

          {error && <div className="saxo-oauth-error">{error}</div>}

          <div className="saxo-oauth-actions">
            <Button
              onClick={handleGetAuthUrl}
              disabled={loading}
              variant="primary"
              fullWidth
            >
              {loading ? <Loading size="sm" /> : '🔗 Obtenir l\'URL d\'authentification'}
            </Button>
          </div>

          {hasTokens && (
            <div className="saxo-oauth-tokens-info">
              <p>
                <strong>Tokens actuels :</strong>
              </p>
              <ul>
                <li>Access Token: {account.saxo_access_token ? '✅ Présent' : '❌ Absent'}</li>
                <li>Refresh Token: {account.saxo_refresh_token ? '✅ Présent' : '❌ Absent'}</li>
                {account.saxo_token_expires_at && (
                  <li>Expire le: {new Date(account.saxo_token_expires_at).toLocaleString('fr-FR')}</li>
                )}
              </ul>
            </div>
          )}
        </div>
      )}

      {step === 'code' && (
        <div className="saxo-oauth-content">
          <div className="saxo-oauth-info">
            <p>
              <strong>Étape 2 :</strong> Échanger le code contre des tokens
            </p>
            <p className="saxo-oauth-hint">
              Après vous être connecté sur Saxo Bank et avoir autorisé l'application,
              vous avez été redirigé vers une URL avec un paramètre <code>code</code>.
              Copiez ce code et collez-le ci-dessous.
            </p>
            {authUrl && (
              <p className="saxo-oauth-url">
                <strong>URL d'authentification :</strong>
                <br />
                <a href={authUrl} target="_blank" rel="noopener noreferrer">
                  {authUrl}
                </a>
              </p>
            )}
          </div>

          {error && <div className="saxo-oauth-error">{error}</div>}

          <Input
            label="Code d'autorisation"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Collez le code d'autorisation ici"
            fullWidth
          />

          <div className="saxo-oauth-actions">
            <Button
              onClick={handleExchangeCode}
              disabled={loading || !code.trim()}
              variant="primary"
              fullWidth
            >
              {loading ? <Loading size="sm" /> : '✅ Échanger le code'}
            </Button>
            <Button
              onClick={() => {
                setStep('start')
                setCode('')
                setError(null)
              }}
              variant="outline"
              fullWidth
            >
              Retour
            </Button>
          </div>
        </div>
      )}

      {step === 'success' && (
        <div className="saxo-oauth-content">
          <div className="saxo-oauth-success">
            <Badge variant="success" className="saxo-oauth-success-badge">
              ✅ Succès !
            </Badge>
            <p>Les tokens ont été sauvegardés avec succès.</p>
            <p>Fermeture automatique dans quelques secondes...</p>
          </div>
        </div>
      )}

      <div className="saxo-oauth-footer">
        <Button onClick={onClose} variant="outline" fullWidth>
          Fermer
        </Button>
      </div>
    </div>
  )
}
