"""
Management command pour marquer automatiquement les assets suivis.

Marque is_tracked=True pour les assets qui ont des trades ou des positions.
"""
from django.core.management.base import BaseCommand
from django.db.models import Q, Exists, OuterRef
from apps.trading.models import Asset, Trade, Position


class Command(BaseCommand):
    help = 'Marque automatiquement les assets qui ont des trades ou positions comme tracked'

    def handle(self, *args, **options):
        # Trouver les assets avec trades
        assets_with_trades = Asset.objects.filter(
            Exists(Trade.objects.filter(all_asset__parent_asset=OuterRef('pk')))
        )
        
        # Trouver les assets avec positions
        assets_with_positions = Asset.objects.filter(
            Exists(Position.objects.filter(all_asset__parent_asset=OuterRef('pk')))
        )
        
        # Combiner et marquer comme tracked
        tracked_assets = (assets_with_trades | assets_with_positions).distinct()
        count = tracked_assets.update(is_tracked=True)
        
        self.stdout.write(self.style.SUCCESS(f'✅ {count} assets marqués comme tracked'))
        
        # Afficher quelques exemples
        examples = Asset.objects.filter(is_tracked=True)[:10]
        self.stdout.write('\n📊 Exemples d\'assets suivis:')
        for asset in examples:
            self.stdout.write(f'  - {asset.symbol} ({asset.name})')
