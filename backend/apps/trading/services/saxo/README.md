# Coûts de transaction Saxo

Service backend pour estimer les commissions **avant** un ordre et récupérer les
frais **réellement facturés** après exécution.

## Endpoints utilisés

| Usage | Route |
|---|---|
| Illustration pré-trade | `GET /cs/v1/tradingconditions/cost/{AccountKey}/{Uic}/{AssetType}` |
| Precheck d'ordre | `POST /trade/v2/orders/precheck` |
| Conditions + marge | `GET /cs/v1/tradingconditions/instrument/{AccountKey}/{Uic}/{AssetType}` |
| Coûts réels | `GET /cs/v1/reports/trades/{ClientKey}` |
| Relevé officiel | `GET /cr/v1/reports/TradesExecuted/{ClientKey}` |

`infoprices` ne donne **pas** les commissions. Les barèmes SIM et LIVE sont
différents : rien n'est hardcodé.

## Token

Les credentials viennent de `BrokerAccount` (OAuth2 déjà géré par l'app) :

- `saxo_access_token` / `saxo_refresh_token`
- `saxo_environment` = `live` ou `simulation`

Le client HTTP rafraîchit le token sur `401` et retente les `429` / `5xx`.

Pour un token SIM 24h (dev) : [Get 24 Hour Token](https://www.developer.saxo/openapi/token).
Ne jamais commiter de token ni d'`AccountKey`.

## Commande de rattrapage

```bash
cd backend
python manage.py sync_saxo_costs --from 2026-08-01 --to 2026-08-24
python manage.py sync_saxo_costs --from 2026-08-01 --to 2026-08-24 --dry-run
```

Idempotent : upsert `(trade, source)` ou `(saxo_trade_id, source)`. Les trades
non matchés sont loggés, jamais devinés.

## Tests

```bash
cd backend
python manage.py test apps.trading.tests.test_services.test_saxo_costs
```
