"""
Commande Django pour migrer les comptes Saxo de SIM vers LIVE.

Usage:
    python manage.py migrate_saxo_to_live [--dry-run] [--force]

Options:
    --dry-run: Affiche ce qui sera modifié sans faire de changement
    --force: Force la migration même si le compte a déjà 'live'
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.trading.models import BrokerAccount


class Command(BaseCommand):
    help = 'Migre tous les comptes Saxo de SIM vers LIVE'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche ce qui sera modifié sans faire de changement',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force la migration même si le compte a déjà environment=live',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']

        self.stdout.write(self.style.SUCCESS('\n=== Migration Saxo SIM → LIVE ===\n'))

        # Trouver tous les comptes Saxo
        saxo_accounts = BrokerAccount.objects.filter(broker__broker_type='SAXO')

        if not saxo_accounts.exists():
            self.stdout.write(self.style.WARNING('Aucun compte Saxo trouvé.'))
            return

        self.stdout.write(f'Comptes Saxo trouvés : {saxo_accounts.count()}\n')

        accounts_to_update = []
        
        for account in saxo_accounts:
            updates = []
            
            # Vérifier environment
            if account.environment != 'live' or force:
                updates.append(f"environment: '{account.environment}' → 'live'")
            
            # Vérifier saxo_environment
            if account.saxo_environment != 'live' or force:
                updates.append(f"saxo_environment: '{account.saxo_environment}' → 'live'")
            
            # Vérifier api_base_url sur le Broker associé si présent
            if hasattr(account, 'broker') and account.broker and hasattr(account.broker, 'api_base_url'):
                broker_url = account.broker.api_base_url
                if broker_url and 'sim/openapi' in broker_url:
                    new_url = broker_url.replace('sim/openapi', 'openapi')
                    updates.append(f"broker.api_base_url: '{broker_url}' → '{new_url}'")
            
            if updates:
                accounts_to_update.append({
                    'account': account,
                    'updates': updates
                })

        if not accounts_to_update:
            self.stdout.write(self.style.SUCCESS('Aucun compte à migrer. Tous sont déjà en LIVE.'))
            return

        # Afficher les modifications prévues
        self.stdout.write(self.style.WARNING('Modifications prévues :\n'))
        for item in accounts_to_update:
            account = item['account']
            self.stdout.write(f"  📋 Compte: {account.name} (ID: {account.id})")
            self.stdout.write(f"     User: {account.user.username}")
            for update in item['updates']:
                self.stdout.write(f"     • {update}")
            self.stdout.write()

        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  MODE DRY-RUN - Aucune modification effectuée'))
            return

        # Demander confirmation
        self.stdout.write(self.style.WARNING(f'\n⚠️  {len(accounts_to_update)} compte(s) seront modifiés.'))
        confirm = input('Continuer ? (yes/no): ').strip().lower()
        
        if confirm not in ['yes', 'y', 'o', 'oui']:
            self.stdout.write(self.style.ERROR('Migration annulée.'))
            return

        # Effectuer les modifications
        updated_count = 0
        with transaction.atomic():
            for item in accounts_to_update:
                account = item['account']
                
                # Mettre à jour environment
                if account.environment != 'live' or force:
                    account.environment = 'live'
                
                # Mettre à jour saxo_environment
                if account.saxo_environment != 'live' or force:
                    account.saxo_environment = 'live'
                
                # Mettre à jour api_base_url sur le Broker associé si nécessaire
                if hasattr(account, 'broker') and account.broker and hasattr(account.broker, 'api_base_url'):
                    if account.broker.api_base_url and 'sim/openapi' in account.broker.api_base_url:
                        account.broker.api_base_url = account.broker.api_base_url.replace('sim/openapi', 'openapi')
                        account.broker.save()
                
                account.save()
                updated_count += 1
                
                self.stdout.write(self.style.SUCCESS(
                    f'✅ Compte {account.name} (ID: {account.id}) migré vers LIVE'
                ))

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Migration terminée : {updated_count} compte(s) modifié(s)'
        ))
        
        self.stdout.write(self.style.WARNING(
            '\n⚠️  IMPORTANT: '
            'N\'oubliez pas de :\n'
            '  1. Vérifier que les credentials (CLIENT_ID, CLIENT_SECRET) sont ceux du compte LIVE\n'
            '  2. Régénérer un token OAuth2 avec le compte LIVE\n'
            '  3. Tester la récupération de prix pour vérifier que tout fonctionne\n'
        ))

