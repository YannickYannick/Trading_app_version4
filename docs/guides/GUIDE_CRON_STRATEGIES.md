# Cron — exécution automatique des stratégies

Les stratégies avec `is_active=True` et `is_automated=True` sont évaluées
périodiquement. La fréquence par stratégie est `check_frequency` (minutes).

En mode `live_trading`, un signal BUY/SELL place un ordre broker.
En `simulation` / `paper_trading`, seuls les signaux sont enregistrés.

## Commande

```bash
cd backend
python manage.py execute_automated_strategies
python manage.py execute_automated_strategies --dry-run
python manage.py execute_automated_strategies --force
python manage.py execute_automated_strategies --ids 12,34
```

## Cron HostArmada (exemple toutes les 5 min)

```cron
*/5 * * * * source /home/lebaffc1/virtualenv/Trading_app_version4/backend/3.12/bin/activate && cd /home/lebaffc1/Trading_app_version4/backend && python manage.py execute_automated_strategies >> /home/lebaffc1/logs/cron_strategies.log 2>&1
```

Prérequis : tokens Saxo à jour (voir `backend/docs/runbooks/GUIDE_CRON_SAXO_TOKENS.md`)
et historique de prix JSONB rempli (`sync_all_asset_prices` / sync Yahoo).

## UI

Page **Stratégies** : activer le robot (`is_automated`) et choisir le mode
d'exécution. Sans cron, l'exécution reste manuelle via le bouton Exécuter.
