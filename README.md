# Trading_app_version4

Application de trading avec backend Django et frontend React.

## Documentation

- [Guide de démarrage](docs/guides/README_DEMARRAGE.md)
- [Dépannage](docs/guides/TROUBLESHOOTING.md)
- [Déploiement](docs/deployment/) — guides et rapports d’hébergement
- [Brokers (migrations / correctifs)](docs/brokers/)
- [Index doc backend (phases, stack)](docs/backend/INDEX.md)
- [IA — Suggestions de diversification (Orders)](docs/AI_DIVERSIFY_ORDERS.md)

## Fonctionnalités
- Trading multi-brokers (Saxo Bank, Binance)
- Gestion de portefeuille (positions, trades, stratégies)
- Données macroéconomiques
- Bot IA assistant

## Installation

```bash
# Créer l'environnement virtuel
python -m venv venv
.\venv\Scripts\Activate.ps1

# Installer les dépendances
cd backend
pip install -r requirements.txt

# Appliquer les migrations
python manage.py migrate

# Lancer le serveur
python manage.py runserver
```

