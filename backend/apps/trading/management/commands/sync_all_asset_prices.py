"""
Django management command to sync AllAsset price history.

Usage:
    python manage.py sync_all_asset_prices --days 30
    python manage.py sync_all_asset_prices --all-asset-id 123 --days 90
    python manage.py sync_all_asset_prices --source YAHOO --days 30
"""
from django.core.management.base import BaseCommand, CommandError

from apps.trading.models import AllAssets
from apps.trading.services.sync.all_asset_price_sync_service import AllAssetPriceSyncService


class Command(BaseCommand):
    help = 'Synchronize price history for AllAssets from Yahoo Finance or brokers'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days of history to sync (default: 30)'
        )
        parser.add_argument(
            '--all-asset-id',
            type=int,
            help='Specific AllAsset ID to sync (if not provided, syncs all eligible AllAssets)'
        )
        parser.add_argument(
            '--source',
            type=str,
            choices=['YAHOO', 'SAXO', 'BINANCE', 'IB'],
            default='YAHOO',
            help='Source to sync from (default: YAHOO)'
        )
    
    def handle(self, *args, **options):
        days = options.get('days', 30)
        all_asset_id = options.get('all_asset_id')
        source = options.get('source', 'YAHOO')
        
        self.stdout.write(
            f"{'='*60}\n"
            f"Syncing AllAsset Price History\n"
            f"{'='*60}\n"
            f"Days: {days}\n"
            f"Source: {source}\n"
        )
        
        if all_asset_id:
            try:
                all_asset = AllAssets.objects.get(id=all_asset_id)
                self.stdout.write(f"AllAsset: {all_asset.symbol} - {all_asset.name}\n")
            except AllAssets.DoesNotExist:
                raise CommandError(f"AllAsset with ID {all_asset_id} not found")
        else:
            self.stdout.write("Syncing all eligible AllAssets (used in Asset, Trade, or Position with validated Yahoo symbol)\n")
        
        self.stdout.write("")
        
        # Initialize service
        service = AllAssetPriceSyncService()
        
        try:
            result = service.sync_all_asset_price_history(
                days=days,
                source=source,
                all_asset_id=all_asset_id
            )
            
            if result.get('success'):
                synced = result.get('synced', 0)
                failed = result.get('failed', 0)
                total_records = result.get('total_records', 0)
                failed_assets = result.get('failed_assets', [])
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n{'='*60}\n"
                        f"SYNC COMPLETED\n"
                        f"{'='*60}\n"
                        f"AllAssets synced: {synced}\n"
                        f"AllAssets failed: {failed}\n"
                        f"Total price records: {total_records}\n"
                    )
                )
                
                if failed_assets:
                    self.stdout.write(
                        self.style.WARNING(
                            f"\nFailed AllAssets:\n"
                        )
                    )
                    for failed_asset in failed_assets:
                        self.stdout.write(
                            f"  - ID {failed_asset['id']} ({failed_asset['symbol']}): "
                            f"{failed_asset['error']}\n"
                        )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"\nSYNC FAILED\n"
                        f"Error: {result.get('message', 'Unknown error')}\n"
                    )
                )
                raise CommandError(result.get('message', 'Sync failed'))
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"\nERROR\n"
                    f"{str(e)}\n"
                )
            )
            raise CommandError(f"Error during sync: {str(e)}")



