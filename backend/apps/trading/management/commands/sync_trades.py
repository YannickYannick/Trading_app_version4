"""
Django management command to sync trade history from brokers.

Usage:
    python manage.py sync_trades --broker saxo --limit 100
    python manage.py sync_trades --account-id 1 --days 7
    python manage.py sync_trades --all
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from apps.trading.models import BrokerAccount
from apps.trading.services.sync import TradeSyncService
from apps.trading.utils.user_utils import get_user_or_error


class Command(BaseCommand):
    help = 'Synchronize trade history from broker APIs to the database'
    
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
            '--symbol',
            type=str,
            help='Only sync trades for this symbol'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of trades to sync per account'
        )
        parser.add_argument(
            '--days',
            type=int,
            help='Only sync trades from the last N days'
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
        symbol = options.get('symbol')
        limit = options.get('limit')
        days = options.get('days')
        sync_all = options.get('all')
        
        # Get user
        if user_id:
            user = get_user_or_error(user_id)
        else:
            user = User.objects.first()
            if not user:
                raise CommandError("No users found in the database")
        
        self.stdout.write(f"Syncing trades for user: {user.username}")
        
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
        service = TradeSyncService(user)
        
        total_created = 0
        total_skipped = 0
        
        for account in accounts:
            self.stdout.write(
                f"\n{'='*50}\n"
                f"Syncing trades from {account.broker.name} ({account.account_id})\n"
                f"{'='*50}"
            )
            
            try:
                result = service.sync(
                    broker_account=account,
                    limit=limit,
                    symbol=symbol,
                    since_days=days,
                )
                
                if result.get('success'):
                    created = result.get('created', 0)
                    skipped = result.get('skipped', 0)
                    
                    total_created += created
                    total_skipped += skipped
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Success: {created} created, {skipped} already exist"
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
            f"Total skipped (duplicates): {total_skipped}\n"
        )

