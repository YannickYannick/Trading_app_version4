/**
 * Page Settings - Paramètres de l'application
 */
import { useState } from 'react'
import { Card, Button, Input, Badge } from '@components/common'
import { useAuth } from '@hooks/useAuth'
import './Settings.css'

export default function Settings() {
  const { user, logout } = useAuth()
  const [notifications, setNotifications] = useState(true)
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')

  const handleSave = () => {
    // TODO: Implémenter la sauvegarde des paramètres
    alert('Paramètres sauvegardés (fonctionnalité à implémenter)')
  }

  return (
    <div className="settings-page">
      <h1>Paramètres</h1>

      <div className="settings-grid">
        <Card title="Profil Utilisateur" className="settings-card">
          <div className="settings-section">
            <div className="settings-field">
              <label>Nom d'utilisateur</label>
              <Input value={user?.username || ''} disabled />
            </div>
            <div className="settings-field">
              <label>Email</label>
              <Input value={user?.email || ''} disabled />
            </div>
          </div>
        </Card>

        <Card title="Préférences" className="settings-card">
          <div className="settings-section">
            <div className="settings-field">
              <label>
                <input
                  type="checkbox"
                  checked={notifications}
                  onChange={(e) => setNotifications(e.target.checked)}
                />
                <span>Activer les notifications</span>
              </label>
            </div>
            <div className="settings-field">
              <label>Thème</label>
              <select
                value={theme}
                onChange={(e) => setTheme(e.target.value as 'dark' | 'light')}
                className="settings-select"
              >
                <option value="dark">Sombre</option>
                <option value="light">Clair</option>
              </select>
            </div>
          </div>
        </Card>

        <Card title="Sécurité" className="settings-card">
          <div className="settings-section">
            <div className="settings-field">
              <label>Changer le mot de passe</label>
              <Button variant="outline" size="sm">
                Modifier
              </Button>
            </div>
            <div className="settings-field">
              <label>Déconnexion</label>
              <Button variant="danger" size="sm" onClick={logout}>
                Se déconnecter
              </Button>
            </div>
          </div>
        </Card>

        <Card title="Informations" className="settings-card">
          <div className="settings-section">
            <div className="settings-field">
              <label>Version de l'application</label>
              <Badge variant="outline">v1.0.0</Badge>
            </div>
            <div className="settings-field">
              <label>Environnement</label>
              <Badge variant="outline">
                {import.meta.env.MODE === 'development' ? 'Développement' : 'Production'}
              </Badge>
            </div>
          </div>
        </Card>
      </div>

      <div className="settings-actions">
        <Button variant="primary" onClick={handleSave}>
          Enregistrer les modifications
        </Button>
      </div>
    </div>
  )
}

