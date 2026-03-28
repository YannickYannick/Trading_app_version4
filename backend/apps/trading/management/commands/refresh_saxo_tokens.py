"""
Management command to refresh Saxo broker access tokens.
This command should be run periodically (every 20 minutes) via cron.
"""
from django.core.management.base import BaseCommand
from apps.trading.models import Broker
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Refresh Saxo broker access tokens before they expire'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force refresh all tokens regardless of expiry time',
        )

    def handle(self, *args, **options):
        force_refresh = options['force']
        
        self.stdout.write(self.style.SUCCESS(
            f'[{datetime.now()}] Starting Saxo token refresh...'
        ))
        
        # Get all Saxo brokers with tokens
        saxo_brokers = Broker.objects.filter(
            broker_type='saxo',
            access_token__isnull=False
        )
        
        if not saxo_brokers.exists():
            self.stdout.write(self.style.WARNING('No Saxo brokers found with tokens'))
            return
        
        refreshed_count = 0
        error_count = 0
        
        for broker in saxo_brokers:
            try:
                # Check if token needs refresh
                should_refresh = force_refresh
                
                if not should_refresh and broker.token_expires_at:
                    # Refresh if token expires in less than 30 minutes
                    time_until_expiry = broker.token_expires_at - datetime.now()
                    should_refresh = time_until_expiry < timedelta(minutes=30)
                
                if should_refresh:
                    self.stdout.write(f'Refreshing token for broker: {broker.name}')
                    
                    # Call the broker's refresh method
                    if hasattr(broker, 'refresh_access_token'):
                        broker.refresh_access_token()
                        refreshed_count += 1
                        self.stdout.write(self.style.SUCCESS(
                            f'  ✓ Successfully refreshed token for {broker.name}'
                        ))
                    else:
                        self.stdout.write(self.style.WARNING(
                            f'  ⚠ Broker {broker.name} does not have refresh_access_token method'
                        ))
                else:
                    self.stdout.write(f'  - Token for {broker.name} still valid, skipping')
                    
            except Exception as e:
                error_count += 1
                logger.error(f'Error refreshing token for broker {broker.name}: {str(e)}')
                self.stdout.write(self.style.ERROR(
                    f'  ✗ Error refreshing token for {broker.name}: {str(e)}'
                ))
        
        # Summary
        self.stdout.write(self.style.SUCCESS(
            f'\n[{datetime.now()}] Token refresh completed:'
        ))
        self.stdout.write(f'  - Refreshed: {refreshed_count}')
        self.stdout.write(f'  - Errors: {error_count}')
        self.stdout.write(f'  - Total brokers checked: {saxo_brokers.count()}')
