# Exemples et Cas d'Usage - Système de Stratégies

## Exemples de Configuration

### 1. Stratégie Threshold Simple

**Objectif** : Acheter AAPL si prix < 150€, vendre si prix > 180€

**Configuration** :
```json
{
  "name": "AAPL Threshold Strategy",
  "asset": 1,
  "all_asset": 123,
  "broker_account": 5,
  "algorithm_type": "threshold",
  "parameters": {
    "threshold_low": 150.0,
    "threshold_high": 180.0,
    "order_size": 10.0,
    "stop_loss": 5.0
  },
  "execution_mode": "paper_trading",
  "check_frequency": 30,
  "target_min_quantity": 0,
  "target_max_quantity": 100
}
```

### 2. Stratégie RSI

**Objectif** : Acheter BTCUSDT si RSI < 30, vendre si RSI > 70

**Configuration** :
```json
{
  "name": "BTC RSI Strategy",
  "asset": 2,
  "all_asset": 456,
  "broker_account": 3,
  "algorithm_type": "rsi",
  "parameters": {
    "rsi_period": 14,
    "rsi_low": 30,
    "rsi_high": 70,
    "order_size": 0.1,
    "stop_loss": 3.0
  },
  "execution_mode": "simulation",
  "check_frequency": 15,
  "target_min_quantity": 0.5,
  "target_max_quantity": 2.0
}
```

### 3. Stratégie MA Crossover

**Objectif** : Détecter les croisements de moyennes mobiles

**Configuration** :
```json
{
  "name": "EURUSD MA Crossover",
  "asset": 3,
  "all_asset": 789,
  "broker_account": 5,
  "algorithm_type": "ma_crossover",
  "parameters": {
    "ma1_period": 20,
    "ma2_period": 50,
    "order_size": 10000,
    "stop_loss": 2.0
  },
  "execution_mode": "live_trading",
  "check_frequency": 60,
  "target_min_quantity": 0,
  "target_max_quantity": 50000
}
```

## Exemples de Requêtes API

### Créer une Stratégie

```bash
POST /api/strategies/
Content-Type: application/json

{
  "name": "My Strategy",
  "asset": 1,
  "all_asset": 123,
  "broker_account": 5,
  "algorithm_type": "threshold",
  "parameters": {
    "threshold_low": 100.0,
    "threshold_high": 200.0
  },
  "execution_mode": "paper_trading",
  "check_frequency": 45
}
```

### Exécuter une Stratégie

```bash
POST /api/strategies/1/execute/
```

**Réponse** :
```json
{
  "success": true,
  "signal": "BUY",
  "signal_strength": 0.85,
  "signal_reason": "Prix (95.50) en dessous du seuil bas (100.00)",
  "current_price": 95.50,
  "order_executed": true,
  "order": {
    "id": 123,
    "broker_order_id": "abc123",
    "status": "OPEN"
  }
}
```

### Calculer un Signal (Sans Exécuter)

```bash
POST /api/strategies/1/calculate-signal/
```

**Réponse** :
```json
{
  "signal": "BUY",
  "signal_strength": 0.85,
  "signal_reason": "Prix (95.50) en dessous du seuil bas (100.00)",
  "current_price": 95.50,
  "price_data_points": 100
}
```

### Historique d'Exécution

```bash
GET /api/strategies/1/executions/?limit=10
```

**Réponse** :
```json
{
  "count": 150,
  "results": [
    {
      "id": 456,
      "execution_time": "2025-12-31T10:30:00Z",
      "signal": "BUY",
      "signal_strength": 0.85,
      "current_price": 95.50,
      "order_executed": true,
      "order_size": 10.0
    }
  ]
}
```

## Workflow Complet

### 1. Création et Configuration

1. Accéder à `/strategies`
2. Cliquer sur "Créer une stratégie"
3. Remplir le formulaire :
   - Nom : "AAPL Threshold"
   - Asset : Sélectionner AAPL via autocomplétion
   - Algorithme : Threshold
   - Paramètres : Seuil bas 150, Seuil haut 180
   - Broker : Sélectionner un compte
   - Mode : Paper Trading
   - Fréquence : 30 minutes
4. Sauvegarder

### 2. Test en Simulation

1. Changer le mode en "Simulation"
2. Cliquer sur "Exécuter" manuellement
3. Vérifier le signal généré
4. Consulter l'historique

### 3. Activation

1. Activer la stratégie (bouton "Activer")
2. Configurer `is_automated=True` si exécution automatique souhaitée
3. La stratégie s'exécutera automatiquement selon `check_frequency`

### 4. Suivi

1. Consulter l'historique d'exécution
2. Vérifier les ordres passés
3. Analyser les performances
4. Ajuster les paramètres si nécessaire

## Cas d'Usage Avancés

### Stratégie avec Quantités Cibles

**Objectif** : Maintenir entre 50 et 150 actions d'AAPL

```json
{
  "target_min_quantity": 50,
  "target_max_quantity": 150,
  "parameters": {
    "threshold_low": 150.0,
    "threshold_high": 180.0,
    "order_size": 20.0
  }
}
```

Comportement :
- Si prix < 150€ et quantité < 150 : Acheter jusqu'à 150
- Si prix > 180€ et quantité > 50 : Vendre jusqu'à 50

### Stratégie Multi-Assets

Créer plusieurs stratégies avec le même algorithme mais pour des assets différents.

### Stratégie avec Stop Loss

Le paramètre `stop_loss` peut être utilisé pour gérer le risque, même si l'implémentation dépend de l'algorithme.

---

**Voir aussi** :
- [STRATEGIES_OVERVIEW.md](STRATEGIES_OVERVIEW.md) : Vue d'ensemble
- [STRATEGIES_API.md](STRATEGIES_API.md) : Documentation API complète

