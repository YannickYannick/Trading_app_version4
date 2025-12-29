"""
Django Management Command: Validation Yahoo Finance des Assets

Ce command valide les assets du catalogue universel (AllAssets) et trouve
leur symbole Yahoo Finance correspondant via un algorithme en cascade.

Usage:
    python manage.py validate_yahoo_assets --broker=SAXO --asset-type=Stock
    python manage.py validate_yahoo_assets --broker=BINANCE --workers=2
    python manage.py validate_yahoo_assets --broker=SAXO --tolerance=3.0 --dry-run
"""

import sys
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from apps.trading.models import AllAssets
from apps.trading.services.yahoo_validator import (
    validate_assets,
    clear_yahoo_cache,
    get_cache_info,
    ValidationStats,
)
from apps.trading.utils.yahoo_config import (
    DEFAULT_PRICE_TOLERANCE_PERCENT,
    DEFAULT_MAX_WORKERS,
)


class Command(BaseCommand):
    help = """
    Valide les assets et enrichit le catalogue avec les symboles Yahoo Finance.
    
    Algorithme de validation en cascade:
    1. Y4 (MIC Mapping) - Utilise le code MIC pour construire le ticker Yahoo
    2. Y3 (Recherche nom) - Recherche via l'API Yahoo Search
    3. Y0 (Symbole brut) - Utilise le symbole sans modification
    
    La validation compare les prix entre le broker et Yahoo Finance avec une
    tolérance configurable (défaut: ±5%).
    """

    def add_arguments(self, parser):
        # Arguments obligatoires
        parser.add_argument(
            '--broker',
            type=str,
            required=True,
            choices=['SAXO', 'BINANCE', 'IB', 'OTHER'],
            help='Broker source (SAXO, BINANCE, etc.)'
        )
        
        # Arguments optionnels
        parser.add_argument(
            '--asset-type',
            type=str,
            default=None,
            help='Type d\'actif à filtrer (Stock, ETF, CfdOnStock, etc.)'
        )
        
        parser.add_argument(
            '--workers',
            type=int,
            default=DEFAULT_MAX_WORKERS,
            help=f'Nombre de threads parallèles (défaut: {DEFAULT_MAX_WORKERS})'
        )
        
        parser.add_argument(
            '--tolerance',
            type=float,
            default=DEFAULT_PRICE_TOLERANCE_PERCENT,
            help=f'Tolérance de prix en %% (défaut: {DEFAULT_PRICE_TOLERANCE_PERCENT}%%)'
        )
        
        parser.add_argument(
            '--access-token',
            type=str,
            default=None,
            help='Token d\'accès Saxo (ou utilise SAXO_ACCESS_TOKEN env var)'
        )
        
        parser.add_argument(
            '--saxo-env',
            type=str,
            default='sim',
            choices=['sim', 'live'],
            help='Environnement Saxo: sim ou live (défaut: sim)'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limiter le nombre d\'assets à traiter (pour les tests)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Exécuter sans sauvegarder en base de données'
        )
        
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Vider le cache Yahoo avant de commencer'
        )
        
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Mode silencieux (pas de progression)'
        )
        
        parser.add_argument(
            '--reset-not-found',
            action='store_true',
            help='Revalider les assets marqués "not_found"'
        )

    def handle(self, *args, **options):
        broker = options['broker']
        asset_type = options['asset_type']
        max_workers = options['workers']
        tolerance = options['tolerance']
        access_token = options['access_token']
        saxo_env = options['saxo_env']
        limit = options['limit']
        dry_run = options['dry_run']
        clear_cache = options['clear_cache']
        quiet = options['quiet']
        reset_not_found = options['reset_not_found']
        
        # === Header ===
        if not quiet:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.SUCCESS("🎯 VALIDATION YAHOO FINANCE"))
            self.stdout.write("=" * 80)
        
        # === Vider le cache si demandé ===
        if clear_cache:
            clear_yahoo_cache()
            self.stdout.write(self.style.WARNING("🧹 Cache Yahoo vidé"))
        
        # === Construire la configuration broker ===
        broker_config = self._build_broker_config(broker, access_token, saxo_env)
        
        if broker == 'SAXO' and not broker_config.get('access_token'):
            raise CommandError(
                "Token Saxo requis. Utilisez --access-token ou "
                "définissez SAXO_ACCESS_TOKEN dans l'environnement."
            )
        
        # === Récupérer les assets ===
        queryset = AllAssets.objects.filter(platform=broker)
        
        if asset_type:
            queryset = queryset.filter(asset_type=asset_type)
        
        # Filtre sur symbole_yahoo
        if reset_not_found:
            # Inclure les not_found pour re-validation
            queryset = queryset.filter(symbole_yahoo__in=['Not_searched', 'not_found'])
            if not quiet:
                self.stdout.write(self.style.WARNING("🔄 Mode reset: inclut les 'not_found'"))
        else:
            queryset = queryset.filter(symbole_yahoo='Not_searched')
        
        # Exclure les manuels
        queryset = queryset.exclude(symbole_yahoo='manual')
        
        if limit:
            queryset = queryset[:limit]
            if not quiet:
                self.stdout.write(self.style.WARNING(f"⚠️ Limité à {limit} assets"))
        
        assets = list(queryset)
        
        if not assets:
            self.stdout.write(self.style.WARNING(
                f"\n⚠️ Aucun asset à valider pour {broker}"
                + (f" (type: {asset_type})" if asset_type else "")
            ))
            return
        
        # === Afficher les paramètres ===
        if not quiet:
            self.stdout.write(f"\n📋 Configuration:")
            self.stdout.write(f"   Broker: {broker}")
            if asset_type:
                self.stdout.write(f"   Type: {asset_type}")
            self.stdout.write(f"   Assets à traiter: {len(assets)}")
            self.stdout.write(f"   Tolérance: ±{tolerance}%")
            self.stdout.write(f"   Workers: {max_workers}")
            self.stdout.write(f"   Dry run: {'Oui' if dry_run else 'Non'}")
            if broker == 'SAXO':
                self.stdout.write(f"   Environnement Saxo: {saxo_env}")
        
        # === Confirmation si beaucoup d'assets ===
        if len(assets) > 500 and not dry_run:
            self.stdout.write(self.style.WARNING(
                f"\n⚠️ Vous allez traiter {len(assets)} assets."
            ))
            if input("Continuer? (y/n): ").lower() != 'y':
                self.stdout.write(self.style.ERROR("Annulé."))
                return
        
        # === Exécuter la validation ===
        try:
            stats = validate_assets(
                all_assets=assets,
                broker_name=broker,
                asset_type=asset_type,
                max_workers=max_workers,
                tolerance_percent=tolerance,
                broker_config=broker_config,
                save_to_db=not dry_run,
                verbose=not quiet,
            )
            
            # === Résumé final ===
            if not quiet:
                self._print_summary(stats, dry_run)
                
                # Info cache
                cache_info = get_cache_info()
                self.stdout.write(f"\n📊 Cache Yahoo:")
                self.stdout.write(f"   Prix: {cache_info['price_cache']['hits']} hits, "
                                  f"{cache_info['price_cache']['misses']} misses")
                self.stdout.write(f"   Search: {cache_info['search_cache']['hits']} hits, "
                                  f"{cache_info['search_cache']['misses']} misses")
            
            # Code de sortie basé sur le succès
            if stats.errors > stats.total * 0.1:  # Plus de 10% d'erreurs
                sys.exit(1)
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.ERROR("\n\n❌ Interrompu par l'utilisateur"))
            sys.exit(130)
        except Exception as e:
            raise CommandError(f"Erreur de validation: {e}")
    
    def _build_broker_config(
        self, 
        broker: str, 
        access_token: str, 
        saxo_env: str
    ) -> dict:
        """Construit la configuration du broker."""
        config = {}
        
        if broker == 'SAXO':
            # Token depuis argument ou environnement
            token = access_token or getattr(settings, 'SAXO_ACCESS_TOKEN', None)
            if not token:
                import os
                token = os.environ.get('SAXO_ACCESS_TOKEN')
            
            config['access_token'] = token
            
            # URL de base selon l'environnement
            if saxo_env == 'live':
                config['base_url'] = 'https://gateway.saxobank.com/openapi'
            else:
                # ✅ MIGRATION: Fallback changé de SIM vers LIVE
                config['base_url'] = 'https://gateway.saxobank.com/openapi'
        
        elif broker == 'BINANCE':
            # Binance n'a pas besoin de token pour les prix publics
            pass
        
        return config
    
    def _print_summary(self, stats: ValidationStats, dry_run: bool) -> None:
        """Affiche le résumé coloré."""
        self.stdout.write("\n" + "=" * 80)
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 RÉSULTATS (DRY RUN - non sauvegardés)"))
        else:
            self.stdout.write(self.style.SUCCESS("✅ RÉSULTATS DE VALIDATION"))
        
        self.stdout.write("=" * 80)
        
        self.stdout.write(f"\n📈 Statistiques:")
        self.stdout.write(f"   Total traité: {stats.total}")
        self.stdout.write(self.style.SUCCESS(f"   ✅ Validés Y4 (MIC): {stats.validated_y4}"))
        self.stdout.write(self.style.SUCCESS(f"   ✅ Validés Y3 (nom): {stats.validated_y3}"))
        self.stdout.write(self.style.SUCCESS(f"   ✅ Validés Y0 (brut): {stats.validated_y0}"))
        
        self.stdout.write(self.style.SUCCESS(
            f"\n   🎯 TOTAL VALIDÉS: {stats.validated_total} ({stats.success_rate:.1f}%)"
        ))
        
        if stats.not_found > 0:
            self.stdout.write(self.style.WARNING(f"   ❌ Non trouvés: {stats.not_found}"))
        
        if stats.errors > 0:
            self.stdout.write(self.style.ERROR(f"   ⚠️ Erreurs: {stats.errors}"))
        
        if stats.skipped > 0:
            self.stdout.write(f"   ⏭️ Ignorés (manual): {stats.skipped}")
        
        self.stdout.write("\n" + "=" * 80)

