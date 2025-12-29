/**
 * Page Brokers - Gestion complète des comptes broker
 */
import { useState, useMemo } from 'react'
import { useBrokers } from '@hooks/useBrokers'
import { brokerService } from '@services'
import Card from '@components/common/Card'
import Button from '@components/common/Button'
import Badge from '@components/common/Badge'
import Loading from '@components/common/Loading'
import Modal from '@components/common/Modal'
import Input from '@components/common/Input'
import { formatDate, formatDateRelative } from '@utils/format'
import type { BrokerAccount } from '@types'
import BrokerForm from '@components/brokers/BrokerForm'
import BrokerTestModal from '@components/brokers/BrokerTestModal'
import BrokerSyncModal from '@components/brokers/BrokerSyncModal'
import BrokerBalance from '@components/brokers/BrokerBalance'
import SaxoOAuthModal from '@components/brokers/SaxoOAuthModal'
import SaxoTransactionsModal from '@components/brokers/SaxoTransactionsModal'
import './Brokers.css'

export default function Brokers() {
  const { accounts, brokers, loading, error, refetch } = useBrokers()
  const [selectedAccount, setSelectedAccount] = useState<BrokerAccount | null>(null)
  const [isFormModalOpen, setIsFormModalOpen] = useState(false)
  const [isTestModalOpen, setIsTestModalOpen] = useState(false)
  const [isSyncModalOpen, setIsSyncModalOpen] = useState(false)
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
  const [isSaxoOAuthModalOpen, setIsSaxoOAuthModalOpen] = useState(false)
  const [isSaxoTransactionsModalOpen, setIsSaxoTransactionsModalOpen] = useState(false)
  const [accountToDelete, setAccountToDelete] = useState<BrokerAccount | null>(null)
  const [refreshingTokens, setRefreshingTokens] = useState<Set<number>>(new Set())
  const [searchTerm, setSearchTerm] = useState('')
  const [filterType, setFilterType] = useState<'ALL' | 'SAXO' | 'BINANCE' | 'IB' | 'OTHER'>('ALL')
  const [filterStatus, setFilterStatus] = useState<'ALL' | 'ACTIVE' | 'INACTIVE'>('ALL')

  // Filtrer les comptes
  const filteredAccounts = useMemo(() => {
    return accounts.filter((account) => {
      // Recherche avec gestion des valeurs null/undefined
      const accountName = account.name || account.account_name || ''
      const brokerName = account.broker_name || account.broker?.name || account.broker_type_display || account.broker_type || ''
      const matchesSearch =
        accountName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        brokerName.toLowerCase().includes(searchTerm.toLowerCase())
      
      // Filtre par type
      const accountBrokerType = account.broker_type || account.broker?.broker_type
      const matchesType = filterType === 'ALL' || accountBrokerType === filterType
      
      // Filtre par statut
      const matchesStatus =
        filterStatus === 'ALL' ||
        (filterStatus === 'ACTIVE' && account.is_active) ||
        (filterStatus === 'INACTIVE' && !account.is_active)

      return matchesSearch && matchesType && matchesStatus
    })
  }, [accounts, searchTerm, filterType, filterStatus])

  const handleCreate = () => {
    setSelectedAccount(null)
    setIsFormModalOpen(true)
  }

  const handleEdit = (account: BrokerAccount) => {
    setSelectedAccount(account)
    setIsFormModalOpen(true)
  }

  const handleTest = (account: BrokerAccount) => {
    setSelectedAccount(account)
    setIsTestModalOpen(true)
  }

  const handleSync = (account: BrokerAccount) => {
    setSelectedAccount(account)
    setIsSyncModalOpen(true)
  }

  const handleDelete = (account: BrokerAccount) => {
    setAccountToDelete(account)
    setIsDeleteModalOpen(true)
  }

  const confirmDelete = async () => {
    if (!accountToDelete) return

    try {
      await brokerService.deleteAccount(accountToDelete.id)
      setIsDeleteModalOpen(false)
      setAccountToDelete(null)
      refetch()
    } catch (err: any) {
      alert(`Erreur lors de la suppression: ${err.error || err.message}`)
    }
  }

  const toggleActive = async (account: BrokerAccount) => {
    try {
      await brokerService.updateAccount(account.id, {
        is_active: !account.is_active,
      })
      refetch()
    } catch (err: any) {
      alert(`Erreur: ${err.error || err.message}`)
    }
  }

  const handleRefreshToken = async (account: BrokerAccount) => {
    if (account.broker_type !== 'SAXO') {
      alert('Le refresh de token est uniquement disponible pour Saxo Bank')
      return
    }

    setRefreshingTokens((prev) => new Set(prev).add(account.id))

    try {
      const updatedAccount = await brokerService.refreshSaxoToken(account.id)
      alert(
        `✅ Token rafraîchi avec succès!\n${
          updatedAccount.saxo_token_expires_at
            ? `Expire le: ${new Date(updatedAccount.saxo_token_expires_at).toLocaleString('fr-FR')}`
            : ''
        }`
      )
      refetch()
    } catch (err: any) {
      const errorMsg =
        err.response?.data?.error ||
        err.response?.data?.message ||
        err.message ||
        'Erreur lors du rafraîchissement du token'
      alert(`❌ Erreur: ${errorMsg}`)
    } finally {
      setRefreshingTokens((prev) => {
        const newSet = new Set(prev)
        newSet.delete(account.id)
        return newSet
      })
    }
  }

  if (loading) {
    return <Loading fullScreen text="Chargement des brokers..." />
  }

  if (error) {
    return (
      <div className="brokers-error">
        <p>Erreur: {error}</p>
        <Button onClick={refetch}>Réessayer</Button>
      </div>
    )
  }

  return (
    <div className="brokers-page">
      <div className="brokers-header">
        <h1 className="page-title">Brokers</h1>
        <Button onClick={handleCreate} variant="primary">
          + Nouveau Broker
        </Button>
      </div>

      {/* Filtres et recherche */}
      <div className="brokers-filters">
        <Input
          type="text"
          placeholder="Rechercher un broker..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="brokers-search"
        />
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value as any)}
          className="brokers-filter"
        >
          <option value="ALL">Tous les types</option>
          <option value="SAXO">Saxo Bank</option>
          <option value="BINANCE">Binance</option>
          <option value="IB">Interactive Brokers</option>
          <option value="OTHER">Autre</option>
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value as any)}
          className="brokers-filter"
        >
          <option value="ALL">Tous les statuts</option>
          <option value="ACTIVE">Actifs</option>
          <option value="INACTIVE">Inactifs</option>
        </select>
      </div>

      {/* Liste des brokers */}
      {filteredAccounts.length === 0 ? (
        <Card className="brokers-empty">
          <p>Aucun broker trouvé.</p>
          <Button onClick={handleCreate} variant="primary">
            Créer un broker
          </Button>
        </Card>
      ) : (
        <div className="brokers-grid">
          {filteredAccounts.map((account) => (
            <Card key={account.id} className="broker-card" hover>
              <div className="broker-card-header">
                <div>
                  <h3 className="broker-card-title">{account.name}</h3>
                  <p className="broker-card-subtitle">
                    {account.broker_name || account.broker?.name || account.broker_type_display || account.broker_type}
                  </p>
                </div>
                <div className="broker-card-badges">
                  <Badge variant={(account.broker_type || account.broker?.broker_type) === 'SAXO' ? 'primary' : 'info'}>
                    {account.broker_type_display || account.broker_type || account.broker?.broker_type || 'UNKNOWN'}
                  </Badge>
                  <Badge variant={account.is_active ? 'success' : 'outline'}>
                    {account.is_active ? 'Actif' : 'Inactif'}
                  </Badge>
                  {account.is_sandbox && (
                    <Badge variant="warning">Sandbox</Badge>
                  )}
                </div>
              </div>

              <div className="broker-card-info">
                {/* Solde EUR */}
                {(account.broker_type === 'BINANCE' || account.broker_type === 'SAXO') && (
                  <div className="broker-info-item broker-balance-container">
                    <BrokerBalance accountId={account.id} />
                  </div>
                )}
                
                <div className="broker-info-item">
                  <span className="broker-info-label">Environnement:</span>
                  <span className="broker-info-value">
                    {account.environment_display || (account.is_sandbox ? 'Simulation' : 'Live Trading')}
                  </span>
                </div>
                {account.last_sync && (
                  <div className="broker-info-item">
                    <span className="broker-info-label">Dernière sync:</span>
                    <span className="broker-info-value">
                      {formatDateRelative(account.last_sync)}
                    </span>
                  </div>
                )}
              </div>

              <div className="broker-card-actions">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={async () => {
                    try {
                      const creds = await brokerService.getCredentials(account.id)
                      console.log('Credentials:', creds)
                      alert(`Credentials:\nAPI Key: ${creds.has_api_key ? '✅ Présente' : '❌ Manquante'}\nAPI Secret: ${creds.has_api_secret ? '✅ Présente' : '❌ Manquante'}\nTestnet: ${creds.testnet}\nEnvironment: ${creds.environment}\n\nVoir la console pour plus de détails.`)
                    } catch (err: any) {
                      alert(`Erreur: ${err.message}`)
                    }
                  }}
                  title="Afficher les credentials (masqués)"
                >
                  🔑 Creds
                </Button>
                {account.broker_type === 'SAXO' && (
                  <>
                    <Button
                      size="sm"
                      variant="info"
                      onClick={() => {
                        setSelectedAccount(account)
                        setIsSaxoOAuthModalOpen(true)
                      }}
                      title="Gérer l'authentification OAuth2 Saxo"
                    >
                      🔐 OAuth2
                    </Button>
                    <Button
                      size="sm"
                      variant="info"
                      onClick={() => {
                        setSelectedAccount(account)
                        setIsSaxoTransactionsModalOpen(true)
                      }}
                      title="Voir les transactions Saxo"
                    >
                      📊 Transactions
                    </Button>
                    <Button
                      size="sm"
                      variant="info"
                      onClick={() => handleRefreshToken(account)}
                      disabled={refreshingTokens.has(account.id)}
                      title="Rafraîchir le token d'accès Saxo"
                    >
                      {refreshingTokens.has(account.id) ? '🔄...' : '🔄 Refresh Token'}
                    </Button>
                  </>
                )}
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleTest(account)}
                >
                  Tester
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleSync(account)}
                >
                  Synchroniser
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => handleEdit(account)}
                >
                  Modifier
                </Button>
                <Button
                  size="sm"
                  variant={account.is_active ? 'danger' : 'success'}
                  onClick={() => toggleActive(account)}
                >
                  {account.is_active ? 'Désactiver' : 'Activer'}
                </Button>
                <Button
                  size="sm"
                  variant="danger"
                  onClick={() => handleDelete(account)}
                >
                  Supprimer
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Modal de création/modification */}
      <Modal
        isOpen={isFormModalOpen}
        onClose={() => {
          setIsFormModalOpen(false)
          setSelectedAccount(null)
        }}
        title={selectedAccount ? 'Modifier le Broker' : 'Nouveau Broker'}
        size="lg"
      >
        <BrokerForm
          account={selectedAccount}
          brokers={brokers}
          onSuccess={() => {
            setIsFormModalOpen(false)
            setSelectedAccount(null)
            refetch()
          }}
          onCancel={() => {
            setIsFormModalOpen(false)
            setSelectedAccount(null)
          }}
        />
      </Modal>

      {/* Modal de test de connexion */}
      <Modal
        isOpen={isTestModalOpen}
        onClose={() => {
          setIsTestModalOpen(false)
          setSelectedAccount(null)
        }}
        title="Test de Connexion"
        size="md"
      >
        {selectedAccount && (
          <BrokerTestModal
            account={selectedAccount}
            onClose={() => {
              setIsTestModalOpen(false)
              setSelectedAccount(null)
            }}
          />
        )}
      </Modal>

      {/* Modal de synchronisation */}
      <Modal
        isOpen={isSyncModalOpen}
        onClose={() => {
          setIsSyncModalOpen(false)
          setSelectedAccount(null)
        }}
        title="Synchroniser les Données"
        size="md"
      >
        {selectedAccount && (
          <BrokerSyncModal
            account={selectedAccount}
            onSuccess={() => {
              setIsSyncModalOpen(false)
              setSelectedAccount(null)
              refetch()
            }}
            onClose={() => {
              setIsSyncModalOpen(false)
              setSelectedAccount(null)
            }}
          />
        )}
      </Modal>

      {/* Modal OAuth2 Saxo */}
      {selectedAccount && selectedAccount.broker_type === 'SAXO' && (
        <>
          <Modal
            isOpen={isSaxoOAuthModalOpen}
            onClose={() => {
              setIsSaxoOAuthModalOpen(false)
              setSelectedAccount(null)
            }}
            title={`OAuth2 Saxo: ${selectedAccount.name}`}
            size="md"
          >
            <SaxoOAuthModal
              account={selectedAccount}
              onSuccess={() => {
                refetch()
                setIsSaxoOAuthModalOpen(false)
                setSelectedAccount(null)
              }}
              onClose={() => {
                setIsSaxoOAuthModalOpen(false)
                setSelectedAccount(null)
              }}
            />
          </Modal>

          {/* Modal Transactions Saxo */}
          <Modal
            isOpen={isSaxoTransactionsModalOpen}
            onClose={() => {
              setIsSaxoTransactionsModalOpen(false)
              setSelectedAccount(null)
            }}
            title={`Transactions Saxo: ${selectedAccount.name}`}
            size="xl"
          >
            <SaxoTransactionsModal
              account={selectedAccount}
              onClose={() => {
                setIsSaxoTransactionsModalOpen(false)
                setSelectedAccount(null)
              }}
            />
          </Modal>
        </>
      )}

      {/* Modal de confirmation de suppression */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => {
          setIsDeleteModalOpen(false)
          setAccountToDelete(null)
        }}
        title="Supprimer le Broker"
        size="sm"
      >
        {accountToDelete && (
          <div className="delete-confirmation">
            <p>
              Êtes-vous sûr de vouloir supprimer le broker{' '}
              <strong>{accountToDelete.account_name}</strong> ?
            </p>
            <p className="delete-warning">
              Cette action est irréversible. Les données associées seront conservées.
            </p>
            <div className="delete-actions">
              <Button variant="danger" onClick={confirmDelete}>
                Supprimer
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setIsDeleteModalOpen(false)
                  setAccountToDelete(null)
                }}
              >
                Annuler
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

