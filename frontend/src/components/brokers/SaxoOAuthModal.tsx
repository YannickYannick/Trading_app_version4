/**
 * Modal pour gérer l'authentification OAuth2 Saxo
 */
import { useState } from 'react'
import { 
  Link2, 
  Key, 
  CheckCircle2, 
  Copy, 
  Check, 
  ExternalLink, 
  AlertCircle,
  ArrowLeft,
  Shield,
  Clock,
  RefreshCw
} from 'lucide-react'
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
  const [copied, setCopied] = useState(false)

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

  const handleCopyUrl = async () => {
    if (!authUrl) return
    try {
      await navigator.clipboard.writeText(authUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Erreur lors de la copie:', err)
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
      // Extraire le code depuis l'URL si nécessaire
      let authCode = code.trim()
      try {
        const url = new URL(authCode)
        const codeParam = url.searchParams.get('code')
        if (codeParam) {
          authCode = codeParam
          setCode(codeParam) // Mettre à jour l'input avec le code extrait
        }
      } catch {
        // Ce n'est pas une URL, utiliser le code tel quel
      }

      await brokerService.exchangeSaxoAuthCode(account.id, authCode, state || undefined)
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
  const tokenExpiresAt = account.saxo_token_expires_at 
    ? new Date(account.saxo_token_expires_at)
    : null
  const isTokenExpired = tokenExpiresAt ? tokenExpiresAt < new Date() : false

  return (
    <div className="saxo-oauth-modal">
      {/* En-tête avec statut */}
      <div className="saxo-oauth-header">
        <div className="saxo-oauth-header-content">
          <div className="saxo-oauth-header-icon">
            <Shield size={24} />
          </div>
          <div>
            <h3>Authentification OAuth2 Saxo Bank</h3>
            <p className="saxo-oauth-subtitle">Sécurisez votre connexion avec Saxo Bank</p>
          </div>
        </div>
        {hasTokens && (
          <Badge variant={isTokenExpired ? 'warning' : 'success'}>
            {isTokenExpired ? 'Token expiré' : 'Token actif'}
          </Badge>
        )}
      </div>

      {/* Indicateur de progression */}
      <div className="saxo-oauth-steps">
        <div className={`saxo-oauth-step ${step === 'start' ? 'active' : step !== 'start' ? 'completed' : ''}`}>
          <div className="saxo-oauth-step-number">1</div>
          <div className="saxo-oauth-step-label">Obtenir l'URL</div>
        </div>
        <div className={`saxo-oauth-step-connector ${step === 'code' || step === 'success' ? 'completed' : ''}`} />
        <div className={`saxo-oauth-step ${step === 'code' ? 'active' : step === 'success' ? 'completed' : ''}`}>
          <div className="saxo-oauth-step-number">2</div>
          <div className="saxo-oauth-step-label">Échanger le code</div>
        </div>
        <div className={`saxo-oauth-step-connector ${step === 'success' ? 'completed' : ''}`} />
        <div className={`saxo-oauth-step ${step === 'success' ? 'active' : ''}`}>
          <div className="saxo-oauth-step-number">3</div>
          <div className="saxo-oauth-step-label">Terminé</div>
        </div>
      </div>

      {/* Étape 1 : Obtenir l'URL */}
      {step === 'start' && (
        <div className="saxo-oauth-content">
          <div className="saxo-oauth-info-card">
            <div className="saxo-oauth-info-icon">
              <Link2 size={32} />
            </div>
            <h4>Étape 1 : Obtenir l'URL d'authentification</h4>
            <p className="saxo-oauth-hint">
              Cliquez sur le bouton ci-dessous pour générer l'URL d'authentification Saxo Bank.
              Un nouvel onglet s'ouvrira automatiquement vers la page de connexion.
            </p>
          </div>

          {error && (
            <div className="saxo-oauth-error">
              <AlertCircle size={20} />
              <span>{error}</span>
            </div>
          )}

          <div className="saxo-oauth-actions">
            <Button
              onClick={handleGetAuthUrl}
              disabled={loading}
              variant="primary"
              fullWidth
              className="saxo-oauth-primary-button"
            >
              {loading ? (
                <>
                  <Loading size="sm" />
                  <span>Génération en cours...</span>
                </>
              ) : (
                <>
                  <ExternalLink size={18} />
                  <span>Obtenir l'URL d'authentification</span>
                </>
              )}
            </Button>
          </div>

          {hasTokens && (
            <div className="saxo-oauth-tokens-info">
              <div className="saxo-oauth-tokens-header">
                <Key size={18} />
                <strong>Statut des tokens actuels</strong>
              </div>
              <div className="saxo-oauth-tokens-list">
                <div className="saxo-oauth-token-item">
                  <span>Access Token:</span>
                  <Badge variant={account.saxo_access_token ? 'success' : 'primary'}>
                    {account.saxo_access_token ? 'Présent' : 'Absent'}
                  </Badge>
                </div>
                <div className="saxo-oauth-token-item">
                  <span>Refresh Token:</span>
                  <Badge variant={account.saxo_refresh_token ? 'success' : 'primary'}>
                    {account.saxo_refresh_token ? 'Présent' : 'Absent'}
                  </Badge>
                </div>
                {tokenExpiresAt && (
                  <div className="saxo-oauth-token-item">
                    <span>
                      <Clock size={14} />
                      Expiration:
                    </span>
                    <span className={isTokenExpired ? 'saxo-oauth-token-expired' : ''}>
                      {tokenExpiresAt.toLocaleString('fr-FR', {
                        day: '2-digit',
                        month: '2-digit',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Étape 2 : Échanger le code */}
      {step === 'code' && (
        <div className="saxo-oauth-content">
          <div className="saxo-oauth-info-card">
            <div className="saxo-oauth-info-icon">
              <Key size={32} />
            </div>
            <h4>Étape 2 : Échanger le code d'autorisation</h4>
            <p className="saxo-oauth-hint">
              Après vous être connecté sur Saxo Bank et avoir autorisé l'application,
              vous avez été redirigé vers une URL avec un paramètre <code>code</code>.
            </p>
            <div className="saxo-oauth-instructions">
              <strong>Instructions :</strong>
              <ol>
                <li>Connectez-vous sur Saxo Bank dans l'onglet qui s'est ouvert</li>
                <li>Autorisez l'application</li>
                <li>Copiez le code depuis l'URL de redirection</li>
                <li>Collez-le dans le champ ci-dessous</li>
              </ol>
            </div>
          </div>

          {authUrl && (
            <div className="saxo-oauth-url-card">
              <div className="saxo-oauth-url-header">
                <span>
                  <ExternalLink size={16} />
                  URL d'authentification
                </span>
                <Button
                  onClick={handleCopyUrl}
                  variant="outline"
                  size="sm"
                  className="saxo-oauth-copy-button"
                >
                  {copied ? (
                    <>
                      <Check size={14} />
                      <span>Copié</span>
                    </>
                  ) : (
                    <>
                      <Copy size={14} />
                      <span>Copier</span>
                    </>
                  )}
                </Button>
              </div>
              <div className="saxo-oauth-url-value" onClick={handleCopyUrl} title="Cliquer pour copier">
                {authUrl}
              </div>
              <a 
                href={authUrl} 
                target="_blank" 
                rel="noopener noreferrer"
                className="saxo-oauth-url-link"
              >
                Ouvrir dans un nouvel onglet <ExternalLink size={14} />
              </a>
            </div>
          )}

          {error && (
            <div className="saxo-oauth-error">
              <AlertCircle size={20} />
              <span>{error}</span>
            </div>
          )}

          <div className="saxo-oauth-input-section">
            <Input
              label="Code d'autorisation"
              value={code}
              onChange={(e) => {
                setCode(e.target.value)
                setError(null)
              }}
              placeholder="Collez le code d'autorisation ici ou l'URL complète de redirection"
              fullWidth
              className="saxo-oauth-code-input"
            />
            <p className="saxo-oauth-input-hint">
              💡 Astuce : Vous pouvez coller l'URL complète, le code sera extrait automatiquement
            </p>
          </div>

          <div className="saxo-oauth-actions">
            <Button
              onClick={handleExchangeCode}
              disabled={loading || !code.trim()}
              variant="primary"
              fullWidth
              className="saxo-oauth-primary-button"
            >
              {loading ? (
                <>
                  <Loading size="sm" />
                  <span>Échange en cours...</span>
                </>
              ) : (
                <>
                  <RefreshCw size={18} />
                  <span>Échanger le code</span>
                </>
              )}
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
              <ArrowLeft size={18} />
              <span>Retour</span>
            </Button>
          </div>
        </div>
      )}

      {/* Étape 3 : Succès */}
      {step === 'success' && (
        <div className="saxo-oauth-content">
          <div className="saxo-oauth-success">
            <div className="saxo-oauth-success-icon">
              <CheckCircle2 size={64} />
            </div>
            <Badge variant="success" className="saxo-oauth-success-badge">
              Authentification réussie !
            </Badge>
            <p className="saxo-oauth-success-message">
              Les tokens d'authentification ont été sauvegardés avec succès.
            </p>
            <p className="saxo-oauth-success-hint">
              La fenêtre se fermera automatiquement dans quelques secondes...
            </p>
          </div>
        </div>
      )}

      {/* Footer */}
      {step !== 'success' && (
        <div className="saxo-oauth-footer">
          <Button onClick={onClose} variant="outline" fullWidth>
            Annuler
          </Button>
        </div>
      )}
    </div>
  )
}
