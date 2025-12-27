# 💶 Affichage du Solde EUR Binance sur la Page Brokers

## 📋 Vue d'ensemble

Ce guide explique comment afficher le montant en euros (EUR) que vous avez sur Binance directement sur la page des brokers.

---

## 🔍 Fonctions disponibles

### 1. Fonction principale : `BinanceBroker.get_account_balance()`

**Fichier** : `backend/apps/trading/brokers/binance.py` (ligne 706)

**Description** : Récupère toutes les balances du compte Binance (EUR, USD, BTC, etc.)

**Retour** : Dictionnaire `Dict[str, Decimal]` avec toutes les devises

**Exemple de retour** :
```python
{
    'EUR': Decimal('100.50'),
    'USD': Decimal('200.00'),
    'BTC': Decimal('0.5'),
    'EUR_free': Decimal('100.00'),
    'EUR_locked': Decimal('0.50'),
    # ... autres devises
}
```

**Code** :
```python
def get_account_balance(self) -> Dict[str, Decimal]:
    """Get account balances."""
    try:
        response = self._make_request('GET', '/api/v3/account', signed=True)
        
        if not response:
            return {}
        
        balances = {}
        for balance in response.get('balances', []):
            asset = balance.get('asset', '')
            free = Decimal(balance.get('free', '0'))
            locked = Decimal(balance.get('locked', '0'))
            total = free + locked
            
            if total > 0:
                balances[asset] = total
                balances[f'{asset}_free'] = free
                balances[f'{asset}_locked'] = locked
        
        return balances
        
    except Exception as e:
        self._set_error(f"Get account balance error: {str(e)}")
        return {}
```

---

### 2. Service : `BrokerService.get_account_balance()`

**Fichier** : `backend/apps/trading/services/broker_service.py` (ligne 547)

**Description** : Méthode de service qui appelle le broker et retourne les balances

**Utilisation** :
```python
from apps.trading.services.broker_service import BrokerService
from apps.trading.models.brokers import BrokerAccount

service = BrokerService(request.user)
account = BrokerAccount.objects.get(id=1)

balances = service.get_account_balance(account)
eur_balance = balances.get('EUR', Decimal('0'))
```

**Code** :
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
        broker = self.get_broker_instance(broker_account)
        
        if not broker.authenticate():
            return {}
        
        return broker.get_account_balance()
        
    except Exception as e:
        logger.error(f"Error getting account balance: {e}")
        return {}
```

---

## 🎯 Solutions d'implémentation

### Solution 1 : API REST (Recommandé pour React/TypeScript)

#### Étape 1 : Compléter l'endpoint API `refresh_balance`

**Fichier** : `backend/apps/trading/api/views.py`

**Localisation** : Dans la classe `BrokerAccountViewSet`, méthode `refresh_balance` (ligne 700)

**Code à remplacer** :
```python
@action(detail=True, methods=['post'], url_path='refresh-balance')
def refresh_balance(self, request, pk=None):
    """
    POST /api/broker-accounts/1/refresh_balance/
    Rafraîchit la balance du compte et retourne le solde EUR.
    """
    from django.utils import timezone
    from decimal import Decimal
    from ..services.broker_service import BrokerService
    import logging
    
    logger = logging.getLogger('trading.api.brokers')
    
    account = self.get_object()
    service = BrokerService(request.user)
    
    try:
        # Récupérer toutes les balances
        balances = service.get_account_balance(account)
        
        # Extraire le solde EUR
        eur_balance = balances.get('EUR', Decimal('0'))
        
        # Mettre à jour le modèle
        account.balance = eur_balance
        account.currency = 'EUR'
        account.balance_updated_at = timezone.now()
        account.save(update_fields=['balance', 'currency', 'balance_updated_at'])
        
        # Formater les balances (exclure les clés _free et _locked)
        all_balances = {
            k: float(v) 
            for k, v in balances.items() 
            if not k.endswith('_free') and not k.endswith('_locked')
        }
        
        return Response({
            'success': True,
            'balance_eur': float(eur_balance),
            'currency': 'EUR',
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

#### Étape 2 : Ajouter une action pour récupérer le solde EUR uniquement

**Fichier** : `backend/apps/trading/api/views.py`

**Localisation** : Dans la classe `BrokerAccountViewSet`, après la méthode `refresh_balance`

**Code à ajouter** :
```python
@action(detail=True, methods=['get'], url_path='balance-eur')
def balance_eur(self, request, pk=None):
    """
    GET /api/broker-accounts/1/balance_eur/
    Récupère le solde EUR actuel du compte sans mettre à jour la base de données.
    """
    from decimal import Decimal
    from ..services.broker_service import BrokerService
    import logging
    
    logger = logging.getLogger('trading.api.brokers')
    
    account = self.get_object()
    service = BrokerService(request.user)
    
    try:
        # Récupérer toutes les balances
        balances = service.get_account_balance(account)
        
        # Extraire le solde EUR
        eur_balance = balances.get('EUR', Decimal('0'))
        
        # Formater les balances (exclure les clés _free et _locked)
        all_balances = {
            k: float(v) 
            for k, v in balances.items() 
            if not k.endswith('_free') and not k.endswith('_locked')
        }
        
        return Response({
            'success': True,
            'balance_eur': float(eur_balance),
            'currency': 'EUR',
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

#### Étape 3 : Utiliser depuis React/TypeScript

**Fichier** : `frontend/src/hooks/useBrokerBalance.ts` (à créer)

**Code** :
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
        `/api/broker-accounts/${accountId}/balance_eur/`
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

**Fichier** : `frontend/src/components/brokers/BrokerCard.tsx` (exemple d'utilisation)

**Code** :
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

### Solution 2 : Vue Django classique (Templates HTML)

#### Étape 1 : Modifier la vue `broker_dashboard`

**Fichier** : `backend/apps/trading/views/brokers.py` (ou `views.py` selon votre structure)

**Code** :
```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from decimal import Decimal
import logging

from ..models.brokers import BrokerAccount
from ..services.broker_service import BrokerService

logger = logging.getLogger('trading.views.brokers')

@login_required
def broker_dashboard(request):
    """Tableau de bord des courtiers avec solde EUR"""
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
            
            # Extraire le solde EUR
            eur_balance = balances.get('EUR', Decimal('0'))
            
            # Formater les balances (exclure les clés _free et _locked)
            all_balances = {
                k: float(v) 
                for k, v in balances.items() 
                if not k.endswith('_free') and not k.endswith('_locked')
            }
            
            broker_balances_eur[account.id] = {
                'eur': float(eur_balance),
                'all': all_balances
            }
            
            # Mettre à jour le modèle si nécessaire
            if account.balance != eur_balance:
                account.balance = eur_balance
                account.currency = 'EUR'
                account.save(update_fields=['balance', 'currency'])
                
        except Exception as e:
            logger.error(f"Error getting balance for account {account.id}: {e}")
            broker_balances_eur[account.id] = {
                'eur': 0.0,
                'all': {},
                'error': str(e)
            }
    
    return render(request, 'trading/broker_dashboard.html', {
        'broker_accounts': broker_accounts,
        'broker_balances_eur': broker_balances_eur,
    })
```

#### Étape 2 : Modifier le template `broker_dashboard.html`

**Fichier** : `backend/apps/trading/templates/trading/broker_dashboard.html`

**Code à ajouter/modifier dans la section des brokers** :
```html
{% load custom_tags %}

<!-- Liste des courtiers -->
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
                <div class="dropdown">
                    <button class="btn btn-sm btn-outline-secondary dropdown-toggle" 
                            type="button" 
                            data-bs-toggle="dropdown">
                        <i class="fas fa-ellipsis-v"></i>
                    </button>
                    <ul class="dropdown-menu">
                        <li>
                            <a class="dropdown-item" href="{% url 'broker_config_edit' account.id %}">
                                <i class="fas fa-edit"></i> Modifier
                            </a>
                        </li>
                        <li>
                            <button class="dropdown-item refresh-balance-btn" 
                                    data-account-id="{{ account.id }}">
                                <i class="fas fa-sync-alt"></i> Rafraîchir le solde
                            </button>
                        </li>
                    </ul>
                </div>
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
    {% empty %}
    <div class="col-12">
        <div class="alert alert-info">
            <i class="fas fa-info-circle me-2"></i>
            Aucun compte broker configuré. 
            <a href="{% url 'broker_config' %}" class="alert-link">Ajoutez-en un maintenant</a>.
        </div>
    </div>
    {% endfor %}
</div>

<!-- Script pour rafraîchir le solde via AJAX -->
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Rafraîchir le solde d'un compte
    document.querySelectorAll('.refresh-balance-btn').forEach(button => {
        button.addEventListener('click', function() {
            const accountId = this.dataset.accountId;
            const button = this;
            
            // Désactiver le bouton et afficher un spinner
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Rafraîchissement...';
            
            // Appeler l'API
            fetch(`/api/broker-accounts/${accountId}/refresh_balance/`, {
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
                    button.innerHTML = '<i class="fas fa-sync-alt"></i> Rafraîchir le solde';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Erreur de connexion lors du rafraîchissement');
                button.disabled = false;
                button.innerHTML = '<i class="fas fa-sync-alt"></i> Rafraîchir le solde';
            });
        });
    });
});
</script>
```

---

## 🔧 Configuration des URLs

### Pour l'API REST

**Fichier** : `backend/apps/trading/api/urls.py`

Les URLs sont déjà configurées via le router DRF. Les endpoints seront :
- `POST /api/broker-accounts/{id}/refresh_balance/` → Rafraîchit et sauvegarde le solde
- `GET /api/broker-accounts/{id}/balance_eur/` → Récupère le solde EUR sans sauvegarder

### Pour les vues Django classiques

**Fichier** : `backend/apps/trading/urls.py`

Assurez-vous que l'URL est configurée :
```python
from django.urls import path
from .views import brokers

urlpatterns = [
    path('brokers/', brokers.broker_dashboard, name='broker_dashboard'),
    # ... autres URLs
]
```

---

## 📊 Exemple de réponse API

### GET `/api/broker-accounts/1/balance_eur/`

**Réponse réussie** :
```json
{
  "success": true,
  "balance_eur": 1250.75,
  "currency": "EUR",
  "all_balances": {
    "EUR": 1250.75,
    "USD": 500.00,
    "BTC": 0.05
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Réponse en cas d'erreur** :
```json
{
  "success": false,
  "error": "Authentication failed",
  "balance_eur": 0.0
}
```

### POST `/api/broker-accounts/1/refresh_balance/`

**Réponse réussie** :
```json
{
  "success": true,
  "balance_eur": 1250.75,
  "currency": "EUR",
  "all_balances": {
    "EUR": 1250.75,
    "USD": 500.00,
    "BTC": 0.05
  },
  "account": {
    "id": 1,
    "name": "Mon compte Binance",
    "balance": "1250.75",
    "currency": "EUR",
    "balance_updated_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## ✅ Checklist d'implémentation

### Pour l'API REST (React/TypeScript)

- [ ] Compléter la méthode `refresh_balance` dans `BrokerAccountViewSet`
- [ ] Ajouter la méthode `balance_eur` dans `BrokerAccountViewSet`
- [ ] Créer le hook `useBrokerBalance.ts`
- [ ] Créer ou modifier le composant `BrokerCard.tsx`
- [ ] Tester l'endpoint API avec Postman ou curl
- [ ] Intégrer le composant dans la page brokers
- [ ] Tester le rafraîchissement automatique et manuel

### Pour les vues Django classiques (Templates HTML)

- [ ] Modifier la vue `broker_dashboard` pour récupérer les balances
- [ ] Modifier le template `broker_dashboard.html` pour afficher le solde EUR
- [ ] Ajouter le script JavaScript pour le rafraîchissement AJAX
- [ ] Tester l'affichage des balances
- [ ] Tester le bouton de rafraîchissement

---

## 🐛 Dépannage

### Problème : Le solde EUR est toujours à 0

**Causes possibles** :
1. Vous n'avez pas d'EUR sur votre compte Binance
2. Les credentials API ne sont pas corrects
3. L'authentification échoue

**Solutions** :
1. Vérifier votre compte Binance pour voir si vous avez des EUR
2. Vérifier les credentials dans `BrokerAccount`
3. Tester la connexion avec `test_connection`
4. Vérifier les logs : `logs/brokers.log` et `logs/errors.log`

### Problème : Erreur "Authentication failed"

**Solutions** :
1. Vérifier que les tokens/credentials sont valides
2. Pour Binance : Vérifier que l'API Key a les permissions de lecture
3. Pour Saxo : Vérifier que le token n'est pas expiré

### Problème : Le rafraîchissement ne fonctionne pas

**Solutions** :
1. Vérifier que l'URL de l'API est correcte
2. Vérifier les permissions CORS si vous utilisez React
3. Vérifier les logs du serveur Django
4. Vérifier la console JavaScript du navigateur

---

## 📚 Ressources

- **Modèle BrokerAccount** : `backend/apps/trading/models/brokers.py`
- **Service Broker** : `backend/apps/trading/services/broker_service.py`
- **Broker Binance** : `backend/apps/trading/brokers/binance.py`
- **API Views** : `backend/apps/trading/api/views.py`
- **Documentation Binance API** : https://binance-docs.github.io/apidocs/spot/en/#account-information-user_data

---

## 🎯 Résultat attendu

Après implémentation :
- ✅ Le solde EUR s'affiche sur la page brokers
- ✅ Le solde se rafraîchit automatiquement au chargement
- ✅ Un bouton permet de rafraîchir manuellement
- ✅ Les autres devises sont affichées dans un détail pliable
- ✅ Les erreurs sont gérées et affichées clairement

