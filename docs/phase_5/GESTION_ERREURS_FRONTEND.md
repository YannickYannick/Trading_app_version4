# ⚠️ Gestion d'Erreurs Frontend

Ce guide explique comment implémenter une gestion d'erreurs complète et cohérente dans le frontend React/TypeScript.

---

## 📋 Vue d'ensemble

La gestion d'erreurs frontend doit couvrir :
1. **Erreurs réseau** : Connexion, timeout, CORS
2. **Erreurs HTTP** : 400, 401, 403, 404, 500
3. **Erreurs de validation** : Données invalides
4. **Erreurs métier** : Erreurs spécifiques à l'application
5. **Affichage utilisateur** : Messages clairs et actions possibles

---

## 🔧 Configuration de Base

### 1. Intercepteur Axios pour les Erreurs

**Fichier** : `frontend/src/services/api.ts`

```typescript
import axios, { AxiosError } from 'axios';

// Intercepteur pour gérer les erreurs
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    // Erreur réseau (pas de réponse du serveur)
    if (!error.response) {
      return Promise.reject({
        type: 'network',
        message: 'Erreur de connexion. Vérifiez votre connexion internet.',
        originalError: error,
      });
    }

    const status = error.response.status;
    const data = error.response.data as any;

    // 401 Unauthorized - Token expiré
    if (status === 401) {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/jwt/refresh/`, {
            refresh: refreshToken,
          });
          localStorage.setItem('access_token', response.data.access);
          // Réessayer la requête originale
          error.config!.headers.Authorization = `Bearer ${response.data.access}`;
          return apiClient.request(error.config!);
        } catch (refreshError) {
          // Refresh échoué, rediriger vers login
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
          return Promise.reject({
            type: 'auth',
            message: 'Session expirée. Veuillez vous reconnecter.',
            originalError: error,
          });
        }
      }
    }

    // Formater l'erreur selon le type
    const formattedError = {
      type: getErrorType(status),
      status,
      message: getErrorMessage(data, status),
      details: data,
      originalError: error,
    };

    return Promise.reject(formattedError);
  }
);

// Fonction pour déterminer le type d'erreur
function getErrorType(status: number): string {
  if (status >= 400 && status < 500) {
    return 'client';
  } else if (status >= 500) {
    return 'server';
  }
  return 'unknown';
}

// Fonction pour obtenir un message d'erreur lisible
function getErrorMessage(data: any, status: number): string {
  // Message personnalisé de l'API
  if (data?.error) {
    return data.error;
  }
  if (data?.detail) {
    return data.detail;
  }
  if (data?.message) {
    return data.message;
  }

  // Messages par défaut selon le code HTTP
  const defaultMessages: Record<number, string> = {
    400: 'Requête invalide. Vérifiez les données saisies.',
    401: 'Non autorisé. Veuillez vous connecter.',
    403: 'Accès refusé. Vous n\'avez pas les permissions nécessaires.',
    404: 'Ressource non trouvée.',
    500: 'Erreur serveur. Veuillez réessayer plus tard.',
    502: 'Service temporairement indisponible.',
    503: 'Service en maintenance.',
  };

  return defaultMessages[status] || 'Une erreur est survenue.';
}
```

---

## 🎨 Composants d'Affichage d'Erreurs

### 1. Composant ErrorMessage

**Fichier** : `frontend/src/components/common/ErrorMessage.tsx`

```typescript
import React from 'react';

interface ErrorMessageProps {
  error: any;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({
  error,
  onRetry,
  onDismiss,
}) => {
  if (!error) return null;

  const getErrorIcon = () => {
    switch (error.type) {
      case 'network':
        return 'fa-wifi';
      case 'auth':
        return 'fa-lock';
      case 'client':
        return 'fa-exclamation-triangle';
      case 'server':
        return 'fa-server';
      default:
        return 'fa-exclamation-circle';
    }
  };

  const getErrorClass = () => {
    switch (error.type) {
      case 'network':
        return 'alert-warning';
      case 'auth':
        return 'alert-danger';
      case 'client':
        return 'alert-warning';
      case 'server':
        return 'alert-danger';
      default:
        return 'alert-secondary';
    }
  };

  return (
    <div className={`alert ${getErrorClass()} alert-dismissible fade show`} role="alert">
      <i className={`fas ${getErrorIcon()} me-2`}></i>
      <strong>Erreur :</strong> {error.message || 'Une erreur est survenue'}
      
      {error.details && (
        <details className="mt-2">
          <summary className="small">Détails techniques</summary>
          <pre className="small mt-2 mb-0">
            {JSON.stringify(error.details, null, 2)}
          </pre>
        </details>
      )}

      <div className="mt-2">
        {onRetry && (
          <button
            className="btn btn-sm btn-outline-primary me-2"
            onClick={onRetry}
          >
            <i className="fas fa-redo me-1"></i>
            Réessayer
          </button>
        )}
        {onDismiss && (
          <button
            type="button"
            className="btn-close"
            onClick={onDismiss}
            aria-label="Close"
          ></button>
        )}
      </div>
    </div>
  );
};
```

### 2. Composant ErrorBoundary

**Fichier** : `frontend/src/components/common/ErrorBoundary.tsx`

```typescript
import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    // Envoyer l'erreur à un service de logging
    // logErrorToService(error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="container mt-5">
          <div className="alert alert-danger" role="alert">
            <h4 className="alert-heading">
              <i className="fas fa-exclamation-triangle me-2"></i>
              Une erreur est survenue
            </h4>
            <p>
              Désolé, une erreur inattendue s'est produite. Veuillez rafraîchir la page.
            </p>
            <hr />
            <details>
              <summary className="small">Détails de l'erreur</summary>
              <pre className="small mt-2 mb-0">
                {this.state.error?.toString()}
              </pre>
            </details>
            <button
              className="btn btn-primary mt-3"
              onClick={() => window.location.reload()}
            >
              <i className="fas fa-redo me-2"></i>
              Rafraîchir la page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
```

---

## 🎣 Hooks Personnalisés pour les Erreurs

### 1. Hook useErrorHandler

**Fichier** : `frontend/src/hooks/useErrorHandler.ts`

```typescript
import { useState, useCallback } from 'react';

interface ErrorState {
  error: any | null;
  hasError: boolean;
}

export const useErrorHandler = () => {
  const [errorState, setErrorState] = useState<ErrorState>({
    error: null,
    hasError: false,
  });

  const handleError = useCallback((error: any) => {
    console.error('Error caught:', error);
    setErrorState({
      error,
      hasError: true,
    });
  }, []);

  const clearError = useCallback(() => {
    setErrorState({
      error: null,
      hasError: false,
    });
  }, []);

  return {
    error: errorState.error,
    hasError: errorState.hasError,
    handleError,
    clearError,
  };
};
```

### 2. Hook useAsyncOperation

**Fichier** : `frontend/src/hooks/useAsyncOperation.ts`

```typescript
import { useState, useCallback } from 'react';

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: any | null;
}

export const useAsyncOperation = <T,>() => {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const execute = useCallback(async (operation: () => Promise<T>) => {
    setState({ data: null, loading: true, error: null });

    try {
      const data = await operation();
      setState({ data, loading: false, error: null });
      return { success: true, data };
    } catch (error: any) {
      setState({ data: null, loading: false, error });
      return { success: false, error };
    }
  }, []);

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null });
  }, []);

  return {
    ...state,
    execute,
    reset,
  };
};
```

**Utilisation** :
```typescript
const MyComponent = () => {
  const { data, loading, error, execute } = useAsyncOperation<BrokerAccount[]>();

  const loadData = async () => {
    await execute(async () => {
      const response = await apiClient.get('/broker-accounts/');
      return response.data.results;
    });
  };

  return (
    <div>
      {error && <ErrorMessage error={error} onRetry={loadData} />}
      {loading && <div>Chargement...</div>}
      {data && <div>{/* Afficher les données */}</div>}
    </div>
  );
};
```

---

## 📝 Exemples d'Utilisation

### 1. Gestion d'Erreurs dans un Formulaire

```typescript
const BrokerForm = () => {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const { execute, loading, error } = useAsyncOperation();

  const handleSubmit = async (data: any) => {
    const result = await execute(async () => {
      return await apiClient.post('/broker-accounts/', data);
    });

    if (!result.success) {
      // Gérer les erreurs de validation
      if (result.error?.details) {
        const validationErrors: Record<string, string> = {};
        Object.entries(result.error.details).forEach(([field, messages]: [string, any]) => {
          validationErrors[field] = Array.isArray(messages) ? messages[0] : messages;
        });
        setErrors(validationErrors);
      }
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {error && <ErrorMessage error={error} />}
      {/* Champs du formulaire avec affichage des erreurs */}
    </form>
  );
};
```

### 2. Gestion d'Erreurs dans une Liste

```typescript
const BrokerList = () => {
  const { data, loading, error, execute, reset } = useAsyncOperation<BrokerAccount[]>();

  useEffect(() => {
    execute(async () => {
      const response = await apiClient.get('/broker-accounts/');
      return response.data.results;
    });
  }, [execute]);

  if (error) {
    return (
      <ErrorMessage
        error={error}
        onRetry={() => {
          reset();
          execute(async () => {
            const response = await apiClient.get('/broker-accounts/');
            return response.data.results;
          });
        }}
      />
    );
  }

  if (loading) {
    return <div>Chargement...</div>;
  }

  return (
    <div>
      {data?.map(account => (
        <BrokerCard key={account.id} account={account} />
      ))}
    </div>
  );
};
```

---

## ✅ Checklist de Validation

### Configuration

- [ ] Intercepteur axios configuré pour les erreurs
- [ ] Messages d'erreur par défaut définis
- [ ] Gestion du refresh token automatique
- [ ] Redirection vers login si token expiré

### Composants

- [ ] Composant `ErrorMessage` créé
- [ ] Composant `ErrorBoundary` créé
- [ ] Hooks personnalisés créés (`useErrorHandler`, `useAsyncOperation`)
- [ ] Affichage des erreurs dans tous les composants

### Types d'Erreurs

- [ ] Erreurs réseau gérées
- [ ] Erreurs HTTP (400, 401, 403, 404, 500) gérées
- [ ] Erreurs de validation gérées
- [ ] Erreurs métier gérées

### Expérience Utilisateur

- [ ] Messages d'erreur clairs et compréhensibles
- [ ] Actions possibles affichées (réessayer, annuler)
- [ ] Loading states pendant les requêtes
- [ ] Pas de crash de l'application

---

## 🧪 Tests

### Test des Erreurs

```typescript
describe('Error Handling', () => {
  it('should handle network errors', async () => {
    // Simuler une erreur réseau
    const error = { type: 'network', message: 'Connection failed' };
    // Vérifier que le message est affiché
  });

  it('should handle 401 errors', async () => {
    // Simuler une erreur 401
    // Vérifier que le refresh token est tenté
    // Vérifier la redirection vers login si échec
  });

  it('should handle validation errors', async () => {
    // Simuler une erreur 400 avec détails
    // Vérifier que les erreurs de validation sont affichées
  });
});
```

---

## 📚 Ressources

- **Gestion d'Erreurs Backend** : `docs/phase_3/GESTION_ERREURS_EXPLANATION.md`
- **React Error Boundaries** : https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary
- **Axios Interceptors** : https://axios-http.com/docs/interceptors

---

## 🎯 Résultat Attendu

Après validation :
- ✅ Toutes les erreurs sont gérées
- ✅ Les messages sont clairs pour l'utilisateur
- ✅ Les actions possibles sont affichées
- ✅ L'application ne crash jamais
- ✅ L'expérience utilisateur est fluide même en cas d'erreur

