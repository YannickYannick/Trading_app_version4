"""
Django management command to sync assets from brokers.

Usage:
    python manage.py sync_assets --broker saxo --limit 500
    python manage.py sync_assets --account-id 1
    python manage.py sync_assets --all
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from apps.trading.models import BrokerAccount
from apps.trading.services.sync import AssetSyncService


class Command(BaseCommand):
    help = 'Synchronize assets from broker APIs to the database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID to sync for'
        )
        parser.add_argument(
            '--account-id',
            type=int,
            help='Broker account ID to sync from'
        )
        parser.add_argument(
            '--broker',
            type=str,
            choices=['saxo', 'binance'],
            help='Broker type to sync'
        )
        parser.add_argument(
            '--asset-type',
            type=str,
            default='Stock',
            help='Asset type to sync (Stock, ETF, Crypto, etc.)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=1000,
            help='Maximum number of assets to sync'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Sync all active broker accounts'
        )
    
    def handle(self, *args, **options):
        user_id = options.get('user_id')
        account_id = options.get('account_id')
        broker_type = options.get('broker')
        asset_type = options.get('asset_type')
        limit = options.get('limit')
        sync_all = options.get('all')
        
        # Get user
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise CommandError(f"User with ID {user_id} not found")
        else:
            user = User.objects.first()
            if not user:
                raise CommandError("No users found in the database")
        
        self.stdout.write(f"Syncing assets for user: {user.username}")
        
        # Get broker accounts
        if account_id:
            accounts = BrokerAccount.objects.filter(id=account_id, user=user)
        elif broker_type:
            accounts = BrokerAccount.objects.filter(
                user=user,
                broker__broker_type__iexact=broker_type,
                is_active=True
            )
        elif sync_all:
            accounts = BrokerAccount.objects.filter(
                user=user,
                is_active=True
            )
        else:
            raise CommandError("Please specify --account-id, --broker, or --all")
        
        if not accounts.exists():
            raise CommandError("No matching broker accounts found")
        
        # Initialize service
        service = AssetSyncService(user)
        
        total_created = 0
        total_updated = 0
        
        for account in accounts:
            self.stdout.write(
                f"\n{'='*50}\n"
                f"Syncing from {account.broker.name} ({account.account_id})\n"
                f"{'='*50}"
            )
            
            try:
                result = service.sync_assets(
                    broker_account=account,
                    asset_type=asset_type,
                    limit=limit,
                )
                
                if result.get('success'):
                    created = result.get('created', 0)
                    updated = result.get('updated', 0)
                    total_created += created
                    total_updated += updated
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Success: {created} created, {updated} updated"
                        )
                    )
                    
                    if result.get('errors'):
                        self.stdout.write(
                            self.style.WARNING(
                                f"⚠️ {len(result['errors'])} errors occurred"
                            )
                        )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"❌ Failed: {result.get('message', 'Unknown error')}"
                        )
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Error: {str(e)}")
                )
        
        # Summary
        self.stdout.write(
            f"\n{'='*50}\n"
            f"SUMMARY\n"
            f"{'='*50}\n"
            f"Total created: {total_created}\n"
            f"Total updated: {total_updated}\n"
        )

