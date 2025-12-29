"""
Django management command to test Binance trades sync.

Usage:
    python manage.py test_binance_trades --account-id 2
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from apps.trading.models import BrokerAccount
from apps.trading.services.sync.trade_sync_service import TradeSyncService
from apps.trading.utils.user_utils import get_broker_account_or_error


class Command(BaseCommand):
    help = 'Test Binance trades synchronization'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--account-id',
            type=int,
            required=True,
            help='Broker account ID to test'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of trades to fetch'
        )
    
    def handle(self, *args, **options):
        account_id = options['account_id']
        limit = options['limit']
        
        account = get_broker_account_or_error(account_id)
        
        if account.get_broker_type().upper() != 'BINANCE':
            raise CommandError(f"Account {account_id} is not a Binance account (type: {account.get_broker_type()})")
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Testing Binance trades sync for account {account_id}")
        self.stdout.write(f"{'='*60}\n")
        self.stdout.write(f"Broker: {account.broker.name}")
        self.stdout.write(f"Account ID: {account.account_id}")
        self.stdout.write(f"User: {account.user.username}\n")
        
        # Create service
        service = TradeSyncService(account.user)
        
        # Test sync
        try:
            self.stdout.write("Starting trade sync...")
            result = service.sync(
                broker_account=account,
                limit=limit,
            )
            
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write("SYNC RESULTS")
            self.stdout.write(f"{'='*60}")
            
            if result.get('success'):
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Success: {result.get('created', 0)} created, "
                        f"{result.get('updated', 0)} updated, "
                        f"{result.get('skipped', 0)} skipped"
                    )
                )
                
                if result.get('errors'):
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️ {len(result['errors'])} errors occurred"
                        )
                    )
                    for error in result['errors'][:5]:  # Show first 5 errors
                        self.stdout.write(f"  - {error}")
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ Failed: {result.get('message', 'Unknown error')}"
                    )
                )
            
            self.stdout.write(f"\nDuration: {result.get('duration_ms', 0)}ms")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error during sync: {e}")
            )
            import traceback
            self.stdout.write(traceback.format_exc())

