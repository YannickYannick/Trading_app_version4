"""
Django management command to sync asset prices.

Usage:
    python manage.py sync_prices --broker saxo
    python manage.py sync_prices --yahoo --symbols AAPL,GOOGL,MSFT
    python manage.py sync_prices --all
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from apps.trading.models import BrokerAccount, Asset
from apps.trading.services.sync import PriceSyncService
from apps.trading.services.data_providers import YahooFinanceService
from apps.trading.utils.user_utils import get_user_or_error


class Command(BaseCommand):
    help = 'Synchronize asset prices from brokers or Yahoo Finance'
    
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
            '--yahoo',
            action='store_true',
            help='Use Yahoo Finance instead of broker API'
        )
        parser.add_argument(
            '--symbols',
            type=str,
            help='Comma-separated list of symbols to sync'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Sync prices for all assets in database'
        )
    
    def handle(self, *args, **options):
        user_id = options.get('user_id')
        account_id = options.get('account_id')
        broker_type = options.get('broker')
        use_yahoo = options.get('yahoo')
        symbols_str = options.get('symbols')
        sync_all = options.get('all')
        
        # Parse symbols
        symbols = None
        if symbols_str:
            symbols = [s.strip().upper() for s in symbols_str.split(',')]
        
        # Use Yahoo Finance
        if use_yahoo:
            self._sync_from_yahoo(symbols, sync_all)
            return
        
        # Get user
        if user_id:
            user = get_user_or_error(user_id)
        else:
            user = User.objects.first()
            if not user:
                raise CommandError("No users found in the database")
        
        self.stdout.write(f"Syncing prices for user: {user.username}")
        
        # Get broker accounts
        if account_id:
            accounts = BrokerAccount.objects.filter(id=account_id, user=user)
        elif broker_type:
            accounts = BrokerAccount.objects.filter(
                user=user,
                broker__broker_type__iexact=broker_type,
                is_active=True
            )
        else:
            raise CommandError("Please specify --account-id, --broker, or --yahoo")
        
        if not accounts.exists():
            raise CommandError("No matching broker accounts found")
        
        # Initialize service
        service = PriceSyncService(user)
        
        total_updated = 0
        
        for account in accounts:
            self.stdout.write(
                f"\n{'='*50}\n"
                f"Syncing prices from {account.broker.name} ({account.account_id})\n"
                f"{'='*50}"
            )
            
            try:
                result = service.sync_current_prices(
                    broker_account=account,
                    symbols=symbols,
                )
                
                if result.get('success'):
                    updated = result.get('updated', 0)
                    total_updated += updated
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Success: {updated} prices updated"
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
            f"Total prices updated: {total_updated}\n"
        )
    
    def _sync_from_yahoo(self, symbols, sync_all):
        """Sync prices from Yahoo Finance."""
        self.stdout.write("Syncing prices from Yahoo Finance...")
        
        service = YahooFinanceService()
        
        if not service.is_available:
            raise CommandError("yfinance package is not installed")
        
        # Get assets to update
        if symbols:
            assets = Asset.objects.filter(symbol__in=symbols)
        elif sync_all:
            assets = Asset.objects.all()
        else:
            raise CommandError("Please specify --symbols or --all with --yahoo")
        
        assets = list(assets)
        
        if not assets:
            raise CommandError("No matching assets found")
        
        self.stdout.write(f"Updating prices for {len(assets)} assets...")
        
        result = service.update_all_prices(assets)
        
        if result.get('success'):
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Updated {result.get('updated', 0)} of {result.get('total', 0)} prices"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"❌ Failed: {result.get('message', 'Unknown error')}"
                )
            )

