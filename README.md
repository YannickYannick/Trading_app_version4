# Trading_app_version4

Application de trading avec backend Django et frontend React.

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

