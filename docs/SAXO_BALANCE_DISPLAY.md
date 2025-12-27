# 💶 Affichage du Solde Saxo Bank

Ce guide explique comment récupérer et afficher le solde d'un compte Saxo Bank dans votre application.

---

## 📋 Vue d'ensemble

Le processus d'affichage du solde Saxo suit cette architecture :

```
Frontend (React/HTML)
    ↓
API REST (Django REST Framework)
    ↓
BrokerService (Service de haut niveau)
    ↓
SaxoBroker (Implémentation du broker)
    ↓
API Saxo Bank (/port/v1/balances)
```

---

## 🔧 Partie 1 : Backend - Récupération du Solde

### 1.1 Méthode dans SaxoBroker

**Fichier** : `backend/apps/trading/brokers/saxo.py`

#### Méthode `get_account_info()`

Cette méthode récupère les informations complètes du compte depuis l'API Saxo :

```python
def get_account_info(self) -> Dict[str, Any]:
    """
    Récupérer les informations du compte
    
    Returns:
        Dictionnaire avec les informations du compte
    """
    try:
        params = {}
        if self.client_key:
            params['ClientKey'] = self.client_key
        
        # Récupérer les balances depuis l'API Saxo
        balance_data = self._make_request('GET', '/port/v1/balances', params=params)
        
        # Récupérer les infos du compte
        account_data = self._make_request('GET', '/port/v1/accounts', params=params)
        
        accounts = account_data.get('Data', [])
        primary_account = accounts[0] if accounts else {}
        
        return {
            'account_id': primary_account.get('AccountId'),
            'account_key': primary_account.get('AccountKey'),
            'currency': primary_account.get('Currency', 'EUR'),
            'balance': balance_data.get('TotalValue', 0),
            'cash_balance': balance_data.get('CashBalance', 0),
            'margin_available': balance_data.get('MarginAvailableForTrading', 0),
            'margin_used': balance_data.get('MarginUsedByCurrentPositions', 0),
            'unrealized_pnl': balance_data.get('UnrealizedProfitLoss', 0),
            'account_type': primary_account.get('AccountType'),
            'is_active': primary_account.get('Active', False),
        }
        
    except Exception as e:
        logger.error(f"Saxo get_account_info error: {e}")
        return {}
```

**Endpoints API Saxo utilisés** :
- `GET /port/v1/balances` : Récupère les balances (CashBalance, TotalValue, etc.)
- `GET /port/v1/accounts` : Récupère les informations du compte (Currency, AccountId, etc.)

#### Méthode `get_account_balance()`

Cette méthode formate les balances pour retourner un dictionnaire simple :

```python
def get_account_balance(self) -> Dict[str, Decimal]:
    """
    Get account balances.
    
    Returns:
        Dictionary mapping currency to balance
    """
    try:
        # Récupérer les informations du compte
        account_info = self.get_account_info()
        
        if not account_info:
            return {}
        
        # Extraire la devise et le solde
        currency = account_info.get('currency', 'EUR')
        cash_balance = account_info.get('cash_balance', 0)
        total_balance = account_info.get('balance', 0)
        
        # Formater les balances
        balances = {}
        
        # Solde en cash (devise principale)
        if cash_balance:
            balances[currency] = Decimal(str(cash_balance))
        
        # Solde total (si différent)
        if total_balance and total_balance != cash_balance:
            balances[f'{currency}_total'] = Decimal(str(total_balance))
        
        # Autres informations
        if account_info.get('margin_available'):
            balances[f'{currency}_margin_available'] = Decimal(str(account_info['margin_available']))
        
        return balances
        
    except Exception as e:
        logger.error(f"Saxo get_account_balance error: {e}")
        self._set_error(f"Get account balance error: {str(e)}")
        return {}
```

**Format de retour** :
```python
{
    'EUR': Decimal('1250.75'),           # Solde en cash (devise principale)
    'EUR_total': Decimal('1500.00'),     # Solde total (si différent)
    'EUR_margin_available': Decimal('500.00')  # Marge disponible
}
```

---

### 1.2 Service de Haut Niveau

**Fichier** : `backend/apps/trading/services/broker_service.py`

#### Méthode `get_account_balance()`

Cette méthode fournit une interface unifiée pour tous les brokers :

```python
def get_account_balance(self, broker_account: BrokerAccount) -> Dict[str, Decimal]:
    """
    Get account balance.
    
    Args:
        broker_account: BrokerAccount model instance
        
    Returns:
        Dictionary mapping currency to balance
    """
    try:
        # Récupérer les credentials pour logging
        credentials = self._get_credentials_from_account(broker_account)
        logger.info(f"Getting balance for account {broker_account.id} (type: {broker_account.broker_type})")
        
        # Créer une instance du broker
        broker = self.get_broker_instance(broker_account)
        
        # Authentifier
        if not broker.authenticate():
            logger.error(f"Authentication failed for account {broker_account.id}")
            return {}
        
        # Récupérer le solde
        return broker.get_account_balance()
        
    except Exception as e:
        logger.error(f"Error getting account balance: {e}", exc_info=True)
        return {}
```

**Utilisation** :
```python
from apps.trading.models.brokers import BrokerAccount
from apps.trading.services.broker_service import BrokerService

account = BrokerAccount.objects.get(id=1, broker_type='SAXO')
service = BrokerService(user=account.user)

balances = service.get_account_balance(account)
eur_balance = balances.get('EUR', Decimal('0'))
print(f"Solde EUR : {eur_balance} €")
```

---

### 1.3 Endpoint API REST

**Fichier** : `backend/apps/trading/api/views.py`

#### Action `refresh_balance()`

Cette action permet de rafraîchir et récupérer le solde via l'API REST :

```python
@action(detail=True, methods=['post'], url_path='refresh-balance')
def refresh_balance(self, request, pk=None):
    """
    POST /api/broker-accounts/{id}/refresh_balance/
    Rafraîchit la balance du compte et retourne le solde.
    """
    from django.utils import timezone
    from decimal import Decimal
    from ..services.broker_service import BrokerService
    import logging
    
    logger = logging.getLogger('trading.api.brokers')
    
    account = self.get_object()
    
    # Vérifier que c'est un compte Saxo
    if account.broker_type != 'SAXO':
        return Response({
            'success': False,
            'error': 'Cette méthode est uniquement pour Saxo Bank'
        }, status=400)
    
    service = BrokerService(request.user)
    
    try:
        # Récupérer toutes les balances
        balances = service.get_account_balance(account)
        
        # Extraire le solde de la devise principale (EUR généralement)
        currency = account.currency or 'EUR'
        eur_balance = balances.get(currency, balances.get('EUR', Decimal('0')))
        
        # Si pas de EUR, prendre la première balance disponible
        if eur_balance == 0 and balances:
            currency = list(balances.keys())[0]
            eur_balance = balances[currency]
        
        # Mettre à jour le modèle
        account.balance = eur_balance
        account.currency = currency
        account.balance_updated_at = timezone.now()
        account.save(update_fields=['balance', 'currency', 'balance_updated_at'])
        
        # Formater les balances (exclure les clés avec suffixe)
        all_balances = {
            k: float(v) 
            for k, v in balances.items() 
            if not k.endswith('_total') and not k.endswith('_margin_available')
        }
        
        return Response({
            'success': True,
            'balance_eur': float(eur_balance),
            'currency': currency,
            'all_balances': all_balances,
            'account': BrokerAccountSerializer(account).data
        })
    except Exception as e:
        logger.error(f"Error refreshing balance for account {account.id}: {e}")
        return Response({
            'success': False,
            'error': str(e),
            'balance_eur': 0.0
        }, status=500)
```

#### Action `balance_eur()` (Alternative)

Pour récupérer le solde sans mettre à jour la base de données :

```python
@action(detail=True, methods=['get'], url_path='balance-eur')
def balance_eur(self, request, pk=None):
    """
    GET /api/broker-accounts/{id}/balance_eur/
    Récupère le solde EUR actuel du compte sans mettre à jour la base de données.
    """
    from decimal import Decimal
    from ..services.broker_service import BrokerService
    from django.utils import timezone
    import logging
    
    logger = logging.getLogger('trading.api.brokers')
    
    account = self.get_object()
    
    if account.broker_type != 'SAXO':
        return Response({
            'success': False,
            'error': 'Cette méthode est uniquement pour Saxo Bank'
        }, status=400)
    
    service = BrokerService(request.user)
    
    try:
        # Récupérer toutes les balances
        balances = service.get_account_balance(account)
        
        # Extraire le solde EUR (ou la devise principale)
        currency = account.currency or 'EUR'
        eur_balance = balances.get(currency, balances.get('EUR', Decimal('0')))
        
        # Si pas de EUR, prendre la première balance disponible
        if eur_balance == 0 and balances:
            currency = list(balances.keys())[0]
            eur_balance = balances[currency]
        
        # Formater les balances
        all_balances = {
            k: float(v) 
            for k, v in balances.items() 
            if not k.endswith('_total') and not k.endswith('_margin_available')
        }
        
        return Response({
            'success': True,
            'balance_eur': float(eur_balance),
            'currency': currency,
            'all_balances': all_balances,
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting EUR balance for account {account.id}: {e}")
        return Response({
            'success': False,
            'error': str(e),
            'balance_eur': 0.0
        }, status=500)
```

**Endpoints disponibles** :
- `POST /api/broker-accounts/{id}/refresh-balance/` : Rafraîchit et sauvegarde le solde
- `GET /api/broker-accounts/{id}/balance-eur/` : Récupère le solde sans sauvegarder

---

## 🎨 Partie 2 : Frontend - Affichage du Solde

### 2.1 React/TypeScript (Recommandé)

#### Hook `useBrokerBalance`

**Fichier** : `frontend/src/hooks/useBrokerBalance.ts`

```typescript
import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../services/api';

interface BrokerBalance {
  balance_eur: number;
  currency: string;
  all_balances: Record<string, number>;
  timestamp?: string;
}

interface UseBrokerBalanceReturn {
  balanceEur: number | null;
  allBalances: Record<string, number> | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export const useBrokerBalance = (accountId: number | null): UseBrokerBalanceReturn => {
  const [balanceEur, setBalanceEur] = useState<number | null>(null);
  const [allBalances, setAllBalances] = useState<Record<string, number> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchBalance = useCallback(async () => {
    if (!accountId) {
      setBalanceEur(null);
      setAllBalances(null);
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.get<{ success: boolean } & BrokerBalance>(
        `/api/broker-accounts/${accountId}/balance-eur/`
      );
      
      if (response.data.success) {
        setBalanceEur(response.data.balance_eur);
        setAllBalances(response.data.all_balances);
      } else {
        setError('Erreur lors de la récupération du solde');
        setBalanceEur(0);
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.message || 'Erreur de connexion';
      setError(errorMessage);
      setBalanceEur(0);
      setAllBalances(null);
    } finally {
      setLoading(false);
    }
  }, [accountId]);

  useEffect(() => {
    fetchBalance();
  }, [fetchBalance]);

  return {
    balanceEur,
    allBalances,
    loading,
    error,
    refresh: fetchBalance
  };
};
```

#### Composant `BrokerCard`

**Fichier** : `frontend/src/components/brokers/BrokerCard.tsx`

```typescript
import React from 'react';
import { useBrokerBalance } from '../../hooks/useBrokerBalance';
import { BrokerAccount } from '../../types';

interface BrokerCardProps {
  account: BrokerAccount;
}

export const BrokerCard: React.FC<BrokerCardProps> = ({ account }) => {
  const { balanceEur, allBalances, loading, error, refresh } = useBrokerBalance(account.id);

  return (
    <div className="card mb-4">
      <div className="card-header d-flex justify-content-between align-items-center">
        <div>
          <h5 className="mb-0">
            <i className="fas fa-university me-2"></i>
            {account.name}
          </h5>
          <small className="text-muted">
            {account.broker.name} - {account.get_environment_display()}
          </small>
        </div>
        <button
          onClick={refresh}
          className="btn btn-sm btn-outline-primary"
          disabled={loading}
          title="Rafraîchir le solde"
        >
          <i className={`fas fa-sync-alt ${loading ? 'fa-spin' : ''}`}></i>
        </button>
      </div>
      
      <div className="card-body">
        <div className="mb-3">
          <strong>Solde EUR :</strong>
          {loading ? (
            <div className="spinner-border spinner-border-sm ms-2" role="status">
              <span className="visually-hidden">Chargement...</span>
            </div>
          ) : error ? (
            <span className="text-danger ms-2">
              <i className="fas fa-exclamation-triangle"></i> {error}
            </span>
          ) : (
            <span className="badge bg-success fs-5 ms-2">
              {balanceEur !== null ? `${balanceEur.toFixed(2)} €` : 'N/A'}
            </span>
          )}
        </div>

        {/* Afficher les autres devises si disponibles */}
        {allBalances && Object.keys(allBalances).length > 1 && (
          <details className="mt-2">
            <summary className="text-muted small cursor-pointer">
              <i className="fas fa-coins me-1"></i>
              Autres devises ({Object.keys(allBalances).length})
            </summary>
            <ul className="list-unstyled mt-2">
              {Object.entries(allBalances)
                .filter(([currency]) => currency !== 'EUR' && allBalances[currency] > 0)
                .map(([currency, amount]) => (
                  <li key={currency} className="d-flex justify-content-between">
                    <span>{currency}:</span>
                    <strong>{amount.toFixed(2)}</strong>
                  </li>
                ))}
            </ul>
          </details>
        )}

        <div className="mt-3">
          <small className="text-muted">
            <i className="fas fa-info-circle me-1"></i>
            Dernière mise à jour : {account.balance_updated_at 
              ? new Date(account.balance_updated_at).toLocaleString('fr-FR')
              : 'Jamais'}
          </small>
        </div>
      </div>
    </div>
  );
};
```

---

### 2.2 Templates Django (HTML)

#### Vue `broker_dashboard`

**Fichier** : `backend/apps/trading/views/brokers.py`

```python
@login_required
def broker_dashboard(request):
    """Tableau de bord des courtiers avec solde EUR"""
    from decimal import Decimal
    from ..models.brokers import BrokerAccount
    from ..services.broker_service import BrokerService
    import logging
    
    logger = logging.getLogger('trading.views.brokers')
    
    service = BrokerService(request.user)
    
    # Récupérer tous les comptes brokers de l'utilisateur
    broker_accounts = BrokerAccount.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('broker').order_by('name')
    
    # Récupérer les balances EUR pour chaque compte
    broker_balances_eur = {}
    for account in broker_accounts:
        try:
            # Récupérer toutes les balances
            balances = service.get_account_balance(account)
            
            # Pour Saxo, extraire le solde de la devise principale
            if account.broker_type == 'SAXO':
                currency = account.currency or 'EUR'
                eur_balance = balances.get(currency, balances.get('EUR', Decimal('0')))
                
                # Si pas de EUR, prendre la première balance disponible
                if eur_balance == 0 and balances:
                    currency = list(balances.keys())[0]
                    eur_balance = balances[currency]
            else:
                # Pour Binance, utiliser directement EUR
                eur_balance = balances.get('EUR', Decimal('0'))
                currency = 'EUR'
            
            # Formater les balances
            all_balances = {
                k: float(v) 
                for k, v in balances.items() 
                if not k.endswith('_total') and not k.endswith('_margin_available')
            }
            
            broker_balances_eur[account.id] = {
                'eur': float(eur_balance),
                'currency': currency,
                'all': all_balances
            }
            
            # Mettre à jour le modèle si nécessaire
            if account.balance != eur_balance:
                account.balance = eur_balance
                account.currency = currency
                account.save(update_fields=['balance', 'currency'])
                
        except Exception as e:
            logger.error(f"Error getting balance for account {account.id}: {e}")
            broker_balances_eur[account.id] = {
                'eur': 0.0,
                'currency': 'EUR',
                'all': {},
                'error': str(e)
            }
    
    return render(request, 'trading/broker_dashboard.html', {
        'broker_accounts': broker_accounts,
        'broker_balances_eur': broker_balances_eur,
    })
```

#### Template HTML

**Fichier** : `backend/apps/trading/templates/trading/broker_dashboard.html`

```html
{% load custom_tags %}

<div class="row">
    {% for account in broker_accounts %}
    <div class="col-md-6 mb-4">
        <div class="card h-100 shadow-sm">
            <div class="card-header d-flex justify-content-between align-items-center">
                <div>
                    <h5 class="mb-0">
                        <i class="fas fa-university me-2"></i>
                        {{ account.name }}
                    </h5>
                    <small class="text-muted">
                        {{ account.broker.name }} - {{ account.get_environment_display }}
                    </small>
                </div>
                <button class="btn btn-sm btn-outline-primary refresh-balance-btn" 
                        data-account-id="{{ account.id }}">
                    <i class="fas fa-sync-alt"></i>
                </button>
            </div>
            
            <div class="card-body">
                <div class="mb-3">
                    <strong>Solde EUR :</strong>
                    {% with balance=broker_balances_eur|dict_key:account.id %}
                        {% if balance.error %}
                            <span class="text-danger ms-2">
                                <i class="fas fa-exclamation-triangle"></i> 
                                Erreur: {{ balance.error }}
                            </span>
                        {% elif balance %}
                            <span class="badge bg-success fs-5 ms-2">
                                {{ balance.eur|floatformat:2 }} €
                            </span>
                        {% else %}
                            <span class="text-muted ms-2">Non disponible</span>
                        {% endif %}
                    {% endwith %}
                </div>

                <!-- Afficher les autres devises si disponibles -->
                {% with balance=broker_balances_eur|dict_key:account.id %}
                    {% if balance.all %}
                        <details class="mt-2">
                            <summary class="text-muted small cursor-pointer">
                                <i class="fas fa-coins me-1"></i>
                                Autres devises ({{ balance.all|length }})
                            </summary>
                            <ul class="list-unstyled mt-2">
                                {% for currency, amount in balance.all.items %}
                                    {% if currency != 'EUR' and amount > 0 %}
                                        <li class="d-flex justify-content-between">
                                            <span>{{ currency }}:</span>
                                            <strong>{{ amount|floatformat:2 }}</strong>
                                        </li>
                                    {% endif %}
                                {% endfor %}
                            </ul>
                        </details>
                    {% endif %}
                {% endwith %}

                <div class="mt-3">
                    <small class="text-muted">
                        <i class="fas fa-info-circle me-1"></i>
                        Dernière mise à jour : 
                        {% if account.balance_updated_at %}
                            {{ account.balance_updated_at|date:"d/m/Y H:i" }}
                        {% else %}
                            Jamais
                        {% endif %}
                    </small>
                </div>
            </div>
        </div>
    </div>
    {% endfor %}
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    // Rafraîchir le solde d'un compte
    document.querySelectorAll('.refresh-balance-btn').forEach(button => {
        button.addEventListener('click', function() {
            const accountId = this.dataset.accountId;
            const button = this;
            
            // Désactiver le bouton et afficher un spinner
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            
            // Appeler l'API
            fetch(`/api/broker-accounts/${accountId}/refresh-balance/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': '{{ csrf_token }}'
                },
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Recharger la page pour afficher le nouveau solde
                    location.reload();
                } else {
                    alert('Erreur lors du rafraîchissement: ' + (data.error || 'Erreur inconnue'));
                    button.disabled = false;
                    button.innerHTML = '<i class="fas fa-sync-alt"></i>';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Erreur de connexion lors du rafraîchissement');
                button.disabled = false;
                button.innerHTML = '<i class="fas fa-sync-alt"></i>';
            });
        });
    });
});
</script>
```

---

## 📊 Partie 3 : Format des Données

### 3.1 Structure de la Réponse API Saxo

L'API Saxo retourne les balances dans ce format :

```json
{
  "CashBalance": 1250.75,
  "TotalValue": 1500.00,
  "MarginAvailableForTrading": 500.00,
  "MarginUsedByCurrentPositions": 250.00,
  "UnrealizedProfitLoss": 50.00
}
```

### 3.2 Format Après Traitement

Après traitement par `get_account_balance()`, le format est :

```python
{
    'EUR': Decimal('1250.75'),                    # Solde en cash
    'EUR_total': Decimal('1500.00'),              # Solde total
    'EUR_margin_available': Decimal('500.00')     # Marge disponible
}
```

### 3.3 Format API REST

L'endpoint API retourne :

```json
{
  "success": true,
  "balance_eur": 1250.75,
  "currency": "EUR",
  "all_balances": {
    "EUR": 1250.75
  },
  "account": {
    "id": 1,
    "name": "Mon compte Saxo",
    "balance": "1250.75",
    "currency": "EUR",
    "balance_updated_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## 🔄 Partie 4 : Flux Complet

### 4.1 Diagramme de Flux

```
1. Utilisateur clique sur "Rafraîchir le solde"
   ↓
2. Frontend appelle POST /api/broker-accounts/{id}/refresh-balance/
   ↓
3. API appelle BrokerService.get_account_balance(account)
   ↓
4. BrokerService crée une instance SaxoBroker via BrokerFactory
   ↓
5. SaxoBroker.authenticate() vérifie/rafraîchit le token
   ↓
6. SaxoBroker.get_account_balance() appelle get_account_info()
   ↓
7. get_account_info() fait 2 requêtes API Saxo :
   - GET /port/v1/balances → CashBalance, TotalValue, etc.
   - GET /port/v1/accounts → Currency, AccountId, etc.
   ↓
8. Les données sont formatées dans get_account_balance()
   ↓
9. Le solde est sauvegardé dans BrokerAccount.balance
   ↓
10. La réponse JSON est retournée au frontend
   ↓
11. Le frontend affiche le solde mis à jour
```

### 4.2 Exemple de Code Complet

**Backend** :
```python
from apps.trading.models.brokers import BrokerAccount
from apps.trading.services.broker_service import BrokerService
from decimal import Decimal

# Récupérer le compte
account = BrokerAccount.objects.get(id=1, broker_type='SAXO')

# Créer le service
service = BrokerService(user=account.user)

# Récupérer le solde
balances = service.get_account_balance(account)

# Afficher
eur_balance = balances.get('EUR', Decimal('0'))
print(f"Solde EUR : {eur_balance} €")
```

**Frontend React** :
```typescript
import { useBrokerBalance } from '../../hooks/useBrokerBalance';

const BrokerCard = ({ account }) => {
  const { balanceEur, loading, error, refresh } = useBrokerBalance(account.id);

  return (
    <div>
      <p>Solde EUR : {balanceEur?.toFixed(2)} €</p>
      <button onClick={refresh}>Rafraîchir</button>
    </div>
  );
};
```

---

## ⚠️ Partie 5 : Gestion des Erreurs

### 5.1 Erreurs Courantes

#### Erreur : "Authentication failed"

**Cause** : Le token d'accès est expiré ou invalide.

**Solution** :
```python
# Le système devrait automatiquement rafraîchir le token
# Vérifier que refresh_token est valide dans BrokerAccount
```

#### Erreur : "Get account balance error"

**Cause** : Problème de connexion à l'API Saxo ou credentials invalides.

**Solution** :
1. Vérifier que les tokens sont valides
2. Vérifier la connexion réseau
3. Vérifier les logs : `logs/brokers.log`

#### Erreur : "No balance found"

**Cause** : Le compte n'a pas de solde ou la devise n'est pas EUR.

**Solution** :
```python
# Vérifier toutes les devises disponibles
balances = service.get_account_balance(account)
print(f"Toutes les balances : {balances}")
```

### 5.2 Logging

Les erreurs sont loggées dans :
- `logs/brokers.log` : Logs des brokers
- `logs/errors.log` : Erreurs critiques

---

## ✅ Checklist d'Implémentation

### Backend

- [ ] `SaxoBroker.get_account_info()` implémentée
- [ ] `SaxoBroker.get_account_balance()` implémentée
- [ ] `BrokerService.get_account_balance()` fonctionne
- [ ] Endpoint API `refresh_balance()` créé
- [ ] Endpoint API `balance_eur()` créé (optionnel)
- [ ] Tests unitaires écrits

### Frontend

- [ ] Hook `useBrokerBalance` créé
- [ ] Composant `BrokerCard` créé
- [ ] Service API `brokers.ts` avec les fonctions nécessaires
- [ ] Affichage du solde dans l'interface
- [ ] Bouton de rafraîchissement fonctionnel
- [ ] Gestion des erreurs implémentée

---

## 📚 Ressources

- **Documentation Saxo OpenAPI** : https://www.developer.saxo/openapi/learn
- **Endpoint Balances** : https://www.developer.saxo/openapi/learn/portfolios/balances
- **Endpoint Accounts** : https://www.developer.saxo/openapi/learn/portfolios/accounts
- **Guide OAuth2** : `docs/SAXO_OAUTH2_AND_BALANCE.md`
- **Fichiers de Connexion** : `docs/SAXO_CONNECTION_FILES.md`

---

## 🎯 Résumé

Pour afficher le solde Saxo :

1. **Backend** : Utiliser `BrokerService.get_account_balance()` qui appelle `SaxoBroker.get_account_balance()`
2. **API** : Exposer via l'endpoint `POST /api/broker-accounts/{id}/refresh-balance/`
3. **Frontend** : Utiliser le hook `useBrokerBalance` ou appeler directement l'API
4. **Affichage** : Afficher `balance_eur` dans l'interface utilisateur

Le système récupère automatiquement le solde depuis l'API Saxo (`/port/v1/balances`) et le formate pour l'affichage.

