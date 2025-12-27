"""
Commande pour créer les migrations après modification du modèle BrokerAccount.
Exécuter: python manage.py makemigrations trading
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Crée les migrations pour le modèle BrokerAccount mis à jour'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                '⚠️  Cette commande est un rappel.\n'
                'Exécutez plutôt: python manage.py makemigrations trading\n'
                'Puis: python manage.py migrate'
            )
        )

