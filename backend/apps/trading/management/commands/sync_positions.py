"""
Django management command to sync positions from brokers.

Usage:
    python manage.py sync_positions --broker saxo
    python manage.py sync_positions --account-id 1
    python manage.py sync_positions --all
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from apps.trading.models import BrokerAccount
from apps.trading.services.sync import PositionSyncService


class Command(BaseCommand):
    help = 'Synchronize positions from broker APIs to the database'
    
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
            '--all',
            action='store_true',
            help='Sync all active broker accounts'
        )
        parser.add_argument(
            '--no-close',
            action='store_true',
            help='Do not close positions missing from broker'
        )
    
    def handle(self, *args, **options):
        user_id = options.get('user_id')
        account_id = options.get('account_id')
        broker_type = options.get('broker')
        sync_all = options.get('all')
        close_missing = not options.get('no_close')
        
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
        
        self.stdout.write(f"Syncing positions for user: {user.username}")
        
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
        service = PositionSyncService(user)
        
        total_created = 0
        total_updated = 0
        total_closed = 0
        
        for account in accounts:
            self.stdout.write(
                f"\n{'='*50}\n"
                f"Syncing positions from {account.broker.name} ({account.account_id})\n"
                f"{'='*50}"
            )
            
            try:
                result = service.sync(
                    broker_account=account,
                    close_missing=close_missing,
                )
                
                if result.get('success'):
                    created = result.get('created', 0)
                    updated = result.get('updated', 0)
                    closed = result.get('closed', 0)
                    
                    total_created += created
                    total_updated += updated
                    total_closed += closed
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Success: {created} created, {updated} updated, {closed} closed"
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
            f"Total closed: {total_closed}\n"
        )

