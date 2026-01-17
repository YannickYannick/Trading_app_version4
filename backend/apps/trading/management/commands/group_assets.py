"""
Management command pour regrouper les AllAssets par asset normalisé.

Crée des Assets normalisés (AAPL, BTC, ETH) et lie les variantes AllAssets (AAPL:xnas, AAPL:xnys).
"""
import re
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.trading.models import AllAssets, Asset


class Command(BaseCommand):
    help = 'Regroupe les AllAssets par asset normalisé et crée les relations parent-enfant'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche les regroupements sans les appliquer',
        )
        parser.add_argument(
            '--clear-assets',
            action='store_true',
            help='Supprime tous les Assets existants avant de regrouper',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        clear_assets = options['clear_assets']

        if clear_assets and not dry_run:
            self.stdout.write(self.style.WARNING('🗑️  Suppression des Assets existants...'))
            Asset.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✅ Assets supprimés'))

        # Récupérer tous les AllAssets
        all_assets = AllAssets.objects.all()
        self.stdout.write(f'📊 {all_assets.count()} AllAssets à traiter')

        # Grouper par symbole normalisé
        grouped = self.group_by_normalized_symbol(all_assets)
        
        self.stdout.write(f'🔍 {len(grouped)} groupes trouvés')

        # Créer les Assets et lier les variantes
        created_count = 0
        updated_count = 0

        for normalized_symbol, variants in grouped.items():
            if dry_run:
                self.stdout.write(f'\n📦 {normalized_symbol}:')
                for variant in variants:
                    best_marker = ' ★' if variant['is_best'] else ''
                    self.stdout.write(f'  - {variant["obj"].symbol} ({variant["obj"].exchange}, {variant["obj"].currency}){best_marker}')
            else:
                created, updated = self.create_or_update_asset(normalized_symbol, variants)
                if created:
                    created_count += 1
                if updated:
                    updated_count += len(variants)

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f'\n✅ {created_count} Assets créés'))
            self.stdout.write(self.style.SUCCESS(f'✅ {updated_count} AllAssets liés'))

    def normalize_symbol(self, symbol: str) -> str:
        """Normalise le symbole en retirant le MIC."""
        # Retirer le MIC (ex: AAPL:xnas -> AAPL)
        base = symbol.split(':')[0] if ':' in symbol else symbol
        # Retirer les espaces
        return base.strip().upper()

    def normalize_company_name(self, name: str) -> str:
        """Normalise le nom de l'entreprise."""
        patterns = [
            r'\s*(A/S)\s*',
            r'\s*(ADR)\s*',
            r'\s*(Inc\.?)\s*',
            r'\s*Classe\s*([A-Z])\s*',
            r'\s*-?\s*([A-Z])\s+Share\s*',
            r'\s*(NV)\s*',
            r'\s*(Corp\.?)\s*',
            r'\s*(Holding)\s*',
        ]
        
        normalized = name
        for pattern in patterns:
            normalized = re.sub(pattern, ' ', normalized, flags=re.IGNORECASE)
        
        return re.sub(r'\s+', ' ', normalized).strip()

    def calculate_score(self, asset: AllAssets) -> float:
        """Calcule le score d'un asset pour déterminer le meilleur."""
        score = 0.0
        
        # Devise (USD prioritaire)
        if asset.currency == 'USD':
            score += 100
        elif asset.currency == 'EUR':
            score += 50
        
        # Bourse principale
        exchange_scores = {
            'NYSE': 80,
            'NASDAQ': 70,
            'Deutsche Börse (XETRA)': 60,
            'Euronext Amsterdam': 50,
            'NASDAQ OMX Copenhagen': 40,
        }
        exchange_name = asset.exchange or ''
        for key, value in exchange_scores.items():
            if key.lower() in exchange_name.lower():
                score += value
                break
        
        # Tradable
        if asset.is_tradable:
            score += 20
        
        return score

    def group_by_normalized_symbol(self, all_assets):
        """Groupe les AllAssets par symbole normalisé."""
        grouped = defaultdict(list)
        
        for asset in all_assets:
            normalized = self.normalize_symbol(asset.symbol)
            score = self.calculate_score(asset)
            
            grouped[normalized].append({
                'obj': asset,
                'score': score,
                'is_best': False,
            })
        
        # Marquer le meilleur pour chaque groupe
        for normalized, variants in grouped.items():
            if variants:
                best = max(variants, key=lambda x: x['score'])
                best['is_best'] = True
        
        return grouped

    @transaction.atomic
    def create_or_update_asset(self, normalized_symbol: str, variants: list):
        """Crée ou met à jour un Asset et lie les variantes."""
        # Trouver le meilleur variant
        best_variant_data = next((v for v in variants if v['is_best']), variants[0])
        best_variant_obj = best_variant_data['obj']
        
        # Créer ou récupérer l'Asset normalisé
        asset, created = Asset.objects.get_or_create(
            symbol=normalized_symbol,
            defaults={
                'name': self.normalize_company_name(best_variant_obj.name),
                'asset_type': self.map_asset_type(best_variant_obj.asset_type),
                'currency': best_variant_obj.currency,
                'exchange': best_variant_obj.exchange,
                'best_variant': best_variant_obj,
            }
        )
        
        # Mettre à jour best_variant si nécessaire
        if not created and asset.best_variant != best_variant_obj:
            asset.best_variant = best_variant_obj
            asset.save()
        
        # Lier toutes les variantes
        for variant_data in variants:
            variant_obj = variant_data['obj']
            variant_obj.parent_asset = asset
            variant_obj.is_best_variant = variant_data['is_best']
            variant_obj.save(update_fields=['parent_asset', 'is_best_variant'])
        
        return created, True

    def map_asset_type(self, broker_type: str) -> str:
        """Mappe le type d'asset broker vers le type Asset."""
        mapping = {
            'Stock': Asset.AssetType.STOCK,
            'CfdOnStock': Asset.AssetType.STOCK,
            'ETF': Asset.AssetType.ETF,
            'Crypto': Asset.AssetType.CRYPTO,
            'FxSpot': Asset.AssetType.FOREX,
        }
        return mapping.get(broker_type, Asset.AssetType.OTHER)
