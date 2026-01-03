#!/bin/bash
# Script de déploiement automatique v4

echo "=========================================="
echo "      DEPLOIEMENT TRADING APP V4"
echo "=========================================="

# Charger les variables d'environnement si .env existe
if [ -f .env ]; then
    # Exporter les variables en ignorant les commentaires et les lignes vides
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
fi

echo "1. Installation des dépendances..."
pip install -r requirements.txt

echo "2. Configuration de la base de données..."
# On force le mode production_test pour les vérifications
export DJANGO_SETTINGS_MODULE=config_django.settings.production_test

# S'assurer que les migrations sont à jour
python manage.py migrate --noinput

echo "3. Application des fichiers statiques..."
python manage.py collectstatic --noinput

echo "4. Vérification de la configuration..."
python manage.py check --deploy

echo "=========================================="
echo "      PRÊT POUR LE DÉMARRAGE"
echo "=========================================="
echo "Pour lancer le serveur :"
echo "export DJANGO_SETTINGS_MODULE=config_django.settings.production_test"
echo "gunicorn --config gunicorn.conf.py config_django.wsgi:application"
echo ""
echo "Ou si vous êtes sur Windows (Waitress) :"
echo "waitress-serve --listen=127.0.0.1:8000 config_django.wsgi:application"
