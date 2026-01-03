"""
Django management command to migrate existing AllAssetPriceHistory data to JSONB format.

This command converts all existing AllAssetPriceHistory records to the new JSONB format
stored in AllAssets.price_history_json field.

Usage:
    python manage.py migrate_price_history_to_jsonb
    python manage.py migrate_price_history_to_jsonb --dry-run  # Affiche ce qui serait fait sans modifier
    python manage.py migrate_price_history_to_jsonb --all-asset-id 123  # Migrer un seul asset
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from collections import defaultdict

from apps.trading.models import AllAssets, AllAssetPriceHistory


class Command(BaseCommand):
    help = 'Migrate existing AllAssetPriceHistory records to JSONB format in AllAssets'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually doing it'
        )
        parser.add_argument(
            '--all-asset-id',
            type=int,
            help='Migrate only a specific AllAsset ID'
        )
        parser.add_argument(
            '--delete-old',
            action='store_true',
            help='Delete old AllAssetPriceHistory records after migration (use with caution!)'
        )
    
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        all_asset_id = options.get('all_asset_id')
        delete_old = options.get('delete_old', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No changes will be made\n"))
        
        if delete_old and not dry_run:
            self.stdout.write(self.style.WARNING("⚠️  WARNING: --delete-old is set. Old records will be deleted!\n"))
        
        self.stdout.write(f"{'='*60}\n")
        self.stdout.write(f"Migrating AllAssetPriceHistory to JSONB format\n")
        self.stdout.write(f"{'='*60}\n")
        
        # Récupérer tous les AllAssets qui ont des prix historiques
        if all_asset_id:
            try:
                all_assets = [AllAssets.objects.get(id=all_asset_id)]
            except AllAssets.DoesNotExist:
                raise CommandError(f"AllAsset with ID {all_asset_id} not found")
        else:
            # Récupérer tous les AllAssets qui ont des prix historiques
            all_asset_ids = AllAssetPriceHistory.objects.values_list(
                'all_asset_id', flat=True
            ).distinct()
            all_assets = AllAssets.objects.filter(id__in=all_asset_ids)
        
        self.stdout.write(f"Found {all_assets.count()} AllAssets with price history\n")
        
        total_migrated = 0
        total_records = 0
        errors = []
        
        for all_asset in all_assets:
            try:
                # Récupérer tous les prix historiques pour cet asset
                price_records = AllAssetPriceHistory.objects.filter(
                    all_asset=all_asset
                ).order_by('date')
                
                if not price_records.exists():
                    continue
                
                # Construire le dictionnaire JSON
                price_dict = {}
                records_count = 0
                
                for record in price_records:
                    date_str = record.date.strftime('%Y-%m-%d')
                    
                    # Si plusieurs sources pour la même date, garder la plus récente
                    # (ou prioriser YAHOO)
                    if date_str in price_dict:
                        existing_source = price_dict[date_str].get('source', '')
                        if existing_source == 'YAHOO' and record.source != 'YAHOO':
                            continue  # Garder YAHOO si existe déjà
                    
                    price_dict[date_str] = {
                        'open': float(record.open_price),
                        'high': float(record.high_price),
                        'low': float(record.low_price),
                        'close': float(record.close_price),
                        'volume': int(record.volume) if record.volume else 0,
                        'source': record.source
                    }
                    records_count += 1
                
                if not dry_run:
                    # Sauvegarder dans le champ JSONB
                    with transaction.atomic():
                        all_asset.price_history_json = price_dict
                        all_asset.price_history_days = len(price_dict)
                        all_asset.price_history_updated_at = timezone.now()
                        all_asset.save(update_fields=[
                            'price_history_json',
                            'price_history_days',
                            'price_history_updated_at'
                        ])
                        
                        # Supprimer les anciens enregistrements si demandé
                        if delete_old:
                            price_records.delete()
                
                total_migrated += 1
                total_records += records_count
                
                self.stdout.write(
                    f"✅ {all_asset.symbol}: {records_count} records → JSONB "
                    f"({len(price_dict)} unique dates)"
                )
                
            except Exception as e:
                error_msg = f"Error migrating {all_asset.symbol} (ID: {all_asset.id}): {str(e)}"
                errors.append(error_msg)
                self.stdout.write(
                    self.style.ERROR(f"❌ {error_msg}")
                )
        
        # Résumé
        self.stdout.write(f"\n{'='*60}\n")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes made\n"))
        else:
            self.stdout.write(self.style.SUCCESS("✅ MIGRATION COMPLETED\n"))
        
        self.stdout.write(
            f"AllAssets migrated: {total_migrated}\n"
            f"Total records processed: {total_records}\n"
            f"Errors: {len(errors)}\n"
        )
        
        if errors:
            self.stdout.write(self.style.ERROR("\n⚠️  Errors occurred:\n"))
            for error in errors:
                self.stdout.write(f"  - {error}\n")
        
        if delete_old and not dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  Old AllAssetPriceHistory records have been deleted!\n"
                )
            )



