"""
Management command to test synchronization with registered brokers.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.trading.models import BrokerAccount
from apps.trading.services.sync.position_sync_service import PositionSyncService
from apps.trading.services.sync.trade_sync_service import TradeSyncService
import logging

logger = logging.getLogger('trading.management.test_sync')


class Command(BaseCommand):
    help = 'Test synchronization of positions and trades with registered brokers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID to test with (default: first user)',
        )
        parser.add_argument(
            '--broker-account-id',
            type=int,
            help='Specific broker account ID to test (default: all active accounts)',
        )
        parser.add_argument(
            '--test-positions',
            action='store_true',
            help='Test position synchronization',
        )
        parser.add_argument(
            '--test-trades',
            action='store_true',
            help='Test trade synchronization',
        )

    def handle(self, *args, **options):
        # Get user
        user_id = options.get('user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User with ID {user_id} not found'))
                return
        else:
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR('No users found in database'))
                return
        
        self.stdout.write(self.style.SUCCESS(f'Testing with user: {user.username} (ID: {user.id})'))
        
        # Get broker accounts
        broker_account_id = options.get('broker_account_id')
        if broker_account_id:
            try:
                accounts = [BrokerAccount.objects.get(id=broker_account_id, user=user, is_active=True)]
            except BrokerAccount.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Broker account with ID {broker_account_id} not found or inactive'))
                return
        else:
            accounts = BrokerAccount.objects.filter(user=user, is_active=True)
            if not accounts.exists():
                self.stdout.write(self.style.ERROR('No active broker accounts found'))
                return
        
        self.stdout.write(self.style.SUCCESS(f'Found {accounts.count()} active broker account(s)'))
        
        # Test positions
        if options.get('test_positions') or (not options.get('test_positions') and not options.get('test_trades')):
            self.stdout.write(self.style.WARNING('\n=== Testing Position Synchronization ==='))
            for account in accounts:
                self.test_positions(user, account)
        
        # Test trades
        if options.get('test_trades') or (not options.get('test_positions') and not options.get('test_trades')):
            self.stdout.write(self.style.WARNING('\n=== Testing Trade Synchronization ==='))
            for account in accounts:
                self.test_trades(user, account)
    
    def test_positions(self, user, account):
        """Test position synchronization for a broker account."""
        self.stdout.write(f'\nTesting positions for: {account.name} ({account.get_broker_type()})')
        
        try:
            service = PositionSyncService(user)
            result = service.sync(account, close_missing=True)
            
            if result.get('success'):
                self.stdout.write(self.style.SUCCESS(
                    f"✓ Success: {result.get('created', 0)} created, "
                    f"{result.get('updated', 0)} updated, "
                    f"{result.get('closed', 0)} closed"
                ))
                if result.get('errors'):
                    self.stdout.write(self.style.WARNING(f"  Warnings: {len(result['errors'])} errors"))
            else:
                self.stdout.write(self.style.ERROR(f"✗ Failed: {result.get('message', 'Unknown error')}"))
                if result.get('errors'):
                    for error in result['errors'][:5]:  # Show first 5 errors
                        self.stdout.write(self.style.ERROR(f"  - {error}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Exception: {str(e)}"))
            logger.exception(f"Error testing positions for account {account.id}")
    
    def test_trades(self, user, account):
        """Test trade synchronization for a broker account."""
        self.stdout.write(f'\nTesting trades for: {account.name} ({account.get_broker_type()})')
        
        try:
            service = TradeSyncService(user)
            result = service.sync(account, limit=100)
            
            if result.get('success'):
                self.stdout.write(self.style.SUCCESS(
                    f"✓ Success: {result.get('created', 0)} created, "
                    f"{result.get('updated', 0)} updated"
                ))
                if result.get('errors'):
                    self.stdout.write(self.style.WARNING(f"  Warnings: {len(result['errors'])} errors"))
            else:
                self.stdout.write(self.style.ERROR(f"✗ Failed: {result.get('message', 'Unknown error')}"))
                if result.get('errors'):
                    for error in result['errors'][:5]:  # Show first 5 errors
                        self.stdout.write(self.style.ERROR(f"  - {error}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Exception: {str(e)}"))
            logger.exception(f"Error testing trades for account {account.id}")

