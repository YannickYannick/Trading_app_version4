# 📁 Liste des Fichiers pour la Connexion Saxo Bank

Ce document liste tous les fichiers nécessaires pour se connecter à Saxo Bank dans le projet.

---

## 🔧 1. Fichiers Principaux (Core)

### Broker Implementation
- **`backend/apps/trading/brokers/saxo.py`**
  - Classe `SaxoBroker` qui implémente l'interface `BrokerBase`
  - Gère l'authentification OAuth2
  - Méthodes principales :
    - `get_authorization_url()` : Génère l'URL d'authentification OAuth2
    - `exchange_code_for_token()` : Échange le code OAuth2 contre des tokens
    - `authenticate()` : Authentifie avec les tokens existants
    - `_refresh_token()` : Rafraîchit le token d'accès
    - `is_authenticated()` : Vérifie si le token est valide

### Base Classes
- **`backend/apps/trading/brokers/base.py`**
  - Classe abstraite `BrokerBase` (interface commune pour tous les brokers)
  - Exceptions : `BrokerAuthenticationError`, `BrokerAPIError`, `BrokerRateLimitError`
  - Définit les méthodes que tous les brokers doivent implémenter

### Factory Pattern
- **`backend/apps/trading/brokers/factory.py`**
  - `BrokerFactory.create_broker()` : Crée des instances de broker
  - Enregistre les brokers supportés (Saxo, Binance)
  - Méthode : `create_broker('saxo', user, credentials)`

---

## 🗄️ 2. Modèles de Données (Models)

- **`backend/apps/trading/models/brokers.py`**
  - **`Broker`** : Modèle pour les brokers supportés
    - Champs : `name`, `broker_type`, `is_active`, etc.
  - **`BrokerAccount`** : Compte utilisateur chez un broker
    - Champs spécifiques Saxo :
      - `saxo_client_id` : ID client OAuth2
      - `saxo_client_secret` : Secret client OAuth2
      - `saxo_redirect_uri` : URI de redirection OAuth2
      - `saxo_access_token` : Token d'accès
      - `saxo_refresh_token` : Token de rafraîchissement
      - `saxo_token_expires_at` : Date d'expiration du token
      - `saxo_environment` : Environnement (live/simulation)
  - **`BrokerSyncLog`** : Logs de synchronisation avec les brokers

---

## 🔌 3. Services (Business Logic)

- **`backend/apps/trading/services/broker_service.py`**
  - **`BrokerService`** : Service de haut niveau pour les opérations de broker
  - Méthodes principales :
    - `get_broker_instance()` : Crée et retourne une instance de broker
    - `get_account_balance()` : Récupère le solde du compte
    - `test_connection()` : Teste la connexion au broker
    - `sync_assets_to_db()` : Synchronise les assets depuis le broker
    - `sync_positions_to_db()` : Synchronise les positions depuis le broker
  - Gère la création et l'utilisation des instances de broker

---

## 🌐 4. API REST (Endpoints)

### ViewSets
- **`backend/apps/trading/api/views.py`**
  - **`BrokerAccountViewSet`** : ViewSet pour les comptes brokers
  - Actions personnalisées :
    - `test_connection()` : Tester la connexion à un broker
    - `refresh_balance()` : Rafraîchir le solde du compte
    - `saxo_auth_url()` : Obtenir l'URL d'authentification Saxo (si implémentée)
    - `exchange_code()` : Échanger le code OAuth2 contre des tokens (si implémentée)

### Serializers
- **`backend/apps/trading/api/serializers.py`**
  - **`BrokerAccountSerializer`** : Sérialise les données du compte broker
  - Inclut tous les champs Saxo pour l'API REST
  - Gère la validation et la transformation des données

### URLs
- **`backend/apps/trading/api/urls.py`**
  - Routes API pour les brokers
  - Endpoints générés automatiquement :
    - `GET /api/broker-accounts/` : Liste tous les comptes brokers
    - `POST /api/broker-accounts/` : Crée un nouveau compte broker
    - `GET /api/broker-accounts/{id}/` : Détails d'un compte broker
    - `PUT /api/broker-accounts/{id}/` : Met à jour un compte broker
    - `DELETE /api/broker-accounts/{id}/` : Supprime un compte broker
  - Endpoints personnalisés :
    - `POST /api/broker-accounts/{id}/test-connection/` : Tester la connexion
    - `POST /api/broker-accounts/{id}/refresh-balance/` : Rafraîchir le solde

---

## 🎨 5. Frontend React/TypeScript

### Composants
- **`frontend/src/components/brokers/BrokerForm.tsx`**
  - Formulaire de configuration d'un compte broker
  - Gère les champs spécifiques Saxo (Client ID, Secret, Redirect URI)
  - Validation des données avant soumission

- **`frontend/src/components/brokers/SaxoOAuthModal.tsx`**
  - Modal pour l'authentification OAuth2 Saxo
  - Gère le flux OAuth2 complet :
    - Affichage de l'URL d'authentification
    - Redirection vers Saxo Bank
    - Gestion du callback avec le code
    - Échange du code contre des tokens

- **`frontend/src/components/brokers/SaxoOAuthModal.css`**
  - Styles pour le modal OAuth2
  - Design responsive et moderne

### Pages
- **`frontend/src/pages/Brokers.tsx`**
  - Page principale de gestion des brokers
  - Affiche la liste des comptes brokers
  - Permet la création, modification et suppression de comptes
  - Intègre le modal OAuth2 pour Saxo

### Services API
- **`frontend/src/services/brokers.ts`**
  - Fonctions pour appeler l'API backend
  - Fonctions principales :
    - `getBrokerAccounts()` : Récupère tous les comptes brokers
    - `createBrokerAccount()` : Crée un nouveau compte
    - `updateBrokerAccount()` : Met à jour un compte
    - `deleteBrokerAccount()` : Supprime un compte
    - `testConnection()` : Teste la connexion
    - `getSaxoAuthUrl()` : Obtient l'URL d'authentification Saxo
    - `exchangeSaxoCode()` : Échange le code OAuth2

### Hooks
- **`frontend/src/hooks/useBrokers.ts`**
  - Hook React personnalisé pour gérer les brokers
  - Gère le state et les appels API
  - Fournit des fonctions pour CRUD sur les brokers

### Types
- **`frontend/src/types/index.ts`**
  - Types TypeScript pour les brokers
  - Interfaces :
    - `BrokerAccount` : Structure d'un compte broker
    - `Broker` : Structure d'un broker
    - `SaxoCredentials` : Credentials spécifiques Saxo

---

## ⚙️ 6. Commandes de Gestion (Management Commands)

- **`backend/apps/trading/management/commands/refresh_saxo_tokens.py`** (si existe)
  - Commande Django pour rafraîchir automatiquement les tokens Saxo
  - Usage : `python manage.py refresh_saxo_tokens`
  - Peut être exécutée via un cron job

- **`backend/apps/trading/management/commands/create_default_brokers.py`**
  - Crée les brokers par défaut (Saxo, Binance) dans la base de données
  - Usage : `python manage.py create_default_brokers`

---

## 📝 7. Documentation

- **`docs/SAXO_OAUTH2_AND_BALANCE.md`**
  - Guide complet pour l'authentification OAuth2 avec Saxo Bank
  - Étapes détaillées pour obtenir les tokens
  - Exemples de code pour chaque étape
  - Guide pour afficher le solde EUR

- **`BROKERS_CONNECTION_FIX.md`**
  - Guide de correction des problèmes de connexion
  - Solutions aux erreurs courantes
  - Checklist de débogage

---

## 🔐 8. Exceptions

- **`backend/apps/trading/exceptions/broker_exceptions.py`**
  - Exceptions spécifiques aux brokers
  - Classes :
    - `BrokerAuthenticationError` : Erreur d'authentification
    - `BrokerAPIError` : Erreur API
    - `BrokerRateLimitError` : Limite de taux dépassée

- **`backend/apps/trading/exceptions/base.py`**
  - Exceptions de base
  - Classe parente pour toutes les exceptions du projet

---

## 🧪 9. Tests

- **`backend/apps/trading/tests/test_brokers/test_saxo_broker.py`**
  - Tests unitaires pour `SaxoBroker`
  - Tests d'authentification
  - Tests de rafraîchissement de tokens
  - Tests de récupération de données

- **`backend/apps/trading/tests/test_services/test_broker_service.py`**
  - Tests pour `BrokerService`
  - Tests de création d'instances de broker
  - Tests de gestion des erreurs
  - Tests de synchronisation

---

## 📊 10. Admin Django

- **`backend/apps/trading/admin.py`**
  - Interface d'administration Django pour les modèles
  - Enregistre `Broker` et `BrokerAccount`
  - Permet de gérer les comptes brokers depuis l'admin Django
  - Utile pour le débogage et la gestion manuelle

---

## 🔄 Flux de Connexion (Ordre d'Utilisation)

### 1. Configuration Initiale
1. **`models/brokers.py`** : Créer un `BrokerAccount` avec les credentials Saxo
2. **`admin.py`** ou formulaire web : Saisir Client ID, Secret, Redirect URI

### 2. Obtention de l'URL d'Authentification
1. **`brokers/saxo.py`** : `get_authorization_url()` génère l'URL
2. **`api/views.py`** : Endpoint pour obtenir l'URL
3. **`frontend/SaxoOAuthModal.tsx`** : Affiche l'URL à l'utilisateur

### 3. Échange du Code OAuth2
1. **`brokers/saxo.py`** : `exchange_code_for_token()` échange le code
2. **`api/views.py`** : Endpoint pour échanger le code
3. **`models/brokers.py`** : Sauvegarde les tokens dans `BrokerAccount`

### 4. Authentification Automatique
1. **`brokers/saxo.py`** : `authenticate()` et `_refresh_token()` gèrent l'auth
2. **`services/broker_service.py`** : `get_broker_instance()` crée et authentifie le broker

### 5. Utilisation
1. **`brokers/saxo.py`** : Méthodes pour récupérer données, passer ordres, etc.
2. **`services/broker_service.py`** : Méthodes de haut niveau pour utiliser le broker

---

## 📌 Fichiers Essentiels (À Connaître en Priorité)

### Top 5 des Fichiers les Plus Importants

1. **`backend/apps/trading/brokers/saxo.py`**
   - ⭐ **LE FICHIER PRINCIPAL**
   - Implémentation complète de la connexion Saxo
   - Toutes les méthodes d'authentification OAuth2

2. **`backend/apps/trading/models/brokers.py`**
   - ⭐ **MODÈLES DE DONNÉES**
   - Structure des données (BrokerAccount, tokens, etc.)
   - Méthode `get_credentials_dict()` pour extraire les credentials

3. **`backend/apps/trading/services/broker_service.py`**
   - ⭐ **SERVICE DE HAUT NIVEAU**
   - Interface unifiée pour utiliser les brokers
   - Gère la création et l'authentification automatique

4. **`backend/apps/trading/api/views.py`**
   - ⭐ **ENDPOINTS API**
   - Expose les fonctionnalités via l'API REST
   - Actions personnalisées pour OAuth2

5. **`frontend/src/components/brokers/SaxoOAuthModal.tsx`**
   - ⭐ **INTERFACE UTILISATEUR**
   - Gère le flux OAuth2 côté frontend
   - Expérience utilisateur pour la connexion

---

## 🔍 Recherche Rapide

### Pour modifier l'authentification OAuth2
→ `backend/apps/trading/brokers/saxo.py`

### Pour modifier les champs de données
→ `backend/apps/trading/models/brokers.py`

### Pour ajouter un endpoint API
→ `backend/apps/trading/api/views.py`

### Pour modifier l'interface utilisateur
→ `frontend/src/components/brokers/SaxoOAuthModal.tsx`

### Pour modifier la logique métier
→ `backend/apps/trading/services/broker_service.py`

---

## 📚 Ressources Complémentaires

- **Documentation Saxo OpenAPI** : https://www.developer.saxo/openapi/learn
- **Portail Développeur Saxo** :
  - Simulation : https://www.developer.saxo/openapi/sim
  - Live : https://www.developer.saxo/openapi/trade
- **Guide OAuth2** : `docs/SAXO_OAUTH2_AND_BALANCE.md`
- **Guide de Correction** : `BROKERS_CONNECTION_FIX.md`

---

## ✅ Checklist de Vérification

Avant de se connecter à Saxo Bank, vérifier que ces fichiers existent :

- [ ] `backend/apps/trading/brokers/saxo.py` existe et contient `SaxoBroker`
- [ ] `backend/apps/trading/models/brokers.py` contient `BrokerAccount` avec les champs Saxo
- [ ] `backend/apps/trading/services/broker_service.py` contient `BrokerService`
- [ ] `backend/apps/trading/api/views.py` contient `BrokerAccountViewSet`
- [ ] `backend/apps/trading/api/urls.py` enregistre les routes des brokers
- [ ] `frontend/src/components/brokers/SaxoOAuthModal.tsx` existe (si frontend React)
- [ ] `frontend/src/services/brokers.ts` contient les fonctions API (si frontend React)

---

## 🎯 Résumé

**Total de fichiers** : ~15-20 fichiers principaux

**Catégories** :
- **Core** : 3 fichiers (saxo.py, base.py, factory.py)
- **Models** : 1 fichier (brokers.py)
- **Services** : 1 fichier (broker_service.py)
- **API** : 3 fichiers (views.py, serializers.py, urls.py)
- **Frontend** : 5-6 fichiers (composants, pages, services, hooks, types)
- **Tests** : 2 fichiers (test_saxo_broker.py, test_broker_service.py)
- **Admin** : 1 fichier (admin.py)
- **Documentation** : 2 fichiers (guides .md)

Ces fichiers couvrent l'ensemble du processus de connexion à Saxo Bank, de la configuration initiale à l'utilisation quotidienne.

