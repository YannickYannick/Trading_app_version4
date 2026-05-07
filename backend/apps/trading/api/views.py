"""
ViewSets pour l'API REST Trading.

Un ViewSet crée automatiquement tous les endpoints CRUD :
- GET /api/assets/ → Liste tous les assets
- POST /api/assets/ → Crée un asset
- GET /api/assets/1/ → Détails de l'asset #1
- PUT /api/assets/1/ → Met à jour l'asset #1
- DELETE /api/assets/1/ → Supprime l'asset #1
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from datetime import timedelta
import logging

from apps.trading.models import (
    AllAssets, Asset, AssetPrice, AllAssetPriceHistory, Position, Trade, Order,
    Strategy, StrategyPerformance, Broker, BrokerAccount, BrokerSyncLog,
    ScheduledTask, TaskExecutionLog, PortfolioSnapshot, StrategyExecution
)
from apps.trading.services.broker_service import BrokerService, resolve_all_asset_from_asset
from .serializers import (
    AllAssetsSerializer, AssetSerializer, AssetNestedSerializer, AssetPriceSerializer,
    AllAssetPriceHistorySerializer, PositionSerializer, TradeSerializer, OrderSerializer,
    StrategySerializer, BrokerSerializer, BrokerAccountSerializer, StrategyExecutionSerializer
)


# ============================================
# PAGINATION PERSONNALISÉE
# ============================================

class StandardPagination(PageNumberPagination):
    """Pagination standard pour la plupart des endpoints."""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class LargePagination(PageNumberPagination):
    """Pagination pour les grandes listes (AllAssets)."""
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 500

# Logger pour ce module
logger = logging.getLogger('trading.api.orders')


# ============================================
# VIEWSETS CATALOGUE (AllAssets)
# ============================================

class AllAssetsViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour le catalogue universel des assets (AllAssets).
    
    Endpoints automatiques :
    - GET /api/all-assets/ → Liste tous les assets du catalogue
    - POST /api/all-assets/ → Ajoute un asset au catalogue
    - GET /api/all-assets/1/ → Détails d'un asset
    - PUT /api/all-assets/1/ → Met à jour un asset
    - DELETE /api/all-assets/1/ → Supprime un asset
    
    Actions personnalisées :
    - GET /api/all-assets/saxo/ → Assets Saxo uniquement
    - GET /api/all-assets/binance/ → Assets Binance uniquement
    - GET /api/all-assets/stats/ → Statistiques du catalogue
    - GET /api/all-assets/search/?q=AAPL → Recherche
    """
    queryset = AllAssets.objects.all()
    serializer_class = AllAssetsSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LargePagination
    
    # Filtres automatiques (django-filter)
    filterset_fields = ['platform', 'asset_type', 'market', 'currency', 'is_tradable']
    search_fields = ['symbol', 'name']
    ordering_fields = ['symbol', 'name', 'platform', 'asset_type', 'last_updated']
    ordering = ['symbol']
    
    @action(detail=False, methods=['get'])
    def saxo(self, request):
        """
        GET /api/all-assets/saxo/
        Récupère uniquement les assets Saxo.
        """
        assets = self.filter_queryset(self.get_queryset().filter(platform='SAXO'))
        page = self.paginate_queryset(assets)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(assets, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def binance(self, request):
        """
        GET /api/all-assets/binance/
        Récupère uniquement les assets Binance.
        """
        assets = self.filter_queryset(self.get_queryset().filter(platform='BINANCE'))
        page = self.paginate_queryset(assets)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(assets, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        GET /api/all-assets/stats/
        Statistiques complètes du catalogue.
        """
        queryset = self.get_queryset()
        total = queryset.count()
        tradable = queryset.filter(is_tradable=True).count()
        by_platform = list(queryset.values('platform').annotate(count=Count('id')).order_by('-count'))
        by_type = list(queryset.values('asset_type').annotate(count=Count('id')).order_by('-count')[:10])
        by_currency = list(queryset.values('currency').annotate(count=Count('id')).order_by('-count')[:10])
        
        return Response({
            'total': total,
            'tradable': tradable,
            'non_tradable': total - tradable,
            'by_platform': by_platform,
            'by_type': by_type,
            'by_currency': by_currency,
            'last_updated': queryset.order_by('-last_updated').first().last_updated if queryset.exists() else None,
        })
    
    @action(detail=False, methods=['get'], url_path='search')
    def search_assets(self, request):
        """
        GET /api/all-assets/search/?q=AAPL
        Recherche avancée dans le catalogue.
        """
        query = request.query_params.get('q', '')
        if len(query) < 2:
            return Response({'error': 'Query must be at least 2 characters'}, status=400)
        
        assets = self.get_queryset().filter(
            Q(symbol__icontains=query) | Q(name__icontains=query)
        )[:50]
        
        serializer = self.get_serializer(assets, many=True)
        return Response({
            'query': query,
            'count': len(serializer.data),
            'results': serializer.data
        })
    
    @action(detail=False, methods=['get'], url_path='autocomplete')
    def autocomplete(self, request):
        """
        GET /api/all-assets/autocomplete/?q=AAPL&platform=SAXO
        Autocomplétion pour le placement d'ordres.
        Retourne une liste simplifiée d'AllAssets pour l'autocomplétion.
        """
        query = request.query_params.get('q', '').strip()
        platform = request.query_params.get('platform')  # Optionnel : filtrer par plateforme
        
        if len(query) < 2:
            return Response({'results': []})
        
        # Nettoyer le symbole de recherche
        query_clean = query.split(':')[0].strip().upper()
        query_clean = query_clean.split('_')[0].strip()
        
        queryset = self.get_queryset().filter(
            Q(symbol__icontains=query_clean) | Q(name__icontains=query),
            is_tradable=True
        )
        
        # Filtrer par plateforme si fournie
        if platform:
            queryset = queryset.filter(platform=platform.upper())
        
        # Limiter à 10 résultats et trier par symbole
        assets = queryset.order_by('symbol')[:10]
        
        results = []
        for asset in assets:
            results.append({
                'id': asset.id,  # ID AllAssets
                'symbol': asset.symbol,
                'name': asset.name,
                'platform': asset.platform,
                'asset_type': asset.asset_type,
                'currency': asset.currency,
                'market': asset.market,
                'text': f"{asset.symbol} - {asset.name} ({asset.platform})",
                'saxo_uic': getattr(asset, 'saxo_uic', None),  # Pour info
            })
        
        return Response({'results': results})

    @action(detail=False, methods=['post'], url_path='populate-names-yahoo')
    def populate_names_yahoo(self, request):
        """
        POST /api/all-assets/populate-names-yahoo/

        Remplit `AllAssets.name` (et métadonnées `sector` / `industry`) depuis Yahoo (yfinance).
        Utile quand la liste Positions affiche 2× le symbole (name = symbol).

        Body (optionnel):
        - limit: int (défaut 200)
        - dry_run: bool (défaut false)
        """
        from ..services.data_providers.yahoo_finance import YahooFinanceService
        import logging

        logger = logging.getLogger('trading.api.assets')

        limit = int(request.data.get('limit', 200) or 200)
        dry_run = bool(request.data.get('dry_run', False))

        service = YahooFinanceService()
        if not service.is_available:
            return Response(
                {'success': False, 'error': 'yfinance not available on server'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Candidats: seulement ceux avec un symbole Yahoo validé (sinon aucune source fiable)
        candidates = (
            self.get_queryset()
            .exclude(symbole_yahoo__in=['Not_searched', 'not_found', 'manual', ''])
            .order_by('id')[: max(1, limit)]
        )

        updated = 0
        checked = 0
        details = []

        for asset in candidates:
            checked += 1

            current_name = (asset.name or '').strip()
            symbol_like = (asset.symbol or '').strip()
            current_sector = (getattr(asset, 'sector', '') or '').strip()
            current_industry = (getattr(asset, 'industry', '') or '').strip()

            needs_name = not current_name or current_name.lower() == symbol_like.lower()
            needs_meta = (not current_sector) or (not current_industry)
            if not (needs_name or needs_meta):
                continue

            info = service.get_asset_info(asset.symbole_yahoo) or {}
            new_name = (info.get('name') or service.get_display_name(asset.symbole_yahoo) or '').strip()
            new_sector = (info.get('sector') or '').strip()
            new_industry = (info.get('industry') or '').strip()

            if needs_name and not new_name:
                continue

            if not dry_run:
                dirty_fields = []
                if needs_name and new_name and new_name != asset.name:
                    asset.name = new_name
                    dirty_fields.append('name')
                if new_sector and new_sector != getattr(asset, 'sector', ''):
                    asset.sector = new_sector
                    dirty_fields.append('sector')
                if new_industry and new_industry != getattr(asset, 'industry', ''):
                    asset.industry = new_industry
                    dirty_fields.append('industry')
                if dirty_fields:
                    dirty_fields.append('last_updated')
                    asset.save(update_fields=dirty_fields)

            updated += 1
            if len(details) < 25:
                details.append({
                    'id': asset.id,
                    'symbol': asset.symbol,
                    'yahoo_symbol': asset.symbole_yahoo,
                    'name': new_name or asset.name,
                    'sector': new_sector or getattr(asset, 'sector', ''),
                    'industry': new_industry or getattr(asset, 'industry', ''),
                })

        logger.info(
            f"[populate-names-yahoo] checked={checked} updated={updated} dry_run={dry_run}"
        )

        return Response({
            'success': True,
            'checked': checked,
            'updated': updated,
            'dry_run': dry_run,
            'sample': details,
        })

    @action(detail=False, methods=['post'], url_path='enrich-yahoo-meta')
    def enrich_yahoo_meta(self, request):
        """
        POST /api/all-assets/enrich-yahoo-meta/

        Enrichit un sous-ensemble d'AllAssets (name/sector/industry) depuis Yahoo, à partir d'une
        liste d'IDs. Conçu pour le workflow UI (Positions → « Charger prix Yahoo »).

        Body:
        - all_asset_ids: number[] (requis)
        - dry_run: bool (défaut false)
        """
        from ..services.data_providers.yahoo_finance import YahooFinanceService
        import logging

        logger = logging.getLogger('trading.api.assets')

        ids = request.data.get('all_asset_ids') or []
        dry_run = bool(request.data.get('dry_run', False))

        if not isinstance(ids, list) or not ids:
            return Response(
                {'success': False, 'error': 'all_asset_ids est requis (liste non vide)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Sanitize IDs
        safe_ids = []
        for x in ids:
            try:
                safe_ids.append(int(x))
            except (TypeError, ValueError):
                continue

        if not safe_ids:
            return Response(
                {'success': False, 'error': 'Aucun all_asset_id valide fourni'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = YahooFinanceService()
        if not service.is_available:
            return Response(
                {'success': False, 'error': 'yfinance not available on server'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        qs = (
            self.get_queryset()
            .filter(id__in=safe_ids)
            .exclude(symbole_yahoo__in=['Not_searched', 'not_found', 'manual', ''])
            .order_by('id')
        )

        checked = 0
        updated = 0
        details = []

        for asset in qs:
            checked += 1
            current_name = (asset.name or '').strip()
            symbol_like = (asset.symbol or '').strip()
            current_sector = (getattr(asset, 'sector', '') or '').strip()
            current_industry = (getattr(asset, 'industry', '') or '').strip()

            needs_name = not current_name or current_name.lower() == symbol_like.lower()
            needs_meta = (not current_sector) or (not current_industry)
            if not (needs_name or needs_meta):
                continue

            info = service.get_asset_info(asset.symbole_yahoo) or {}
            new_name = (info.get('name') or service.get_display_name(asset.symbole_yahoo) or '').strip()
            new_sector = (info.get('sector') or '').strip()
            new_industry = (info.get('industry') or '').strip()

            if needs_name and not new_name:
                continue

            if not dry_run:
                dirty_fields = []
                if needs_name and new_name and new_name != asset.name:
                    asset.name = new_name
                    dirty_fields.append('name')
                if new_sector and new_sector != getattr(asset, 'sector', ''):
                    asset.sector = new_sector
                    dirty_fields.append('sector')
                if new_industry and new_industry != getattr(asset, 'industry', ''):
                    asset.industry = new_industry
                    dirty_fields.append('industry')
                if dirty_fields:
                    dirty_fields.append('last_updated')
                    asset.save(update_fields=dirty_fields)

            updated += 1
            if len(details) < 25:
                details.append({
                    'id': asset.id,
                    'symbol': asset.symbol,
                    'yahoo_symbol': asset.symbole_yahoo,
                    'name': new_name or asset.name,
                    'sector': new_sector or getattr(asset, 'sector', ''),
                    'industry': new_industry or getattr(asset, 'industry', ''),
                })

        logger.info(
            f"[enrich-yahoo-meta] checked={checked} updated={updated} ids={len(safe_ids)} dry_run={dry_run}"
        )

        return Response({
            'success': True,
            'checked': checked,
            'updated': updated,
            'dry_run': dry_run,
            'sample': details,
        })
    
    @action(detail=False, methods=['post'], url_path='validate-yahoo-symbols')
    def validate_yahoo_symbols(self, request):
        """
        POST /api/all-assets/validate-yahoo-symbols/
        Met à jour les symboles Yahoo Finance pour tous les assets.
        
        Body optionnel:
        - reset: Si true, réinitialise tous les symboles avant validation
        - limit: Nombre max d'assets à traiter (défaut: DEFAULT_VALIDATION_LIMIT)
        - platform: Filtrer par plateforme (SAXO, BINANCE, etc.)
        """
        from ..services.yahoo_validator import validate_single_asset, ValidationStats
        from ..utils.yahoo_config import ValidationStatus
        from ..constants import DEFAULT_VALIDATION_LIMIT, DEFAULT_PRICE_TOLERANCE_PERCENT
        from django.utils import timezone
        import logging
        
        logger = logging.getLogger('trading.api.assets')
        
        try:
            # Récupérer les paramètres du body ou query params
            data = request.data if hasattr(request, 'data') and request.data else {}
            reset = data.get('reset', request.query_params.get('reset', 'false'))
            reset = str(reset).lower() == 'true'
            limit = int(data.get('limit', request.query_params.get('limit', DEFAULT_VALIDATION_LIMIT)))
            platform = data.get('platform') or request.query_params.get('platform')
            only_existing_assets = data.get('onlyExistingAssets', False) or data.get('only_existing_assets', False)
            
            # Construire le queryset
            queryset = AllAssets.objects.all()
            
            if platform:
                queryset = queryset.filter(platform=platform)
            
            # ✅ NOUVELLE OPTION: Filtrer uniquement les assets qui existent dans le modèle Asset
            if only_existing_assets:
                from ..models import Asset
                existing_all_asset_ids = Asset.objects.filter(
                    all_asset__isnull=False
                ).values_list('all_asset_id', flat=True).distinct()
                queryset = queryset.filter(id__in=existing_all_asset_ids)
                logger.info(f"Filtrage 'only-existing-assets': {queryset.count()} assets correspondent au modèle Asset")
            
            # Si reset, réinitialiser les symboles Yahoo
            if reset:
                updated_count = queryset.update(symbole_yahoo='Not_searched')
                logger.info(f"Reset symbole_yahoo pour {updated_count} assets")
            
            # Filtrer les assets qui ont besoin de validation
            queryset = queryset.filter(
                symbole_yahoo__in=['Not_searched', 'not_found']
            )[:limit]
            
            assets_list = list(queryset)
            assets_count = len(assets_list)
            
            if assets_count == 0:
                return Response({
                    'success': True,
                    'message': 'Aucun asset à valider',
                    'processed': 0,
                    'validated': 0,
                    'failed': 0,
                    'not_found': 0
                })
            
            logger.info(f"Démarrage validation Yahoo pour {assets_count} assets")
            
            # Initialiser les stats
            stats = ValidationStats()
            stats.total = assets_count
            
            # ✅ OPTIMISATION: Créer l'instance broker une seule fois avant la boucle
            # Récupérer le broker config si disponible (pour Saxo)
            broker_config = {}
            if assets_list and assets_list[0].platform == 'SAXO':
                # Essayer de récupérer un access token valide d'un compte Saxo actif
                # Utiliser le service broker pour obtenir un token valide (avec refresh automatique)
                from ..models import BrokerAccount
                from ..services.broker_service import BrokerService
                saxo_account = BrokerAccount.objects.filter(
                    broker_type='SAXO',
                    user=request.user
                ).first()
                if saxo_account:
                    try:
                        # ✅ OPTIMISATION: Créer l'instance broker une seule fois et la réutiliser
                        broker_service = BrokerService(request.user)
                        broker = broker_service.get_broker_instance(saxo_account, use_cache=True)  # Utiliser le cache
                        
                        # Authentifier (cela va rafraîchir le token si nécessaire)
                        if broker.authenticate():
                            broker_config['access_token'] = broker.access_token
                            broker_config['base_url'] = broker.base_url
                            logger.debug(f"Using valid Saxo token for validation (account {saxo_account.id}) - instance réutilisée")
                        else:
                            logger.warning(f"Could not authenticate Saxo broker for validation: {broker.last_error}")
                    except Exception as e:
                        logger.warning(f"Error getting valid Saxo token: {e}")
                        # Fallback: utiliser le token stocké directement (peut être expiré)
                        if saxo_account.saxo_access_token:
                            broker_config['access_token'] = saxo_account.saxo_access_token
                            # ✅ MIGRATION: Fallback changé de SIM vers LIVE
                            broker_config['base_url'] = 'https://gateway.saxobank.com/openapi'
                            logger.debug(f"Using stored Saxo token (may be expired)")
            
            # Valider chaque asset avec suivi du progrès
            processed_count = 0
            for asset in assets_list:
                processed_count += 1
                logger.debug(f"Traitement asset {processed_count}/{assets_count}: {asset.symbol}")
                try:
                    
                    # Utiliser validate_single_asset
                    result = validate_single_asset(
                        asset,
                        broker_config=broker_config,
                        tolerance_percent=DEFAULT_PRICE_TOLERANCE_PERCENT
                    )
                    
                    # Log détaillé pour débogage
                    logger.debug(
                        f"Asset {asset.symbol}: status={result.status}, "
                        f"yahoo_symbol={result.yahoo_symbol}, method={result.method}, "
                        f"error={result.error_message}"
                    )
                    
                    # Mettre à jour les statistiques
                    # result.status est déjà une chaîne (ex: 'validated_y4', 'not_found', 'error')
                    # Comparaison en utilisant les valeurs string des constantes ValidationStatus
                    status_str = str(result.status) if result.status else ''
                    if status_str == ValidationStatus.VALIDATED_Y4:
                        stats.validated_y4 += 1
                    elif status_str == ValidationStatus.VALIDATED_Y3:
                        stats.validated_y3 += 1
                    elif status_str == ValidationStatus.VALIDATED_Y0:
                        stats.validated_y0 += 1
                    elif status_str == ValidationStatus.NOT_FOUND:
                        stats.not_found += 1
                    elif status_str == ValidationStatus.ERROR:
                        stats.errors += 1
                        # Logger l'erreur pour comprendre pourquoi
                        logger.warning(
                            f"Validation ERROR pour {asset.symbol}: {result.error_message or 'No error message'}"
                        )
                    else:
                        # Cas inattendu, logger et compter comme erreur
                        logger.warning(
                            f"Status inattendu pour {asset.symbol}: {result.status} "
                            f"(type: {type(result.status)})"
                        )
                        stats.errors += 1
                    
                    # Sauvegarder le résultat
                    asset.symbole_yahoo = result.yahoo_symbol
                    asset.yahoo_validation_method = result.method
                    asset.yahoo_validated_at = timezone.now()
                    asset.save(update_fields=[
                        'symbole_yahoo',
                        'yahoo_validation_method',
                        'yahoo_validated_at'
                    ])
                    
                except Exception as e:
                    logger.error(f"Erreur validation asset {asset.symbol}: {e}")
                    stats.errors += 1
            
            return Response({
                'success': True,
                'message': f'Validation terminée pour {assets_count} assets',
                'processed': stats.total,  # Utiliser stats.total au lieu de processed_total
                'validated': stats.validated_total,
                'failed': stats.errors,
                'not_found': stats.not_found,
                'details': {
                    'y4_matches': stats.validated_y4,
                    'y3_matches': stats.validated_y3,
                    'y0_matches': stats.validated_y0,
                }
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la validation Yahoo: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='prices')
    def prices(self, request, pk=None):
        """
        GET /api/all-assets/{id}/prices/
        Récupère l'historique des prix pour cet AllAsset depuis le champ JSONB.
        
        Query params:
        - days: Nombre de jours à récupérer (défaut: 100)
        - source: Filtrer par source (YAHOO, SAXO, BINANCE, etc.) - optionnel
            - output_format: Format de réponse ('json' ou 'list', défaut: 'list') - utilisez 'output_format' au lieu de 'format' pour éviter conflit avec DRF
        
        Avec detail=True, DRF gère automatiquement le routing vers {pk}
        On récupère directement l'objet pour éviter les problèmes avec filter_queryset().
        """
        logger = logging.getLogger('trading.api.assets')
        logger.info(f"[PRICES] Prices endpoint called for AllAsset ID: {pk}, user: {request.user}")
        
        # Récupérer l'objet directement depuis le queryset de base (sans filtres)
        # pour éviter les problèmes avec django_filters qui nécessite request.query_params
        try:
            # Utiliser le queryset de base directement, sans filtres
            all_asset = AllAssets.objects.get(pk=pk)
            logger.info(f"[PRICES] Found AllAsset: {all_asset.symbol} (ID: {all_asset.pk})")
        except AllAssets.DoesNotExist:
            logger.error(f"[PRICES] AllAsset {pk} not found")
            return Response(
                {
                    'all_asset_id': int(pk) if pk else None,
                    'all_asset_symbol': None,
                    'count': 0,
                    'message': f'AllAsset {pk} not found',
                    'error': 'Not found',
                    'results': []
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"[PRICES] Error getting AllAsset {pk}: {e}", exc_info=True)
            return Response(
                {
                    'all_asset_id': int(pk) if pk else None,
                    'all_asset_symbol': None,
                    'count': 0,
                    'message': f'Error retrieving AllAsset {pk}',
                    'error': str(e),
                    'results': []
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Récupérer les paramètres de requête
        # Gérer à la fois DRF request (query_params) et WSGIRequest standard (GET)
        query_params = getattr(request, 'query_params', request.GET)
        
        days_param = query_params.get('days', '100')
        try:
            days = int(days_param)
            if days <= 0:
                raise ValueError("Days must be positive")
        except ValueError:
            logger.warning(f"[PRICES] Invalid days parameter: {days_param}, using default 100")
            days = 100
        
        source = query_params.get('source')
        # Utiliser 'output_format' au lieu de 'format' pour éviter conflit avec DRF format suffix
        format_type = query_params.get('output_format') or query_params.get('format', 'list')
        
        # Utiliser la même logique que show_last_saxo_trade.py
        # Vérifier si l'historique existe
        if not all_asset.has_price_history:
            logger.debug(f"[PRICES] No price history for AllAsset {all_asset.id}")
            return Response({
                'all_asset_id': all_asset.id,
                'all_asset_symbol': all_asset.symbol,
                'count': 0,
                'message': 'No price history available',
                'results': []
            })
        
        # Récupérer les dates disponibles (triées du plus récent au plus ancien)
        dates = all_asset.get_price_history_dates()
        
        if not dates:
            logger.debug(f"[PRICES] No dates in price history for AllAsset {all_asset.id}")
            return Response({
                'all_asset_id': all_asset.id,
                'all_asset_symbol': all_asset.symbol,
                'count': 0,
                'message': 'No dates available in price history',
                'results': []
            })
        
        # Limiter au nombre de jours demandés
        dates_to_return = dates[:days]
        
        logger.debug(f"[PRICES] Total history dates: {len(dates)}, Requested days: {days}, Returning: {len(dates_to_return)}")
        
        # Convertir en liste formatée (comme dans le script)
        prices_list = []
        
        for date_str in dates_to_return:
            # Utiliser get_price_for_date() comme dans le script
            price_data = all_asset.get_price_for_date(date_str)
            
            if not price_data:
                logger.debug(f"[PRICES] No price data for date {date_str}")
                continue
            
            # Filtrer par source si spécifié
            price_source = price_data.get('source', 'YAHOO')
            if source and price_source != source:
                continue
            
            # Vérifier que le prix de clôture n'est pas None/NaN
            close_price = price_data.get('close')
            if close_price is None:
                logger.debug(f"[PRICES] Skipping {date_str}: close price is None")
                continue
            
            # Formater comme le script (mais en JSON)
            prices_list.append({
                'date': date_str,
                'open': price_data.get('open'),
                'high': price_data.get('high'),
                'low': price_data.get('low'),
                'close': close_price,
                'close_price': close_price,  # Alias pour compatibilité frontend
                'open_price': price_data.get('open'),
                'high_price': price_data.get('high'),
                'low_price': price_data.get('low'),
                'volume': price_data.get('volume', 0),
                'source': price_source
            })
        
        logger.debug(f"[PRICES] Final prices_list count: {len(prices_list)}")
        
        # Retourner selon le format demandé
        if format_type == 'json':
            # Retourner le JSON brut (format compact)
            return Response({
                'all_asset_id': all_asset.id,
                'all_asset_symbol': all_asset.symbol,
                'count': len(prices_list),
                'format': 'json',
                'data': all_asset.price_history_json or {}
            })
        else:
            # Format liste (compatible avec le frontend)
            return Response({
                'all_asset_id': all_asset.id,
                'all_asset_symbol': all_asset.symbol,
                'count': len(prices_list),
                'format': 'list',
                'total_days_available': len(dates),
                'results': prices_list
            })

    @action(detail=True, methods=['get'], url_path='chart-tooltip')
    def chart_tooltip(self, request, pk=None):
        """
        GET /api/all-assets/{id}/chart-tooltip/
        Retourne un payload optimisé pour un tooltip:
        - historique (close) depuis `price_history_json` (déjà synchronisé)
        - marqueurs trades BUY/SELL (user) pour cet AllAsset

        Query params:
        - days: nombre de jours d'historique (défaut 180)
        - trades_days: filtre trades sur N jours (défaut = days)
        - max_trades: limite de trades renvoyés (défaut 200)

        ⚠️ Ne déclenche pas de sync yfinance pour éviter le spam (le front peut appeler
        /sync_price_history/ explicitement via un bouton si besoin).
        """
        from ..models import Trade, AllAssets
        import logging

        logger = logging.getLogger('trading.api.assets')

        try:
            all_asset = AllAssets.objects.get(pk=pk)
        except AllAssets.DoesNotExist:
            return Response(
                {'error': f'AllAsset {pk} not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        qp = getattr(request, 'query_params', request.GET)
        try:
            days = int(qp.get('days', 180))
            if days <= 0:
                days = 180
        except (TypeError, ValueError):
            days = 180

        try:
            trades_days = int(qp.get('trades_days', days))
            if trades_days <= 0:
                trades_days = days
        except (TypeError, ValueError):
            trades_days = days

        try:
            max_trades = int(qp.get('max_trades', 200))
            if max_trades <= 0:
                max_trades = 200
            max_trades = min(max_trades, 1000)
        except (TypeError, ValueError):
            max_trades = 200

        # --- Prices (close) ---
        prices = []
        if all_asset.has_price_history:
            dates = all_asset.get_price_history_dates()
            for date_str in dates[:days]:
                price_data = all_asset.get_price_for_date(date_str) or {}
                close_price = price_data.get('close')
                if close_price is None:
                    continue
                prices.append({
                    'date': date_str,
                    'close': close_price,
                })
            # Repasser en chrono (lightweight-charts / recharts apprécient)
            prices.sort(key=lambda x: x['date'])

        # --- Trades markers ---
        since = timezone.now() - timedelta(days=trades_days)
        qs = (
            Trade.objects.filter(
                user=request.user,
                all_asset_id=all_asset.id,
                executed_at__gte=since,
            )
            .only('id', 'trade_type', 'quantity', 'price', 'executed_at')
            .order_by('executed_at')[:max_trades]
        )

        trades = []
        for t in qs:
            trades.append({
                'id': t.id,
                'side': t.trade_type,
                'quantity': float(t.quantity),
                'price': float(t.price),
                'date': t.executed_at.date().isoformat(),
                'timestamp': t.executed_at.isoformat(),
            })

        logger.debug(
            f"[chart-tooltip] all_asset={all_asset.id} prices={len(prices)} trades={len(trades)} days={days}"
        )

        return Response({
            'all_asset_id': all_asset.id,
            'all_asset_symbol': all_asset.symbol,
            'prices_count': len(prices),
            'trades_count': len(trades),
            'days': days,
            'trades_days': trades_days,
            'prices': prices,
            'trades': trades,
        })
    
    @action(detail=True, methods=['get'])
    def current_price(self, request, pk=None):
        """
        GET /api/all-assets/{id}/current_price/
        Récupère le prix actuel depuis Yahoo Finance pour cet AllAsset.
        
        Ne nécessite pas d'historique synchronisé - récupère directement depuis Yahoo.
        """
        from ..services.data_providers.yahoo_finance import YahooFinanceService
        
        all_asset = self.get_object()
        
        if not all_asset.symbole_yahoo or all_asset.symbole_yahoo in ['Not_searched', 'not_found', 'manual']:
            return Response({
                'success': False,
                'message': f'No validated Yahoo symbol for {all_asset.symbol}',
                'price': None
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            yahoo_service = YahooFinanceService()
            price = yahoo_service.get_current_price(all_asset.symbole_yahoo)
            
            if price is None:
                return Response({
                    'success': False,
                    'message': f'Could not fetch current price for {all_asset.symbole_yahoo}',
                    'price': None
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                'success': True,
                'all_asset_id': all_asset.id,
                'all_asset_symbol': all_asset.symbol,
                'yahoo_symbol': all_asset.symbole_yahoo,
                'price': float(price),
                'currency': all_asset.currency or 'USD'
            })
            
        except Exception as e:
            logger = logging.getLogger('trading.api.assets')
            logger.exception(f"Error fetching current price for {all_asset.symbol}: {e}")
            return Response({
                'success': False,
                'message': str(e),
                'price': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def validate_single_yahoo(self, request, pk=None):
        """
        POST /api/all-assets/{id}/validate_single_yahoo/
        Valide le symbole Yahoo pour un AllAsset spécifique.
        """
        from ..services.yahoo_validator import validate_single_asset
        from ..utils.yahoo_config import ValidationStatus
        from ..constants import DEFAULT_PRICE_TOLERANCE_PERCENT
        from ..services.broker_service import BrokerService
        from ..models import BrokerAccount
        from django.utils import timezone
        import logging
        
        logger = logging.getLogger('trading.api.assets')
        all_asset = self.get_object()
        
        try:
            # Récupérer la configuration broker si nécessaire (pour Saxo)
            broker_config = {}
            if all_asset.platform == 'SAXO':
                saxo_account = BrokerAccount.objects.filter(
                    broker_type='SAXO',
                    user=request.user,
                    is_active=True
                ).first()
                if saxo_account:
                    try:
                        broker_service = BrokerService(request.user)
                        broker = broker_service.get_broker_instance(saxo_account, use_cache=True)
                        if broker.authenticate():
                            broker_config['access_token'] = broker.access_token
                            broker_config['base_url'] = broker.base_url
                    except Exception as e:
                        logger.warning(f"Could not get valid Saxo token: {e}")
            
            # Valider l'asset
            result = validate_single_asset(
                all_asset,
                broker_config=broker_config,
                tolerance_percent=DEFAULT_PRICE_TOLERANCE_PERCENT
            )
            
            # Sauvegarder le résultat
            all_asset.symbole_yahoo = result.yahoo_symbol
            all_asset.yahoo_validation_method = result.method
            all_asset.yahoo_validated_at = timezone.now()
            all_asset.save(update_fields=[
                'symbole_yahoo',
                'yahoo_validation_method',
                'yahoo_validated_at'
            ])
            
            return Response({
                'success': True,
                'yahoo_symbol': result.yahoo_symbol,
                'status': result.status,
                'method': result.method,
                'message': f'Symbole Yahoo trouvé: {result.yahoo_symbol}' if result.yahoo_symbol not in ['Not_searched', 'not_found', 'manual'] else 'Symbole Yahoo non trouvé'
            })
            
        except Exception as e:
            logger.exception(f"Error validating Yahoo symbol for {all_asset.symbol}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def sync_price_history(self, request, pk=None):
        """
        POST /api/all-assets/{id}/sync_price_history/
        Synchronise l'historique des prix pour un AllAsset spécifique.
        
        Body:
        {
            "days": 365,  // nombre de jours (défaut: 365)
            "interval": "1d"  // intervalle Yahoo Finance: "1d", "1wk", "1mo" (défaut: "1d")
        }
        """
        from ..services.sync.all_asset_price_sync_service import AllAssetPriceSyncService
        import logging
        
        logger = logging.getLogger('trading.api.assets')
        all_asset = self.get_object()
        
        try:
            # Récupérer les paramètres
            days = int(request.data.get('days', 365))
            interval = request.data.get('interval', '1d')
            
            # Valider l'intervalle
            if interval not in ['1d', '1wk', '1mo']:
                return Response({
                    'success': False,
                    'error': f'Interval invalide. Doit être "1d", "1wk" ou "1mo"'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Synchroniser
            service = AllAssetPriceSyncService()
            result = service.sync_from_yahoo_finance(
                all_asset=all_asset,
                days=days,
                interval=interval
            )
            
            return Response(result)
            
        except Exception as e:
            logger.exception(f"Error syncing price history for {all_asset.symbol}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================
# VIEWSETS ASSETS ENRICHIS
# ============================================

class AssetViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les assets enrichis (données Yahoo, etc.).
    
    Actions personnalisées :
    - GET /api/assets/1/prices/ → Historique des prix
    - GET /api/assets/1/positions/ → Positions sur cet asset
    - GET /api/assets/1/trades/ → Trades sur cet asset
    - GET /api/assets/1/summary/ → Résumé complet
    - POST /api/assets/1/update_price/ → Met à jour le prix
    """
    queryset = Asset.objects.filter(is_active=True)
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    
    filterset_fields = ['asset_type', 'currency', 'is_active', 'is_favorite']
    search_fields = ['symbol', 'name', 'sector', 'industry']
    ordering_fields = ['symbol', 'name', 'current_price', 'market_cap', 'pe_ratio']
    ordering = ['symbol']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtrage personnalisé pour is_tracked
        # Si is_tracked=true, on retourne (is_tracked OR is_favorite)
        is_tracked = self.request.query_params.get('is_tracked')
        if is_tracked and is_tracked.lower() == 'true':
            queryset = queryset.filter(Q(is_tracked=True) | Q(is_favorite=True))
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def prices(self, request, pk=None):
        """
        GET /api/assets/1/prices/
        Récupère l'historique des prix (100 derniers jours).
        """
        asset = self.get_object()
        days = int(request.query_params.get('days', 100))
        prices = AssetPrice.objects.filter(asset=asset).order_by('-date')[:days]
        serializer = AssetPriceSerializer(prices, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def positions(self, request, pk=None):
        """
        GET /api/assets/1/positions/
        Récupère les positions de l'utilisateur sur cet asset.
        """
        asset = self.get_object()
        positions = Position.objects.filter(asset=asset, user=request.user)
        serializer = PositionSerializer(positions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def trades(self, request, pk=None):
        """
        GET /api/assets/1/trades/
        Récupère les trades de l'utilisateur sur cet asset.
        """
        asset = self.get_object()
        trades = Trade.objects.filter(asset=asset, user=request.user).order_by('-executed_at')
        serializer = TradeSerializer(trades, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """
        GET /api/assets/1/summary/
        Résumé complet de l'asset avec positions et statistiques.
        """
        asset = self.get_object()
        
        positions = Position.objects.filter(asset=asset, user=request.user)
        open_positions = positions.filter(is_open=True)
        trades = Trade.objects.filter(asset=asset, user=request.user)
        
        # Calculs
        total_quantity = sum(p.quantity for p in open_positions)
        total_value = sum((p.current_price or p.entry_price) * p.quantity for p in open_positions)
        total_pnl = sum(p.pnl or 0 for p in open_positions)
        
        return Response({
            'asset': AssetSerializer(asset).data,
            'positions': {
                'open_count': open_positions.count(),
                'closed_count': positions.filter(is_open=False).count(),
                'total_quantity': float(total_quantity),
                'total_value': float(total_value),
                'total_pnl': float(total_pnl),
            },
            'trades': {
                'total_count': trades.count(),
                'buy_count': trades.filter(trade_type='BUY').count(),
                'sell_count': trades.filter(trade_type='SELL').count(),
            }
        })
    
    @action(detail=True, methods=['post'])
    def update_price(self, request, pk=None):
        """
        POST /api/assets/1/update_price/
        Met à jour le prix de l'asset.
        Body: {"price": 150.50}
        """
        asset = self.get_object()
        new_price = request.data.get('price')
        
        if new_price is None:
            return Response({'error': 'price is required'}, status=400)
        
        try:
            asset.current_price = float(new_price)
            asset.price_updated_at = timezone.now()
            asset.save()
            return Response(AssetSerializer(asset).data)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid price format'}, status=400)


# ============================================
# VIEWSETS TRADING
# ============================================

class PositionViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les positions.
    
    Filtré automatiquement par utilisateur connecté.
    
    Actions personnalisées :
    - GET /api/positions/open/ → Positions ouvertes
    - GET /api/positions/closed/ → Positions fermées
    - GET /api/positions/summary/ → Résumé du portefeuille
    - GET /api/positions/by_broker/ → Positions groupées par broker
    - POST /api/positions/1/close/ → Fermer une position
    """
    serializer_class = PositionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    
    filterset_fields = ['is_open', 'side', 'broker', 'strategy']
    search_fields = ['all_asset__symbol', 'all_asset__name', 'asset__symbol', 'asset__name']
    ordering_fields = ['opened_at', 'entry_price', 'quantity']
    ordering = ['-opened_at']
    
    def get_queryset(self):
        """Filtrer par utilisateur connecté."""
        # Perf: éviter N+1 queries sur les relations utilisées par les serializers.
        return (
            Position.objects.filter(user=self.request.user)
            .select_related('all_asset', 'asset', 'broker', 'strategy')
            # Perf: évite de charger le JSON volumineux de l'historique prix
            .defer('all_asset__price_history_json')
        )

    def get_serializer_class(self):
        # Perf: pour la liste, on renvoie un payload minimal.
        if getattr(self, 'action', None) == 'list':
            from .serializers import PositionListSerializer
            return PositionListSerializer
        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Opt-in uniquement : sinon chaque position déclenche un appel Yahoo (très lent).
        q = self.request.query_params.get('include_yahoo_price', '')
        context['include_yahoo_price'] = str(q).lower() in ('1', 'true', 'yes')
        return context
    
    def perform_create(self, serializer):
        """Ajouter l'utilisateur automatiquement lors de la création."""
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def open(self, request):
        """GET /api/positions/open/ → Positions ouvertes uniquement."""
        positions = self.filter_queryset(self.get_queryset().filter(is_open=True))
        page = self.paginate_queryset(positions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(positions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def closed(self, request):
        """GET /api/positions/closed/ → Positions fermées."""
        positions = self.filter_queryset(self.get_queryset().filter(is_open=False))
        page = self.paginate_queryset(positions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(positions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        GET /api/positions/summary/
        Résumé complet du portefeuille.
        """
        positions = self.get_queryset().filter(is_open=True)
        
        # Calculs agrégés
        total_value = sum((p.current_price or p.entry_price) * p.quantity for p in positions)
        total_pnl = sum(p.pnl or 0 for p in positions)
        total_pnl_percent = (total_pnl / total_value * 100) if total_value else 0
        
        # Par side
        long_positions = positions.filter(side='LONG')
        short_positions = positions.filter(side='SHORT')
        
        return Response({
            'total_positions': positions.count(),
            'total_value': float(total_value),
            'total_pnl': float(total_pnl),
            'total_pnl_percent': round(total_pnl_percent, 2),
            'long': {
                'count': long_positions.count(),
                'value': float(sum((p.current_price or p.entry_price) * p.quantity for p in long_positions)),
            },
            'short': {
                'count': short_positions.count(),
                'value': float(sum((p.current_price or p.entry_price) * p.quantity for p in short_positions)),
            },
            'winning': positions.filter(current_price__gt=F('entry_price')).count(),
            'losing': positions.filter(current_price__lt=F('entry_price')).count(),
        })
    
    @action(detail=False, methods=['get'])
    def by_broker(self, request):
        """
        GET /api/positions/by_broker/
        Positions groupées par broker.
        """
        positions = self.get_queryset().filter(is_open=True)
        by_broker = positions.values('broker__name').annotate(
            count=Count('id'),
            total_quantity=Sum('quantity')
        ).order_by('-count')
        
        return Response(list(by_broker))
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """
        POST /api/positions/1/close/
        Ferme une position.
        Body optionnel: {"close_price": 155.50}
        """
        position = self.get_object()
        
        if not position.is_open:
            return Response({'error': 'Position is already closed'}, status=400)
        
        close_price = request.data.get('close_price', position.current_price)
        
        position.is_open = False
        position.closed_at = timezone.now()
        if close_price:
            position.current_price = close_price
        position.save()
        
        return Response(PositionSerializer(position).data)


class TradeViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les trades.
    
    Actions personnalisées :
    - GET /api/trades/recent/ → 20 derniers trades
    - GET /api/trades/today/ → Trades du jour
    - GET /api/trades/stats/ → Statistiques de trading
    - GET /api/trades/by_asset/ → Trades groupés par asset
    """
    serializer_class = TradeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    
    filterset_fields = ['trade_type', 'broker', 'asset']
    search_fields = ['all_asset__symbol', 'all_asset__name', 'asset__symbol', 'broker_trade_id']
    ordering_fields = ['executed_at', 'price', 'quantity']
    ordering = ['-executed_at']
    
    def get_queryset(self):
        # Perf: éviter N+1 queries sur les relations utilisées par les serializers.
        return (
            Trade.objects.filter(user=self.request.user)
            .select_related('all_asset', 'asset', 'broker', 'position', 'strategy')
            # Perf: évite de charger le JSON volumineux de l'historique prix
            .defer('all_asset__price_history_json')
        )

    def get_serializer_class(self):
        # Perf: pour la liste, on renvoie un payload minimal.
        if getattr(self, 'action', None) == 'list':
            from .serializers import TradeListSerializer
            return TradeListSerializer
        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Opt-in uniquement : sinon chaque trade déclenche un appel Yahoo (très lent).
        q = self.request.query_params.get('include_yahoo_price', '')
        context['include_yahoo_price'] = str(q).lower() in ('1', 'true', 'yes')
        return context
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """GET /api/trades/recent/ → 20 derniers trades."""
        limit = int(request.query_params.get('limit', 20))
        trades = self.get_queryset()[:limit]
        serializer = self.get_serializer(trades, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """GET /api/trades/today/ → Trades du jour."""
        today = timezone.now().date()
        trades = self.get_queryset().filter(executed_at__date=today)
        serializer = self.get_serializer(trades, many=True)
        return Response({
            'date': today.isoformat(),
            'count': trades.count(),
            'trades': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        GET /api/trades/stats/
        Statistiques de trading.
        """
        trades = self.get_queryset()
        
        # Période (défaut: 30 jours)
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        recent_trades = trades.filter(executed_at__gte=since)
        
        buy_trades = recent_trades.filter(trade_type='BUY')
        sell_trades = recent_trades.filter(trade_type='SELL')
        
        return Response({
            'period_days': days,
            'total_trades': recent_trades.count(),
            'buy_trades': buy_trades.count(),
            'sell_trades': sell_trades.count(),
            'total_volume': float(sum(t.quantity * t.price for t in recent_trades)),
            'total_fees': float(sum(t.fees for t in recent_trades)),
            'avg_trade_size': float(recent_trades.aggregate(avg=Avg('quantity'))['avg'] or 0),
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        GET /api/trades/statistics/
        Alias pour /api/trades/stats/ pour compatibilité avec le frontend.
        Retourne les statistiques avec win_rate.
        """
        trades = self.get_queryset()
        
        # Période (défaut: 30 jours)
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        recent_trades = trades.filter(executed_at__gte=since)
        
        # Utiliser 'trade_type' (le modèle Trade n'a pas de champ side)
        buy_trades = recent_trades.filter(trade_type='BUY')
        sell_trades = recent_trades.filter(trade_type='SELL')
        
        # Calculer le win_rate si possible
        # Vérifier si le modèle Trade a un champ pour calculer win/loss
        total_volume = float(sum((t.quantity or 0) * (t.price or 0) for t in recent_trades))
        total_fees = float(sum(t.fees or 0 for t in recent_trades))
        
        # Win rate simplifié - calcul basé sur les trades rentables
        # Si vous avez un champ PnL ou une autre logique, ajustez ici
        win_rate = 50.0  # Valeur par défaut
        
        # Essayer de calculer un vrai win_rate si possible
        # Q est déjà importé en haut du fichier (ligne 17)
        try:
            # Si les trades ont une position liée avec PnL
            trades_with_pnl = recent_trades.exclude(position__isnull=True)
            if trades_with_pnl.exists():
                # Vérifier si les positions ont un PnL calculé
                winning_count = trades_with_pnl.filter(
                    Q(position__pnl__gt=0) | Q(position__pnl_percent__gt=0)
                ).count()
                total_with_pnl = trades_with_pnl.count()
                if total_with_pnl > 0:
                    win_rate = (winning_count / total_with_pnl) * 100
        except Exception as e:
            # Si le calcul échoue, utiliser la valeur par défaut
            logger = logging.getLogger('trading.api.trades')
            logger.debug(f"Could not calculate win_rate: {e}")
            pass
        
        return Response({
            'period_days': days,
            'total_trades': recent_trades.count(),
            'buy_trades': buy_trades.count(),
            'sell_trades': sell_trades.count(),
            'total_volume': total_volume,
            'total_fees': total_fees,
            'avg_trade_size': float(recent_trades.aggregate(avg=Avg('quantity'))['avg'] or 0),
            'win_rate': round(win_rate, 2),
        })
    
    @action(detail=False, methods=['get'])
    def by_asset(self, request):
        """GET /api/trades/by_asset/ → Trades groupés par asset."""
        trades = self.get_queryset()
        by_asset = trades.values('asset__symbol', 'asset__name').annotate(
            count=Count('id'),
            total_quantity=Sum('quantity'),
            buy_count=Count('id', filter=Q(trade_type='BUY')),
            sell_count=Count('id', filter=Q(trade_type='SELL')),
        ).order_by('-count')[:20]
        
        return Response(list(by_asset))


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les ordres.
    
    Actions personnalisées :
    - GET /api/orders/pending/ → Ordres en attente
    - GET /api/orders/filled/ → Ordres exécutés
    - POST /api/orders/1/cancel/ → Annuler un ordre
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    
    filterset_fields = ['order_type', 'side', 'status', 'broker', 'asset']
    search_fields = ['asset__symbol', 'broker_order_id']
    ordering_fields = ['created_at', 'price', 'quantity']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        order = serializer.save(user=self.request.user)
        if order.asset_id and not order.all_asset_id:
            try:
                asset = Asset.objects.select_related('all_asset').get(pk=order.asset_id)
            except Asset.DoesNotExist:
                return
            broker_type = getattr(order.broker, 'broker_type', None) if order.broker_id else None
            aa = resolve_all_asset_from_asset(asset, broker_type)
            if aa:
                if not asset.all_asset_id:
                    asset.all_asset = aa
                    asset.save(update_fields=['all_asset'])
                order.all_asset = aa
                order.save(update_fields=['all_asset'])
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """GET /api/orders/pending/ → Ordres en attente."""
        orders = self.filter_queryset(
            self.get_queryset()
            .filter(status__in=['PENDING', 'OPEN', 'PARTIALLY_FILLED'])
            .select_related('all_asset', 'broker', 'asset', 'asset__all_asset')
        )
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='backfill-all-asset')
    def backfill_all_asset(self, request):
        """
        POST /api/orders/backfill-all-asset/
        Renseigne Order.all_asset via Asset.all_asset ou résolution catalogue (symbole normalisé).
        """
        qs = (
            self.get_queryset()
            .filter(all_asset__isnull=True)
            .exclude(asset__isnull=True)
            .select_related('asset', 'asset__all_asset', 'broker')
        )
        updated = 0
        for order in qs:
            if not order.asset_id or not order.asset:
                continue
            asset = order.asset
            broker_type = getattr(order.broker, 'broker_type', None) if order.broker_id else None
            aa = resolve_all_asset_from_asset(asset, broker_type)
            if aa and not asset.all_asset_id:
                asset.all_asset = aa
                asset.save(update_fields=['all_asset'])
            if aa:
                order.all_asset = aa
                order.save(update_fields=['all_asset'])
                updated += 1
        return Response({'updated': updated, 'message': f'{updated} ordre(s) mis à jour.'})
    
    @action(detail=False, methods=['get'])
    def filled(self, request):
        """GET /api/orders/filled/ → Ordres exécutés."""
        orders = self.filter_queryset(self.get_queryset().filter(status='FILLED'))
        page = self.paginate_queryset(orders)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        POST /api/orders/1/cancel/
        Annule un ordre en attente (localement).
        Si l'ordre a un broker_order_id, essaie aussi d'annuler chez le broker.
        """
        order = self.get_object()
        
        if order.status in ['FILLED', 'CANCELLED', 'EXPIRED']:
            return Response(
                {'error': f'Cannot cancel order with status {order.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Si l'ordre a un broker_order_id, essayer d'annuler chez le broker
        if order.broker_order_id:
            try:
                broker_account = BrokerAccount.objects.filter(
                    user=request.user,
                    broker=order.broker
                ).first()
                
                if broker_account:
                    service = BrokerService(request.user)
                    result = service.cancel_order(
                        broker_account=broker_account,
                        order_id=order.broker_order_id,
                        symbol=order.asset.symbol if order.asset else None
                    )
                    
                    if not result.success:
                        # Si l'ordre n'existe pas chez le broker (404), considérer qu'il est déjà annulé
                        error_msg = result.error or ''
                        if 'not found' in error_msg.lower() or '404' in error_msg or 'does not exist' in error_msg.lower():
                            logger.info(f"Order {order.broker_order_id} not found at broker, considering it already cancelled")
                            # On continue avec l'annulation locale
                        else:
                            # Pour les autres erreurs, on retourne l'erreur
                            return Response(
                                {'error': f'Failed to cancel order at broker: {result.error}'},
                                status=status.HTTP_400_BAD_REQUEST
                            )
            except Exception as e:
                logger.warning(f"Error cancelling order at broker: {e}")
                # Continue avec l'annulation locale même si le broker échoue
        
        order.status = 'CANCELLED'
        order.save()
        
        return Response({
            'status': 'Order cancelled',
            'order': OrderSerializer(order).data
        })
    
    @action(detail=False, methods=['post'])
    def place(self, request):
        """
        POST /api/orders/place/
        Place un ordre directement via le broker.
        
        Flux basé sur AllAssets comme source de vérité :
        1. Chercher dans AllAssets (par symbole et plateforme)
        2. Créer/find Asset depuis AllAssets
        3. Pour Saxo : utiliser saxo_uic depuis AllAssets
        4. Pour Binance : utiliser symbole depuis AllAssets
        
        Body:
        {
            "broker_account_id": 1,
            "symbol": "AAPL" ou "AAPL:xnas",  // Accepte les variantes
            "all_asset_id": 123,  // optionnel, si fourni utilise directement
            "side": "BUY",
            "quantity": "10",
            "order_type": "MARKET",
            "price": "150.25",  // optionnel pour LIMIT
            "stop_price": "145.00"  // optionnel pour STOP
        }
        """
        broker_account_id = request.data.get('broker_account_id')
        symbol_raw = request.data.get('symbol', '').strip()
        all_asset_id = request.data.get('all_asset_id')  # Optionnel : ID AllAssets direct
        side = request.data.get('side')
        quantity = request.data.get('quantity')
        order_type = request.data.get('order_type', 'MARKET')
        price = request.data.get('price')
        stop_price = request.data.get('stop_price')
        
        # Nettoyer le symbole (enlever les suffixes comme :xnas, :nasdaq, etc.)
        symbol_clean = symbol_raw.split(':')[0].strip().upper()
        symbol_clean = symbol_clean.split('_')[0].strip()  # Enlever _0, _1, etc.
        
        # Validation
        if not all([broker_account_id, symbol_clean if not all_asset_id else True, side, quantity]):
            return Response(
                {'error': 'Missing required fields: broker_account_id, symbol (or all_asset_id), side, quantity'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get broker account
            broker_account = BrokerAccount.objects.get(
                id=broker_account_id,
                user=request.user
            )
        except BrokerAccount.DoesNotExist:
            return Response(
                {'error': 'Broker account not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # ✅ CRITIQUE: Chercher AllAssets d'abord (source de vérité)
        all_asset = None
        broker_type = broker_account.broker.broker_type
        
        if all_asset_id:
            # Utiliser directement l'ID AllAssets fourni
            try:
                all_asset = AllAssets.objects.get(id=all_asset_id)
            except AllAssets.DoesNotExist:
                return Response(
                    {'error': f'AllAssets with id {all_asset_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Rechercher dans AllAssets par symbole et plateforme
            # Recherche exacte d'abord
            all_asset = AllAssets.objects.filter(
                symbol__iexact=symbol_clean,
                platform=broker_type,
                is_tradable=True
            ).first()
            
            # Si pas trouvé, recherche partielle
            if not all_asset:
                all_asset = AllAssets.objects.filter(
                    Q(symbol__icontains=symbol_clean) | Q(name__icontains=symbol_clean),
                    platform=broker_type,
                    is_tradable=True
                ).order_by('symbol').first()
        
        if not all_asset:
            return Response(
                {
                    'error': f'Asset not found for symbol "{symbol_clean}" on platform {broker_type}. Please sync assets from broker first.'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # ✅ Pour Saxo : vérifier que l'UIC existe
        if broker_type == 'SAXO' and not all_asset.saxo_uic:
            return Response(
                {
                    'error': f'UIC manquant pour {all_asset.symbol}. Veuillez synchroniser les assets depuis Saxo d\'abord.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # ✅ Créer ou trouver Asset depuis AllAssets
        asset, asset_created = Asset.objects.get_or_create(
            symbol=all_asset.symbol,
            defaults={
                'all_asset': all_asset,
                'name': all_asset.name,
                'asset_type': all_asset.asset_type,
                'currency': all_asset.currency,
                'exchange': all_asset.exchange or '',
            }
        )
        
        # Mettre à jour le lien all_asset si nécessaire
        if not asset.all_asset:
            asset.all_asset = all_asset
            asset.save()
        
        # Convert quantity to Decimal
        from decimal import Decimal
        try:
            quantity_decimal = Decimal(str(quantity))
            price_decimal = Decimal(str(price)) if price else None
            stop_price_decimal = Decimal(str(stop_price)) if stop_price else None
        except (ValueError, TypeError) as e:
            return Response(
                {'error': f'Invalid numeric value: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # ✅ Préparer les paramètres spécifiques au broker
        broker_kwargs = {}
        
        if broker_type == 'SAXO':
            # Pour Saxo, passer l'UIC directement
            broker_kwargs['uic'] = all_asset.saxo_uic
            broker_kwargs['asset_type'] = all_asset.asset_type
            # Utiliser le symbole exact depuis AllAssets
            trading_symbol = all_asset.symbol
        elif broker_type == 'BINANCE':
            # Pour Binance, utiliser le symbole depuis AllAssets
            trading_symbol = all_asset.symbol
            # Ajouter suffixe si nécessaire (mais normalement AllAssets a déjà le bon format)
            if not any(trading_symbol.endswith(suffix) for suffix in ['USDT', 'EUR', 'BTC', 'BNB', 'ETH']):
                # Tenter d'ajouter USDT si pas de suffixe
                trading_symbol = f"{trading_symbol}USDT"
        else:
            trading_symbol = all_asset.symbol
        
        # Place order via broker
        service = BrokerService(request.user)
        result = service.place_order(
            broker_account=broker_account,
            symbol=trading_symbol,  # Symbole depuis AllAssets
            side=side.upper(),
            quantity=quantity_decimal,
            order_type=order_type.upper(),
            price=price_decimal,
            stop_price=stop_price_decimal,
            **broker_kwargs  # Paramètres spécifiques (uic pour Saxo, etc.)
        )
        
        if not result.success:
            return Response(
                {'error': result.error},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create or update order in database
        order, created = Order.objects.update_or_create(
            user=request.user,
            broker=broker_account.broker,
            asset=asset,
            broker_order_id=result.order_id or '',
            defaults={
                'order_type': order_type.upper(),
                'side': side.upper(),
                'quantity': quantity_decimal,
                'price': price_decimal,
                'stop_price': stop_price_decimal,
                'status': 'OPEN' if result.success else 'REJECTED',
                'all_asset': all_asset,
            }
        )
        
        return Response({
            'success': True,
            'message': result.message,
            'order': OrderSerializer(order).data,
            'broker_result': {
                'order_id': result.order_id,
                'message': result.message
            }
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def place_broker(self, request, pk=None):
        """
        POST /api/orders/{id}/place_broker/
        Place un ordre existant (avec statut PENDING) via le broker.
        """
        order = self.get_object()
        
        if order.status != 'PENDING':
            return Response(
                {'error': f'Can only place orders with status PENDING, current status: {order.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get broker account
        try:
            broker_account = BrokerAccount.objects.get(
                user=request.user,
                broker=order.broker
            )
        except BrokerAccount.DoesNotExist:
            return Response(
                {'error': 'Broker account not found for this broker'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Place order via broker
        service = BrokerService(request.user)
        result = service.place_order(
            broker_account=broker_account,
            symbol=order.asset.symbol,
            side=order.side,
            quantity=order.quantity,
            order_type=order.order_type,
            price=order.price,
            stop_price=order.stop_price
        )
        
        if not result.success:
            order.status = 'REJECTED'
            order.save()
            return Response(
                {'error': result.error},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update order with broker response
        order.broker_order_id = result.order_id or order.broker_order_id
        order.status = 'OPEN'
        if order.asset_id and not order.all_asset_id:
            try:
                a = Asset.objects.select_related('all_asset').get(pk=order.asset_id)
                if a.all_asset_id:
                    order.all_asset = a.all_asset
            except Asset.DoesNotExist:
                pass
        order.save()
        
        return Response({
            'success': True,
            'message': result.message,
            'order': OrderSerializer(order).data,
            'broker_result': {
                'order_id': result.order_id,
                'message': result.message
            }
        })
    
    @action(detail=True, methods=['post'])
    def cancel_broker(self, request, pk=None):
        """
        POST /api/orders/{id}/cancel_broker/
        Annule un ordre chez le broker (nécessite un broker_order_id).
        """
        order = self.get_object()
        
        if not order.broker_order_id:
            return Response(
                {'error': 'Order does not have a broker_order_id. Cannot cancel at broker.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if order.status in ['FILLED', 'CANCELLED', 'EXPIRED']:
            return Response(
                {'error': f'Cannot cancel order with status {order.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get broker account
        try:
            broker_account = BrokerAccount.objects.get(
                user=request.user,
                broker=order.broker
            )
        except BrokerAccount.DoesNotExist:
            return Response(
                {'error': 'Broker account not found for this broker'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Cancel order at broker
        service = BrokerService(request.user)
        result = service.cancel_order(
            broker_account=broker_account,
            order_id=order.broker_order_id,
            symbol=order.asset.symbol if order.asset else None
        )
        
        if not result.success:
            # Si l'ordre n'existe pas chez le broker (404), considérer qu'il est déjà annulé
            error_msg = result.error or ''
            if 'not found' in error_msg.lower() or '404' in error_msg or 'does not exist' in error_msg.lower() or 'already been cancelled' in error_msg.lower():
                logger.info(f"Order {order.broker_order_id} not found at broker, marking as cancelled locally")
                # Mettre à jour le statut local à CANCELLED même si l'ordre n'existe pas chez le broker
                order.status = 'CANCELLED'
                order.save()
                
                return Response({
                    'success': True,
                    'message': 'Order was already cancelled at broker, status updated locally',
                    'order': OrderSerializer(order).data
                })
            else:
                # Pour les autres erreurs, retourner l'erreur
                return Response(
                    {'error': result.error},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Update order status
        order.status = 'CANCELLED'
        order.save()
        
        return Response({
            'success': True,
            'message': 'Order cancelled at broker',
            'order': OrderSerializer(order).data
        })
    
    @action(detail=False, methods=['post'])
    def get_asset_price(self, request):
        """
        POST /api/orders/get_asset_price/
        Récupère le prix actuel d'un actif depuis le broker ET Yahoo Finance (en parallèle).
        
        Body:
        {
            "broker_account_id": 1,
            "symbol": "AAPL",
            "all_asset_id": 123  // optionnel
        }
        
        Returns:
        {
            "success": true,
            "broker_price": {
                "price": 150.25,
                "currency": "USD",
                "source": "SAXO"
            },
            "yahoo_data": {
                "price": 150.30,
                "symbol": "AAPL",
                "available": true
            }
        }
        """
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
        from ..services.data_providers.yahoo_finance import YahooFinanceService
        from decimal import Decimal
        
        broker_account_id = request.data.get('broker_account_id')
        symbol = request.data.get('symbol', '').strip().upper()
        all_asset_id = request.data.get('all_asset_id')
        
        if not broker_account_id or not symbol:
            return Response(
                {'error': 'broker_account_id and symbol are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            broker_account = BrokerAccount.objects.get(
                id=broker_account_id,
                user=request.user
            )
        except BrokerAccount.DoesNotExist:
            return Response(
                {'error': 'Broker account not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Récupérer AllAssets
        all_asset = None
        if all_asset_id:
            try:
                all_asset = AllAssets.objects.get(id=all_asset_id)
            except AllAssets.DoesNotExist:
                pass
        
        if not all_asset and symbol:
            all_asset = AllAssets.objects.filter(
                symbol__iexact=symbol,
                platform=broker_account.broker.broker_type,
                is_tradable=True
            ).first()
        
        # Fonction pour récupérer le prix broker
        def get_broker_price():
            try:
                service = BrokerService(request.user)
                broker_instance = service.get_broker_instance(broker_account)
                
                if not broker_instance.authenticate():
                    logger.warning(f"Failed to authenticate with {broker_account.broker.broker_type}")
                    return {'error': 'Failed to authenticate with broker'}
                
                price_params = {}
                
                # Pour Saxo, utiliser UIC et asset_type si disponibles
                if broker_account.broker.broker_type == 'SAXO':
                    if all_asset and all_asset.saxo_uic:
                        price_params['uic'] = all_asset.saxo_uic
                        price_params['asset_type'] = all_asset.asset_type or 'Stock'
                        logger.debug(f"Using UIC {all_asset.saxo_uic} and asset_type {price_params['asset_type']} for {symbol}")
                    else:
                        # Essayer de trouver l'UIC depuis le symbole
                        logger.debug(f"No UIC found for {symbol}, will try to find it via symbol")
                        price_params['asset_type'] = all_asset.asset_type if all_asset else 'Stock'
                
                logger.debug(f"Fetching price from {broker_account.broker.broker_type} for symbol {symbol} with params: {price_params}")
                
                price_data = broker_instance.get_asset_price(
                    symbol=symbol,
                    **price_params
                )
                
                logger.debug(f"Price data returned from broker: {type(price_data)}, value: {price_data}")
                
                if price_data is not None:
                    # Extraire le prix selon le format retourné par le broker
                    price_value = None
                    if isinstance(price_data, (Decimal, int, float)):
                        price_value = float(price_data)
                        logger.debug(f"Extracted price value (numeric): {price_value}")
                    elif isinstance(price_data, dict):
                        # Chercher le prix dans différentes clés possibles
                        logger.debug(f"Price data is dict with keys: {list(price_data.keys())}")
                        price_value = (
                            price_data.get('price') or 
                            price_data.get('last') or 
                            price_data.get('close') or
                            price_data.get('lastPrice')
                        )
                        if price_value:
                            price_value = float(price_value)
                            logger.debug(f"Extracted price value (from dict): {price_value}")
                    
                    if price_value and price_value > 0:
                        logger.info(f"Successfully retrieved price {price_value} from {broker_account.broker.broker_type} for {symbol}")
                        return {
                            'price': price_value,
                            'currency': all_asset.currency if all_asset else 'USD',
                            'source': broker_account.broker.broker_type
                        }
                    else:
                        logger.warning(f"Invalid price value: {price_value} for {symbol}")
                
                error_msg = f'Could not retrieve price from {broker_account.broker.broker_type} for {symbol}'
                if broker_account.broker.broker_type == 'SAXO' and not all_asset:
                    error_msg += ' (asset not found in AllAssets)'
                elif broker_account.broker.broker_type == 'SAXO' and all_asset and not all_asset.saxo_uic:
                    error_msg += f' (UIC missing for {symbol})'
                logger.warning(error_msg)
                return {'error': error_msg}
                
            except Exception as e:
                logger.exception(f"Error getting broker price for {symbol}: {e}")
                return {'error': f'Error: {str(e)}'}
        
        # Fonction pour récupérer le prix Yahoo
        def get_yahoo_price_data():
            try:
                # Récupérer le symbole Yahoo depuis AllAssets
                yahoo_symbol = None
                if all_asset and all_asset.symbole_yahoo:
                    if all_asset.symbole_yahoo not in ['Not_searched', 'not_found', 'manual']:
                        yahoo_symbol = all_asset.symbole_yahoo
                
                # Si pas de symbole Yahoo validé, nettoyer le symbole original
                if not yahoo_symbol:
                    # Nettoyer le symbole (enlever :XNAS, etc.)
                    yahoo_symbol = symbol.split(':')[0].strip().upper()
                
                # Nettoyer le symbole Yahoo si il contient des extensions
                if yahoo_symbol and (':' in yahoo_symbol or '.' in yahoo_symbol):
                    # Enlever les extensions de marché (:XNAS, .PA, etc.)
                    parts = yahoo_symbol.replace('.', ':').split(':')
                    yahoo_symbol = parts[0].strip().upper()
                
                logger.debug(f"Yahoo symbol to try: {yahoo_symbol} (original: {symbol})")
                
                # Utiliser YahooFinanceService
                yahoo_service = YahooFinanceService()
                if not yahoo_service.is_available:
                    return {'available': False, 'error': 'Yahoo Finance service not available'}
                
                # Essayer plusieurs variantes de symboles
                symbols_to_try = []
                
                # D'abord le symbole nettoyé
                if yahoo_symbol:
                    symbols_to_try.append(yahoo_symbol)
                
                # Ajouter des variantes si c'est un symbole simple
                if yahoo_symbol and len(yahoo_symbol) <= 5 and yahoo_symbol.isalpha():
                    # Pour les actions US, essayer juste le symbole de base
                    # Pour les cryptos, ajouter le suffixe USD
                    if broker_account.broker.broker_type == 'BINANCE':
                        if not any(yahoo_symbol.endswith(s) for s in ['USD', 'EUR', 'USDT']):
                            symbols_to_try.append(f"{yahoo_symbol}-USD")
                
                # Si le symbole original était différent, l'essayer aussi
                clean_original = symbol.split(':')[0].strip().upper()
                if clean_original != yahoo_symbol and clean_original not in symbols_to_try:
                    symbols_to_try.append(clean_original)
                
                logger.debug(f"Trying Yahoo symbols: {symbols_to_try}")
                
                # Essayer chaque symbole jusqu'à en trouver un qui fonctionne
                for sym in symbols_to_try:
                    try:
                        price = yahoo_service.get_current_price(sym)
                        if price is not None:
                            logger.info(f"Yahoo price found for {sym}: {price}")
                            return {
                                'price': float(price),
                                'symbol': sym,
                                'available': True
                            }
                    except Exception as e:
                        logger.debug(f"Yahoo price error for {sym}: {e}")
                        continue
                
                logger.warning(f"Yahoo price not found for any symbol: {symbols_to_try}")
                return {
                    'available': False,
                    'error': f'Price not found for symbols: {", ".join(symbols_to_try)}',
                    'tried_symbols': symbols_to_try
                }
                
            except Exception as e:
                logger.exception(f"Error getting Yahoo price: {e}")
                return {
                    'available': False,
                    'error': str(e)
                }
        
        # Exécuter les deux requêtes en parallèle
        broker_result = {'error': 'Timeout'}
        yahoo_result = {'available': False, 'error': 'Timeout'}
        
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                broker_future = executor.submit(get_broker_price)
                yahoo_future = executor.submit(get_yahoo_price_data)
                
                broker_result = broker_future.result(timeout=10)
                yahoo_result = yahoo_future.result(timeout=10)
        except FutureTimeoutError:
            logger.warning("Timeout while fetching prices")
        except Exception as e:
            logger.error(f"Error in parallel price fetching: {e}")
        
        # Préparer la réponse
        response_data = {
            'success': 'error' not in broker_result,
            'broker_price': broker_result,
        }
        
        # Ajouter les données Yahoo
        if yahoo_result.get('available'):
            response_data['yahoo_data'] = {
                'price': yahoo_result.get('price'),
                'symbol': yahoo_result.get('symbol'),
                'available': True
            }
        else:
            response_data['yahoo_data'] = {
                'available': False,
                'error': yahoo_result.get('error', 'Price not available'),
                'tried_symbols': yahoo_result.get('tried_symbols', [])
            }
        
        # Ajouter le symbole Yahoo validé si disponible
        if all_asset and all_asset.symbole_yahoo:
            response_data['yahoo_data']['validated_symbol'] = (
                all_asset.symbole_yahoo 
                if all_asset.symbole_yahoo not in ['Not_searched', 'not_found', 'manual']
                else None
            )
        
        return Response(response_data)
    
    @action(detail=False, methods=['post'])
    def sync(self, request):
        """
        POST /api/orders/sync/
        Synchronise les ordres depuis un broker.
        
        Body:
        {
            "broker_account_id": 1,
            "status": "OPEN",  // optionnel, défaut: "OPEN"
            "symbol": "AAPL"   // optionnel, filtrer par symbole
        }
        """
        broker_account_id = request.data.get('broker_account_id')
        status = request.data.get('status', 'OPEN')
        symbol = request.data.get('symbol')
        
        if not broker_account_id:
            return Response(
                {'error': 'broker_account_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            broker_account = BrokerAccount.objects.get(
                id=broker_account_id,
                user=request.user
            )
        except BrokerAccount.DoesNotExist:
            return Response(
                {'error': 'Broker account not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Sync orders
        service = BrokerService(request.user)
        result = service.sync_pending_orders_from_broker(
            broker_account=broker_account,
            status=status,
            symbol=symbol
        )
        
        if not result.get('success'):
            return Response(
                {'error': result.get('message', 'Sync failed')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            'success': True,
            'message': result.get('message'),
            'created': result.get('created', 0),
            'updated': result.get('updated', 0),
            'errors': result.get('errors', [])
        })


# ============================================
# VIEWSETS STRATEGIES
# ============================================

class StrategyViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les stratégies.
    
    Actions personnalisées :
    - GET /api/strategies/1/performance/ → Performance de la stratégie
    - GET /api/strategies/1/positions/ → Positions de la stratégie
    - POST /api/strategies/1/activate/ → Activer la stratégie
    - POST /api/strategies/1/deactivate/ → Désactiver la stratégie
    """
    serializer_class = StrategySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    filterset_fields = ['risk_level', 'is_active', 'is_automated']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        return Strategy.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        """
        GET /api/strategies/1/performance/
        Performance de la stratégie sur les 30 derniers jours.
        """
        strategy = self.get_object()
        days = int(request.query_params.get('days', 30))
        since = timezone.now().date() - timedelta(days=days)
        
        performances = StrategyPerformance.objects.filter(
            strategy=strategy,
            date__gte=since
        ).order_by('date')
        
        total_trades = sum(p.total_trades for p in performances)
        total_pnl = sum(p.net_pnl for p in performances)
        winning_trades = sum(p.winning_trades for p in performances)
        
        return Response({
            'strategy': StrategySerializer(strategy).data,
            'period_days': days,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': round((winning_trades / total_trades * 100), 2) if total_trades else 0,
            'total_pnl': float(total_pnl),
            'daily_performance': [
                {
                    'date': p.date.isoformat(),
                    'trades': p.total_trades,
                    'pnl': float(p.net_pnl),
                }
                for p in performances
            ]
        })
    
    @action(detail=True, methods=['get'])
    def positions(self, request, pk=None):
        """GET /api/strategies/1/positions/ → Positions de la stratégie."""
        strategy = self.get_object()
        positions = Position.objects.filter(strategy=strategy, user=request.user)
        serializer = PositionSerializer(positions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """POST /api/strategies/1/activate/ → Active la stratégie."""
        strategy = self.get_object()
        strategy.is_active = True
        strategy.save()
        return Response({'status': 'Strategy activated', 'strategy': StrategySerializer(strategy).data})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """POST /api/strategies/1/deactivate/ → Désactive la stratégie."""
        strategy = self.get_object()
        strategy.is_active = False
        strategy.save()
        return Response({'status': 'Strategy deactivated', 'strategy': StrategySerializer(strategy).data})
    
    def _build_portfolio_data(self, strategy):
        """
        Construit les données de portfolio pour une stratégie.
        
        Returns:
            tuple: (portfolio_dict, pending_orders_list)
        """
        from apps.trading.models import Position, Order
        from decimal import Decimal
        
        # Portfolio : cash et quantité totale pour cet asset
        # Pour simplifier, on considère le cash comme illimité (ou configurable)
        # La quantité totale = positions ouvertes pour cet asset
        positions = Position.objects.filter(
            all_asset=strategy.all_asset,  # Utiliser all_asset au lieu de asset
            user=strategy.user,
            is_open=True
        )
        
        quantity_total = sum(Decimal(str(p.quantity)) for p in positions)
        
        # Cash : Récupérer depuis BrokerAccount ou fallback sur le budget
        cash_total = 0.0
        if strategy.broker_account and strategy.broker_account.balance is not None:
            cash_total = float(strategy.broker_account.balance)
        elif strategy.budget is not None:
            cash_total = float(strategy.budget)
        else:
            cash_total = 10000.0 # Fallback ultime
        
        portfolio = {
            'cash_total': float(cash_total),
            'quantity_total': float(quantity_total),
            'broker_name': strategy.broker_account.broker.name if strategy.broker_account and strategy.broker_account.broker else 'Simulation'
        }
        
        # Pending orders : ordres non exécutés pour cet asset
        pending_orders_qs = Order.objects.filter(
            all_asset=strategy.all_asset,  # Utiliser all_asset au lieu de asset
            user=strategy.user,
            status='pending'
        )
        
        pending_orders = []
        for order in pending_orders_qs:
            pending_orders.append({
                'type': order.order_type.upper(),  # 'BUY' ou 'SELL'
                'qty': float(order.quantity),
                'price': float(order.price)
            })
        
        return portfolio, pending_orders
    

    def _execute_signal(self, strategy, signal_type, quantity, price, execution):
        """
        Exécute concrètement le signal en créant les entrées en base (Order, Trade, Position).
        Appelle l'API du broker réel (Binance/Saxo) et capture la réponse.
        """
        from apps.trading.models import Position, Order, Trade
        from apps.trading.services.broker_service import BrokerService
        from decimal import Decimal
        import logging
        
        logger = logging.getLogger(__name__)
        
        if not strategy.broker_account or not strategy.broker_account.broker:
            raise Exception("Aucun compte broker configuré pour cette stratégie")
            
        broker = strategy.broker_account.broker
        qty_decimal = Decimal(str(quantity))
        price_decimal = Decimal(str(price))
        
        # ============================================
        # APPEL API BROKER RÉEL
        # ============================================
        broker_api_response = None
        broker_api_url = None
        broker_api_error = None
        
        try:
            # Déterminer l'URL de l'API en fonction du broker
            broker_name = broker.name.lower()
            if 'binance' in broker_name:
                broker_api_url = "POST https://api.binance.com/api/v3/order"
            elif 'saxo' in broker_name:
                broker_api_url = "POST https://gateway.saxobank.com/openapi/trade/v2/orders"
            else:
                broker_api_url = f"API {broker.name} (endpoint inconnu)"
            
            # Appeler le BrokerService pour passer l'ordre réel
            broker_service = BrokerService(user=strategy.user)
            
            # Récupérer le symbole de l'asset
            asset_symbol = strategy.all_asset.symbol if strategy.all_asset else 'UNKNOWN'
            
            # ============================================
            # AJUSTER LA QUANTITÉ SELON LES FILTRES DU BROKER
            # ============================================
            adjusted_quantity = qty_decimal
            
            try:
                # Obtenir l'instance du broker pour accéder aux filtres
                broker_instance = broker_service.get_broker_instance(strategy.broker_account)
                
                # Pour Binance : récupérer les filtres LOT_SIZE
                if 'binance' in broker_name:
                    exchange_info = broker_instance._get_exchange_info() if hasattr(broker_instance, '_get_exchange_info') else None
                    
                    if exchange_info:
                        symbols = exchange_info.get('symbols', [])
                        symbol_info = next((s for s in symbols if s.get('symbol') == asset_symbol.upper()), None)
                        
                        if symbol_info:
                            filters = symbol_info.get('filters', [])
                            lot_size_filter = next((f for f in filters if f.get('filterType') == 'LOT_SIZE'), None)
                            
                            if lot_size_filter:
                                from decimal import Decimal, ROUND_DOWN
                                
                                min_qty = Decimal(str(lot_size_filter.get('minQty', '0')))
                                max_qty = Decimal(str(lot_size_filter.get('maxQty', '999999999')))
                                step_size = Decimal(str(lot_size_filter.get('stepSize', '1')))
                                
                                logger.info(
                                    f"📏 Filtres Binance {asset_symbol}: "
                                    f"minQty={min_qty}, maxQty={max_qty}, stepSize={step_size}"
                                )
                                
                                # Arrondir au stepSize
                                if step_size > 0:
                                    # Diviser par stepSize, arrondir vers le bas, puis multiplier
                                    adjusted_quantity = (qty_decimal / step_size).quantize(Decimal('1'), rounding=ROUND_DOWN) * step_size
                                
                                # Vérifier min/max
                                if adjusted_quantity < min_qty:
                                    logger.warning(f"⚠️ Quantité {adjusted_quantity} < minQty {min_qty}, ajustement à minQty")
                                    adjusted_quantity = min_qty
                                elif adjusted_quantity > max_qty:
                                    logger.warning(f"⚠️ Quantité {adjusted_quantity} > maxQty {max_qty}, ajustement à maxQty")
                                    adjusted_quantity = max_qty
                                
                                logger.info(
                                    f"✅ Quantité ajustée : {qty_decimal} -> {adjusted_quantity} "
                                    f"(stepSize={step_size})"
                                )
                            else:
                                logger.warning(f"⚠️ Pas de filtre LOT_SIZE trouvé pour {asset_symbol}")
                        else:
                            logger.warning(f"⚠️ Symbole {asset_symbol} non trouvé dans exchangeInfo")
                    else:
                        logger.warning("⚠️ Impossible de récupérer exchangeInfo de Binance")
                
                # Pour Saxo : logique similaire si nécessaire (à implémenter)
                elif 'saxo' in broker_name:
                    # Saxo a des règles différentes, à implémenter si nécessaire
                    logger.info(f"📏 Saxo : pas d'ajustement automatique implémenté pour le moment")
                    
            except Exception as adjust_error:
                logger.warning(f"⚠️ Erreur lors de l'ajustement de quantité : {adjust_error}, utilisation de la quantité originale")
                adjusted_quantity = qty_decimal
            
            # ============================================
            # APPELER L'API BROKER AVEC LA QUANTITÉ AJUSTÉE
            # ============================================
            
            logger.info(
                f"🚀 Appel API broker {broker.name} pour {signal_type} "
                f"{adjusted_quantity} {asset_symbol} @ {price_decimal}"
            )
            
            # Passer l'ordre via le broker
            order_result = broker_service.place_order(
                broker_account=strategy.broker_account,
                symbol=asset_symbol,
                side=signal_type,  # 'BUY' ou 'SELL'
                quantity=adjusted_quantity,  # Utiliser la quantité ajustée
                order_type='MARKET',
                price=None,  # MARKET orders n'ont pas de prix limite
            )
            
            if order_result.success:
                logger.info(f"✅ Ordre broker placé avec succès : {order_result.order_id}")
                broker_api_response = {
                    'success': True,
                    'order_id': order_result.order_id,
                    'message': order_result.message,
                    'raw_data': order_result.raw_data if hasattr(order_result, 'raw_data') else None,
                }
            else:
                logger.error(f"❌ Échec de l'ordre broker : {order_result.error}")
                broker_api_error = order_result.error
                broker_api_response = {
                    'success': False,
                    'error': order_result.error,
                }
        
        except Exception as e:
            logger.exception(f"❌ Erreur lors de l'appel API broker : {e}")
            broker_api_error = str(e)
            broker_api_response = {
                'success': False,
                'error': str(e),
                'exception_type': type(e).__name__,
            }
        
        # ============================================
        # CRÉER LES ENTRÉES EN BASE DE DONNÉES
        # ============================================
        
        # 1. Créer l'Ordre en base locale
        broker_order_id = f"AUTO-{execution.id}"
        if broker_api_response and broker_api_response.get('success'):
            # Si l'API broker a retourné un ID, l'utiliser
            if broker_api_response.get('order_id'):
                broker_order_id = broker_api_response['order_id']
        
        Order.objects.create(
             user=strategy.user,
             all_asset=strategy.all_asset,
             broker=broker,
             strategy=strategy,
             order_type='MARKET',
             side='BUY' if signal_type == 'BUY' else 'SELL',
             status='FILLED' if broker_api_response and broker_api_response.get('success') else 'FAILED',
             quantity=adjusted_quantity,  # Utiliser la quantité ajustée
             filled_quantity=adjusted_quantity if broker_api_response and broker_api_response.get('success') else Decimal('0'),
             price=price_decimal,
             broker_order_id=broker_order_id
        )
        
        # 2. Créer le Trade (seulement si succès)
        trade = None
        if broker_api_response and broker_api_response.get('success'):
            trade = Trade.objects.create(
                 user=strategy.user,
                 all_asset=strategy.all_asset,
                 broker=broker,
                 position=None, # Sera lié après
                 strategy=strategy,
                 trade_type='BUY' if signal_type == 'BUY' else 'SELL',
                 quantity=adjusted_quantity,  # Utiliser la quantité ajustée
                 price=price_decimal,
                 fees=Decimal('0'),
                 executed_at=timezone.now(),
                 broker_trade_id=f"TRD-{execution.id}"
            )
        
        # 3. Mettre à jour la Position (seulement si succès)
        if broker_api_response and broker_api_response.get('success'):
            position = Position.objects.filter(
                user=strategy.user, 
                all_asset=strategy.all_asset,
                is_open=True
            ).first()
            
            if signal_type == 'BUY':
                 if position:
                     # Moyenne pondérée du prix d'entrée
                     current_val = position.entry_price * position.quantity
                     trade_val = price_decimal * adjusted_quantity  # Utiliser la quantité ajustée
                     new_qty = position.quantity + adjusted_quantity  # Utiliser la quantité ajustée
                     position.entry_price = (current_val + trade_val) / new_qty
                     position.quantity = new_qty
                     position.save()
                 else:
                     # Nouvelle position
                     position = Position.objects.create(
                         user=strategy.user,
                         all_asset=strategy.all_asset,
                         broker=broker,
                         strategy=strategy,
                         side='LONG',
                         quantity=adjusted_quantity,  # Utiliser la quantité ajustée
                         entry_price=price_decimal,
                         current_price=price_decimal,
                         is_open=True
                     )
            elif signal_type == 'SELL':
                 if position:
                     position.quantity -= adjusted_quantity  # Utiliser la quantité ajustée
                     if position.quantity <= Decimal('0.00000001'):
                         position.is_open = False
                         position.closed_at = timezone.now()
                         position.quantity = 0
                     position.save()
                     
            # Lier le trade à la position
            if trade and position:
                trade.position = position
                trade.save()
        
        # ============================================
        # RETOURNER LA RÉPONSE POUR AFFICHAGE
        # ============================================
        return {
            'api_url': broker_api_url,
            'api_response': broker_api_response,
            'api_error': broker_api_error,
            'quantity_original': float(qty_decimal),
            'quantity_adjusted': float(adjusted_quantity),
            'quantity_was_adjusted': (qty_decimal != adjusted_quantity),
        }

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """POST /api/strategies/1/execute/ → Exécute la stratégie manuellement."""
        from apps.trading.models import StrategyExecution
        from apps.trading.algorithms import get_algorithm_instance
        import json
        from datetime import datetime
        
        strategy = self.get_object()
        
        # Créer un log d'exécution
        execution = StrategyExecution.objects.create(
            strategy=strategy,
            status='running'
        )
        
        try:
            # Récupérer l'algorithme
            algo = strategy.get_algorithm_instance()
            if not algo:
                raise Exception(f"Impossible de créer l'algorithme {strategy.algorithm_type}")
            
            # Construire les données de portfolio et ordres en attente
            portfolio, pending_orders = self._build_portfolio_data(strategy)
            
            # Récupérer les données de prix de l'asset (Depuis JSONB)
            # Support both new JSONB format and fallback if needed (though we prefer JSONB)
            price_history_json = getattr(strategy.all_asset, 'price_history_json', {}) or {}
            
            if not price_history_json:
                raise Exception(f"Aucune donnée de prix disponible pour l'asset {strategy.all_asset} (JSONB empty)")
                
            # Convert JSONB dict to list sorted by date
            # JSON format: {'YYYY-MM-DD': {'open': ..., 'close': ...}}
            sorted_dates = sorted(price_history_json.keys())
            
            # Keep last 100 points
            sorted_dates = sorted_dates[-100:]
            
            price_data = []
            for d in sorted_dates:
                data = price_history_json[d]
                # conversion format
                try:
                    dt_obj = datetime.strptime(d, '%Y-%m-%d').date()
                except ValueError:
                    dt_obj = datetime.fromisoformat(d.replace('Z', '')).date()

                price_data.append({
                    'date': dt_obj,
                    'open': data.get('open'),
                    'high': data.get('high'),
                    'low': data.get('low'),
                    'close': data.get('close'),
                    'volume': data.get('volume')
                })
            
            if not price_data:
                raise Exception(f"Aucune donnée de prix disponible pour l'asset {strategy.all_asset}")
            
            # Calculer les signaux avec portfolio et ordres en attente
            signals = algo.calculate_signals(price_data, portfolio, pending_orders)
            
            # Déterminer le signal principal
            signal_type = signals.get('signal', 'NONE')
            signal_price = float(price_data[-1]['close']) if price_data else None
            # Utiliser la quantité calculée par l'algorithme au lieu de max_quantity
            signal_quantity = signals.get('quantity', 0)
            output_data = {
                'signals': signals,
                'price_data_count': len(price_data),
                'portfolio': portfolio,
                'pending_orders_count': len(pending_orders)
            }
            
            # Mettre à jour l'exécution
            execution.status = 'completed'
            execution.signal = signal_type
            execution.signal_price = signal_price
            execution.signal_quantity = signal_quantity
            execution.output = json.dumps(output_data)
            execution.completed_at = timezone.now()
            execution.save()
            
            # AUTOMATED TRADING: Execute the signal if automated and valid
            if strategy.is_automated and signal_type in ['BUY', 'SELL'] and signal_quantity > 0:
                try:
                    # Appeler _execute_signal et capturer la réponse de l'API broker
                    broker_response = self._execute_signal(strategy, signal_type, signal_quantity, signal_price, execution)
                    
                    # Ajouter la réponse du broker à l'output
                    output_data['execution_executed'] = True
                    output_data['broker_api_url'] = broker_response.get('api_url')
                    output_data['broker_api_response'] = broker_response.get('api_response')
                    output_data['broker_api_error'] = broker_response.get('api_error')
                    
                    execution.output = json.dumps(output_data)
                    execution.save()
                except Exception as e:
                    execution.error = f"Execution error: {str(e)}"
                    execution.status = 'failed'
                    execution.save()
            
            return Response({
                'status': 'success',
                'execution_id': execution.id,
                'signal': signal_type,
                'signal_price': signal_price,
                'signal_quantity': signal_quantity,
                'output': output_data
            })


            
        except Exception as e:
            execution.status = 'failed'
            execution.error = str(e)
            execution.completed_at = timezone.now()
            execution.save()
            
            return Response({
                'status': 'error',
                'execution_id': execution.id,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def execute_all(self, request):
        """POST /api/strategies/execute-all/ → Exécute toutes les stratégies actives."""
        from apps.trading.models import StrategyExecution
        import json
        from datetime import datetime
        
        strategies = Strategy.objects.filter(user=request.user, is_active=True)
        results = []
        
        for strategy in strategies:
            execution = StrategyExecution.objects.create(
                strategy=strategy,
                status='running'
            )
            
            try:
                algo = strategy.get_algorithm_instance()
                if not algo:
                    raise Exception(f"Impossible de créer l'algorithme {strategy.algorithm_type}")
                
                # Construire les données de portfolio et ordres en attente
                portfolio, pending_orders = self._build_portfolio_data(strategy)
                
                 # Récupérer les données de prix de l'asset (Depuis JSONB)
                price_history_json = getattr(strategy.all_asset, 'price_history_json', {}) or {}
                
                if not price_history_json:
                    raise Exception(f"Aucune donnée de prix disponible pour l'asset {strategy.all_asset} (JSONB empty)")
                    
                sorted_dates = sorted(price_history_json.keys())
                sorted_dates = sorted_dates[-100:]
                
                price_data = []
                for d in sorted_dates:
                    data = price_history_json[d]
                    try:
                        dt_obj = datetime.strptime(d, '%Y-%m-%d').date()
                    except ValueError:
                        dt_obj = datetime.fromisoformat(d.replace('Z', '')).date()

                    price_data.append({
                        'date': dt_obj,
                        'open': data.get('open'),
                        'high': data.get('high'),
                        'low': data.get('low'),
                        'close': data.get('close'),
                        'volume': data.get('volume')
                    })

                if not price_data:
                    raise Exception(f"Aucune donnée de prix disponible pour l'asset {strategy.all_asset}")
                
                # Calculer les signaux avec portfolio et ordres en attente
                signals = algo.calculate_signals(price_data, portfolio, pending_orders)
                
                signal_type = signals.get('signal', 'NONE')
                signal_price = float(price_data[-1]['close']) if price_data else None
                # Utiliser la quantité calculée par l'algorithme au lieu de max_quantity
                signal_quantity = signals.get('quantity', 0)
                output_data = {
                    'signals': signals,
                    'price_data_count': len(price_data),
                    'portfolio': portfolio,
                    'pending_orders_count': len(pending_orders)
                }
                
                execution.status = 'completed'
                execution.signal = signal_type
                execution.signal_price = signal_price
                execution.signal_quantity = signal_quantity
                execution.output = json.dumps(output_data)
                execution.completed_at = timezone.now()
                execution.save()
                
                # AUTOMATED TRADING: Execute the signal if automated and valid
                if strategy.is_automated and signal_type in ['BUY', 'SELL'] and signal_quantity > 0:
                    try:
                        # Appeler _execute_signal et capturer la réponse de l'API broker
                        broker_response = self._execute_signal(strategy, signal_type, signal_quantity, signal_price, execution)
                        
                        # Ajouter la réponse du broker à l'output
                        output_data['execution_executed'] = True
                        output_data['broker_api_url'] = broker_response.get('api_url')
                        output_data['broker_api_response'] = broker_response.get('api_response')
                        output_data['broker_api_error'] = broker_response.get('api_error')
                        
                        execution.output = json.dumps(output_data)
                        execution.save()
                    except Exception as e:
                        execution.error = f"Execution error: {str(e)}"
                        execution.status = 'failed'
                        execution.save()
                
                results.append({
                    'strategy_id': strategy.id,
                    'strategy_name': strategy.name,
                    'status': 'success',
                    'execution_id': execution.id,
                    'signal': signal_type
                })
                
            except Exception as e:
                execution.status = 'failed'
                execution.error = str(e)
                execution.completed_at = timezone.now()
                execution.save()
                
                results.append({
                    'strategy_id': strategy.id,
                    'strategy_name': strategy.name,
                    'status': 'error',
                    'execution_id': execution.id,
                    'error': str(e)
                })
        
        return Response({
            'total_strategies': len(strategies),
            'results': results
        })



class StrategyExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour les logs d'exécution de stratégies (lecture seule).
    
    Endpoints:
    - GET /api/strategy-executions/ → Liste tous les logs
    - GET /api/strategy-executions/1/ → Détails d'un log
    - GET /api/strategy-executions/recent/ → Logs récents (20 derniers)
    """
    from .serializers import StrategyExecutionSerializer
    serializer_class = StrategyExecutionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    
    filterset_fields = ['strategy', 'status', 'signal']
    ordering_fields = ['started_at', 'completed_at']
    ordering = ['-started_at']
    
    def get_queryset(self):
        """Filtre les exécutions par utilisateur via la stratégie."""
        from apps.trading.models import StrategyExecution
        return StrategyExecution.objects.filter(
            strategy__user=self.request.user
        ).select_related('strategy')
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """GET /api/strategy-executions/recent/ → 20 derniers logs."""
        executions = self.get_queryset()[:20]
        serializer = self.get_serializer(executions, many=True)
        return Response(serializer.data)


# ============================================
# VIEWSETS BROKERS
# ============================================

class BrokerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour les brokers (lecture seule).
    Les brokers sont gérés par l'admin.
    """
    queryset = Broker.objects.filter(is_active=True)
    serializer_class = BrokerSerializer
    permission_classes = [permissions.IsAuthenticated]


class BrokerAccountViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les comptes broker.
    
    Actions personnalisées :
    - GET /api/broker-accounts/1/sync_status/ → Statut de synchronisation
    - POST /api/broker-accounts/1/refresh_balance/ → Rafraîchir la balance
    - POST /api/broker-accounts/1/test-connection/ → Tester la connexion
    - POST /api/broker-accounts/1/sync/ → Synchroniser les données
    """
    serializer_class = BrokerAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['broker', 'broker_type', 'is_active', 'environment']
    ordering = ['broker_type', 'name']
    pagination_class = StandardPagination
    
    def get_queryset(self):
        return BrokerAccount.objects.filter(user=self.request.user).select_related('broker')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def sync_status(self, request, pk=None):
        """
        GET /api/broker-accounts/1/sync_status/
        Statut des dernières synchronisations.
        """
        account = self.get_object()
        logs = BrokerSyncLog.objects.filter(broker_account=account).order_by('-started_at')[:10]
        
        return Response({
            'account': BrokerAccountSerializer(account).data,
            'recent_syncs': [
                {
                    'sync_type': log.sync_type,
                    'status': log.status,
                    'records_synced': log.records_synced,
                    'started_at': log.started_at.isoformat(),
                    'error': log.error_message if log.status == 'FAILED' else None,
                }
                for log in logs
            ]
        })
    
    @action(detail=True, methods=['post'], url_path='refresh-balance')
    def refresh_balance(self, request, pk=None):
        """
        POST /api/broker-accounts/1/refresh-balance/
        Rafraîchit la balance du compte et retourne le solde EUR.
        """
        from django.utils import timezone
        from decimal import Decimal
        from ..services.broker_service import BrokerService
        import logging
        
        logger = logging.getLogger('trading.api.brokers')
        
        account = self.get_object()
        service = BrokerService(request.user)
        
        try:
            # Récupérer toutes les balances
            balances = service.get_account_balance(account)
            
            # Pour Saxo, extraire le solde de la devise principale
            if account.broker_type == 'SAXO':
                currency = account.currency or 'EUR'
                eur_balance = balances.get(currency, balances.get('EUR', Decimal('0')))
                
                # Si pas de EUR, prendre la première balance disponible
                if eur_balance == 0 and balances:
                    currency = list(balances.keys())[0]
                    eur_balance = balances[currency]
            else:
                # Pour Binance, convertir toutes les balances crypto en EUR
                from ..utils.binance_balance_converter import get_binance_eur_balance
                broker = service.get_broker_instance(account)
                # S'assurer que le broker est authentifié pour récupérer les prix
                if broker and hasattr(broker, 'is_authenticated') and not broker.is_authenticated():
                    broker.authenticate()
                eur_balance = get_binance_eur_balance(balances, broker_instance=broker)
                currency = 'EUR'
            
            # Mettre à jour le modèle
            account.balance = eur_balance
            account.currency = currency
            account.balance_updated_at = timezone.now()
            account.save(update_fields=['balance', 'currency', 'balance_updated_at'])
            
            # Formater les balances (exclure les clés _free, _locked, _margin_available, _total)
            all_balances = {
                k: float(v) 
                for k, v in balances.items() 
                if not k.endswith('_free') and not k.endswith('_locked')
                and not k.endswith('_margin_available') and not k.endswith('_total')
            }
            
            return Response({
                'success': True,
                'balance_eur': float(eur_balance),
                'currency': currency,
                'all_balances': all_balances,
                'account': BrokerAccountSerializer(account).data
            })
        except Exception as e:
            logger.error(f"Error refreshing balance for account {account.id}: {e}")
            return Response({
                'success': False,
                'error': str(e),
                'balance_eur': 0.0
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='credentials')
    def credentials(self, request, pk=None):
        """
        GET /api/broker-accounts/1/credentials/
        Affiche les credentials (masqués) pour débogage.
        """
        account = self.get_object()
        credentials_dict = account.get_credentials_dict()
        
        # Masquer les secrets
        masked_credentials = {}
        for key, value in credentials_dict.items():
            if value:
                if 'secret' in key.lower() or 'token' in key.lower() or 'key' in key.lower():
                    # Masquer les secrets (afficher les 4 premiers et 4 derniers caractères)
                    str_value = str(value)
                    if len(str_value) > 8:
                        masked_credentials[key] = f"{str_value[:4]}...{str_value[-4:]}"
                    else:
                        masked_credentials[key] = "***"
                else:
                    masked_credentials[key] = value
            else:
                masked_credentials[key] = None
        
        # Afficher aussi les valeurs brutes (masquées) pour vérifier
        raw_credentials = {}
        if account.broker_type == 'BINANCE':
            raw_credentials = {
                'binance_api_key': account.binance_api_key[:8] + '...' if account.binance_api_key else None,
                'binance_api_secret': account.binance_api_secret[:8] + '...' if account.binance_api_secret else None,
                'binance_testnet': account.binance_testnet if hasattr(account, 'binance_testnet') else None,
                'api_key': account.api_key[:8] + '...' if account.api_key else None,
                'api_secret': account.api_secret[:8] + '...' if account.api_secret else None,
            }
        elif account.broker_type == 'SAXO':
            raw_credentials = {
                'saxo_client_id': account.saxo_client_id[:8] + '...' if account.saxo_client_id else None,
                'saxo_client_secret': account.saxo_client_secret[:8] + '...' if account.saxo_client_secret else None,
            }
        
        return Response({
            'broker_type': account.broker_type,
            'credentials_dict': masked_credentials,
            'raw_fields': raw_credentials,
            'has_api_key': bool(credentials_dict.get('api_key')),
            'has_api_secret': bool(credentials_dict.get('api_secret')),
            'testnet': credentials_dict.get('testnet', False),
            'environment': credentials_dict.get('environment', 'unknown'),
        })
    
    @action(detail=True, methods=['get'], url_path='balance-eur')
    def balance_eur(self, request, pk=None):
        """
        GET /api/broker-accounts/1/balance-eur/
        Récupère le solde EUR actuel du compte sans mettre à jour la base de données.
        """
        from decimal import Decimal
        from ..services.broker_service import BrokerService
        from ..brokers.base import BrokerAuthenticationError
        from django.utils import timezone
        import logging
        
        logger = logging.getLogger('trading.api.brokers')
        
        account = self.get_object()
        service = BrokerService(request.user)
        
        try:
            # Récupérer toutes les balances
            balances = service.get_account_balance(account)
            
            # Pour Saxo, extraire le solde de la devise principale
            if account.broker_type == 'SAXO':
                currency = account.currency or 'EUR'
                eur_balance = balances.get(currency, balances.get('EUR', Decimal('0')))
                
                # Si pas de EUR, prendre la première balance disponible
                if eur_balance == 0 and balances:
                    currency = list(balances.keys())[0]
                    eur_balance = balances[currency]
            else:
                # Pour Binance, convertir toutes les balances crypto en EUR
                from ..utils.binance_balance_converter import get_binance_eur_balance
                
                # Logger les balances brutes reçues
                logger.info(
                    f"Binance account {account.id}: Raw balances received: "
                    f"{dict(balances)} (count: {len(balances)})"
                )
                
                broker = service.get_broker_instance(account)
                
                # S'assurer que le broker est authentifié pour récupérer les prix
                if broker:
                    if hasattr(broker, 'is_authenticated'):
                        is_auth = broker.is_authenticated()
                        logger.debug(f"Binance account {account.id}: Broker authenticated: {is_auth}")
                        if not is_auth:
                            logger.info(f"Binance account {account.id}: Authenticating broker...")
                            auth_result = broker.authenticate()
                            logger.info(f"Binance account {account.id}: Authentication result: {auth_result}")
                    else:
                        logger.warning(f"Binance account {account.id}: Broker has no is_authenticated method")
                else:
                    logger.warning(f"Binance account {account.id}: No broker instance available")
                
                eur_balance = get_binance_eur_balance(balances, broker_instance=broker)
                currency = 'EUR'
                
                # Logger pour déboguer
                logger.info(
                    f"Binance account {account.id}: Balance conversion result: "
                    f"eur_balance={eur_balance} (type: {type(eur_balance)})"
                )
                
                # Vérifier si le solde est 0 alors qu'on a des balances
                if eur_balance == 0 and balances:
                    clean_count = len([
                        k for k in balances.keys()
                        if not k.endswith('_free') and not k.endswith('_locked')
                        and not k.endswith('_margin_available') and not k.endswith('_total')
                        and balances[k] > 0
                    ])
                    if clean_count > 0:
                        logger.warning(
                            f"Binance account {account.id}: WARNING - eur_balance is 0 but we have {clean_count} "
                            f"non-zero balances! This suggests a conversion problem."
                        )
            
            # Formater les balances (exclure les clés _free, _locked, _margin_available, _total)
            all_balances = {
                k: float(v) 
                for k, v in balances.items() 
                if not k.endswith('_free') and not k.endswith('_locked') 
                and not k.endswith('_margin_available') and not k.endswith('_total')
            }
            
            logger.debug(
                f"Returning balance for account {account.id}: "
                f"balance_eur={eur_balance}, currency={currency}, all_balances={list(all_balances.keys())}"
            )
            
            return Response({
                'success': True,
                'balance_eur': float(eur_balance),
                'currency': currency,
                'all_balances': all_balances,
                'timestamp': timezone.now().isoformat()
            })
        except BrokerAuthenticationError as e:
            # Erreur d'authentification spécifique
            error_msg = str(e)
            logger.warning(f"Authentication error for account {account.id}: {error_msg}")
            
            # Message plus explicite selon le type d'erreur
            if 'expired' in error_msg.lower() or 'invalid' in error_msg.lower():
                message = 'Token expiré ou invalide. Veuillez rafraîchir le token ou vous ré-authentifier via OAuth2.'
            else:
                message = 'Erreur d\'authentification. Vérifiez vos credentials ou ré-authentifiez-vous.'
            
            return Response({
                'success': False,
                'error': error_msg,
                'error_type': 'AUTHENTICATION_ERROR',
                'balance_eur': 0.0,
                'message': message
            }, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            logger.error(f"Error getting EUR balance for account {account.id}: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'error_type': 'UNKNOWN_ERROR',
                'balance_eur': 0.0
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='saxo-auth-url')
    def saxo_auth_url(self, request, pk=None):
        """
        GET /api/broker-accounts/{id}/saxo-auth-url/
        Obtient l'URL d'authentification OAuth2 pour Saxo Bank.
        """
        from ..services.broker_service import BrokerService
        import secrets
        import logging
        import os
        
        logger = logging.getLogger('trading.api.brokers')
        
        account = self.get_object()
        
        if account.broker_type != 'SAXO':
            return Response({
                'success': False,
                'error': 'Cette méthode est uniquement pour Saxo Bank'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Si aucune redirect URI n'est définie en base, utiliser une valeur de prod.
            # Cela évite de rediriger vers le domaine "fallback" historique (ex: le-baff.com)
            # quand le frontend est désormais hébergé sur Vercel.
            if not account.saxo_redirect_uri:
                frontend_url = (
                    os.environ.get("SAXO_REDIRECT_URI")
                    or os.environ.get("FRONTEND_URL")
                    or "https://trading-app-version4.vercel.app/"
                )
                account.saxo_redirect_uri = frontend_url.rstrip("/") + "/"
                account.save(update_fields=["saxo_redirect_uri"])

            service = BrokerService(request.user)
            broker = service.get_broker_instance(account, use_cache=False)
            
            # Générer un state pour CSRF protection
            state = secrets.token_urlsafe(32)
            request.session[f'saxo_oauth_state_{account.id}'] = state
            
            auth_url = broker.get_authorization_url(state=state)
            
            return Response({
                'success': True,
                'auth_url': auth_url,
                'state': state,
            })
        except Exception as e:
            logger.error(f"Error getting Saxo auth URL for account {account.id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], url_path='saxo-exchange-code')
    def saxo_exchange_code(self, request, pk=None):
        """
        POST /api/broker-accounts/{id}/saxo-exchange-code/
        Échange le code d'autorisation OAuth2 contre des tokens.
        
        Body: { "code": "AUTHORIZATION_CODE", "state": "STATE_VALUE" }
        """
        from ..services.broker_service import BrokerService
        from django.utils import timezone
        import logging
        
        logger = logging.getLogger('trading.api.brokers')
        
        account = self.get_object()
        
        if account.broker_type != 'SAXO':
            return Response({
                'success': False,
                'error': 'Cette méthode est uniquement pour Saxo Bank'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        code = request.data.get('code')
        state = request.data.get('state')
        
        if not code:
            return Response({
                'success': False,
                'error': 'Le code d\'autorisation est requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier le state (CSRF protection)
        stored_state = request.session.get(f'saxo_oauth_state_{account.id}')
        if state and stored_state and stored_state != state:
            return Response({
                'success': False,
                'error': 'State invalide - possible attaque CSRF'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            service = BrokerService(request.user)
            broker = service.get_broker_instance(account, use_cache=False)
            
            # Échanger le code contre des tokens
            token_data = broker.exchange_code_for_token(code)
            
            # Sauvegarder les tokens dans la base de données
            account.saxo_access_token = token_data['access_token']
            account.saxo_refresh_token = token_data.get('refresh_token')
            if token_data.get('token_expires_at'):
                from ..utils.token_utils import parse_iso_datetime
                account.saxo_token_expires_at = parse_iso_datetime(
                    token_data['token_expires_at']
                )
            account.save(update_fields=['saxo_access_token', 'saxo_refresh_token', 'saxo_token_expires_at'])
            
            # Nettoyer le state de la session
            if f'saxo_oauth_state_{account.id}' in request.session:
                del request.session[f'saxo_oauth_state_{account.id}']
            
            return Response({
                'success': True,
                'message': 'Tokens obtenus avec succès',
                'token_expires_at': token_data.get('token_expires_at'),
                'account': BrokerAccountSerializer(account).data
            })
        except Exception as e:
            logger.error(f"Error exchanging Saxo code for account {account.id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], url_path='saxo-refresh-token')
    def saxo_refresh_token(self, request, pk=None):
        """
        POST /api/broker-accounts/{id}/saxo-refresh-token/
        Rafraîchit le token d'accès Saxo.
        """
        from ..services.broker_service import BrokerService
        from django.utils import timezone
        import logging
        
        logger = logging.getLogger('trading.api.brokers')
        
        account = self.get_object()
        
        if account.broker_type != 'SAXO':
            return Response({
                'success': False,
                'error': 'Cette méthode est uniquement pour Saxo Bank'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            service = BrokerService(request.user)
            broker = service.get_broker_instance(account, use_cache=False)
            
            # Rafraîchir le token
            success = broker._refresh_token()
            
            if success:
                # Sauvegarder les nouveaux tokens
                from ..utils.token_utils import parse_iso_datetime
                
                account.saxo_access_token = broker.access_token
                if broker.refresh_token:
                    account.saxo_refresh_token = broker.refresh_token
                if broker.token_expires_at:
                    account.saxo_token_expires_at = parse_iso_datetime(
                        broker.token_expires_at
                    )
                account.save(update_fields=['saxo_access_token', 'saxo_refresh_token', 'saxo_token_expires_at'])
                
                return Response({
                    'success': True,
                    'message': 'Token rafraîchi avec succès',
                    'token_expires_at': broker.token_expires_at,
                    'account': BrokerAccountSerializer(account).data
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Échec du rafraîchissement du token'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error refreshing Saxo token for account {account.id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], url_path='saxo-delete-tokens')
    def saxo_delete_tokens(self, request, pk=None):
        """
        POST /api/broker-accounts/{id}/saxo-delete-tokens/
        Supprime les tokens OAuth2 Saxo.
        """
        account = self.get_object()
        
        if account.broker_type != 'SAXO':
            return Response({
                'success': False,
                'error': 'Cette méthode est uniquement pour Saxo Bank'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        account.saxo_access_token = None
        account.saxo_refresh_token = None
        account.saxo_token_expires_at = None
        account.save(update_fields=['saxo_access_token', 'saxo_refresh_token', 'saxo_token_expires_at'])
        
        return Response({
            'success': True,
            'message': 'Tokens supprimés avec succès',
            'account': BrokerAccountSerializer(account).data
        })
    
    @action(detail=True, methods=['get'], url_path='saxo-assets')
    def saxo_assets(self, request, pk=None):
        """
        GET /api/broker-accounts/{id}/saxo-assets/
        Récupère les assets disponibles depuis Saxo.
        
        Query params:
            - asset_type: Type d'asset (Stock, Etf, etc.) - default: Stock
            - keywords: Mots-clés de recherche
            - limit: Nombre maximum de résultats - default: 100
        """
        from ..services.broker_service import BrokerService
        
        account = self.get_object()
        
        if account.broker_type != 'SAXO':
            return Response({
                'success': False,
                'error': 'Cette méthode est uniquement pour Saxo Bank'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            service = BrokerService(request.user)
            asset_type = request.query_params.get('asset_type', 'Stock')
            keywords = request.query_params.get('keywords', '')
            limit = int(request.query_params.get('limit', 100))
            
            broker_assets = service.get_assets(
                broker_account=account,
                asset_type=asset_type,
                keywords=keywords,
                limit=limit
            )
            
            # Convertir en format sérialisable
            assets_data = []
            for asset in broker_assets:
                assets_data.append({
                    'symbol': asset.symbol,
                    'name': asset.name,
                    'asset_type': asset.asset_type,
                    'exchange': asset.exchange,
                    'currency': asset.currency,
                    'is_tradable': asset.is_tradable,
                    'broker_id': asset.broker_id,
                })
            
            return Response({
                'success': True,
                'count': len(assets_data),
                'assets': assets_data,
            })
        except Exception as e:
            logger.error(f"Error fetching Saxo assets for account {account.id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='saxo-positions')
    def saxo_positions(self, request, pk=None):
        """
        GET /api/broker-accounts/{id}/saxo-positions/
        Récupère les positions depuis Saxo.
        """
        from ..services.broker_service import BrokerService
        
        account = self.get_object()
        
        if account.broker_type != 'SAXO':
            return Response({
                'success': False,
                'error': 'Cette méthode est uniquement pour Saxo Bank'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            service = BrokerService(request.user)
            positions = service.get_positions(account)
            
            # Convertir en format sérialisable
            positions_data = []
            for pos in positions:
                positions_data.append({
                    'symbol': pos.symbol,
                    'quantity': float(pos.quantity),
                    'entry_price': float(pos.entry_price),
                    'current_price': float(pos.current_price) if pos.current_price else None,
                    'unrealized_pnl': float(pos.unrealized_pnl) if pos.unrealized_pnl else None,
                    'currency': pos.currency,
                    'side': pos.side,
                    'broker_id': pos.broker_id,
                })
            
            return Response({
                'success': True,
                'count': len(positions_data),
                'positions': positions_data,
            })
        except Exception as e:
            logger.error(f"Error fetching Saxo positions for account {account.id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='saxo-transactions')
    def saxo_transactions(self, request, pk=None):
        """
        GET /api/broker-accounts/{id}/saxo-transactions/
        Récupère les transactions depuis Saxo (hist/v1/transactions).
        
        Query params:
            - from_date: Date de début (format ISO, optionnel)
            - to_date: Date de fin (format ISO, optionnel)
            - limit: Nombre maximum de transactions - default: 1000
        """
        from ..services.broker_service import BrokerService
        
        account = self.get_object()
        
        if account.broker_type != 'SAXO':
            return Response({
                'success': False,
                'error': 'Cette méthode est uniquement pour Saxo Bank'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            service = BrokerService(request.user)
            broker = service.get_broker_instance(account, use_cache=False)
            
            # Récupérer les paramètres
            from_date = request.query_params.get('from_date')
            to_date = request.query_params.get('to_date')
            limit = int(request.query_params.get('limit', 1000))
            
            # Récupérer les transactions
            transactions = broker.get_transactions(
                from_date=from_date,
                to_date=to_date,
                limit=limit
            )
            
            return Response({
                'success': True,
                'count': len(transactions),
                'transactions': transactions,
            })
        except Exception as e:
            logger.error(f"Error fetching Saxo transactions for account {account.id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='binance-assets')
    def binance_assets(self, request, pk=None):
        """
        GET /api/broker-accounts/{id}/binance-assets/
        Récupère les assets disponibles depuis Binance.
        
        Query params:
            - asset_type: Type d'asset (Crypto, Spot) - default: Crypto
            - keywords: Mots-clés de recherche (ex: BTC, ETH)
            - limit: Nombre maximum de résultats - default: 100
        """
        from ..services.broker_service import BrokerService
        
        account = self.get_object()
        
        if account.broker_type != 'BINANCE':
            return Response({
                'success': False,
                'error': 'Cette méthode est uniquement pour Binance'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            service = BrokerService(request.user)
            asset_type = request.query_params.get('asset_type', 'Crypto')
            keywords = request.query_params.get('keywords', '')
            limit = int(request.query_params.get('limit', 100))
            
            broker_assets = service.get_assets(
                broker_account=account,
                asset_type=asset_type,
                keywords=keywords,
                limit=limit
            )
            
            # Convertir en format sérialisable
            assets_data = []
            for asset in broker_assets:
                assets_data.append({
                    'symbol': asset.symbol,
                    'name': asset.name,
                    'asset_type': asset.asset_type,
                    'exchange': asset.exchange,
                    'currency': asset.currency,
                    'is_tradable': asset.is_tradable,
                    'broker_id': asset.broker_id,
                })
            
            return Response({
                'success': True,
                'count': len(assets_data),
                'assets': assets_data,
            })
        except Exception as e:
            logger.error(f"Error fetching Binance assets for account {account.id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='binance-positions')
    def binance_positions(self, request, pk=None):
        """
        GET /api/broker-accounts/{id}/binance-positions/
        Récupère les positions (balances) depuis Binance.
        """
        from ..services.broker_service import BrokerService
        
        account = self.get_object()
        
        if account.broker_type != 'BINANCE':
            return Response({
                'success': False,
                'error': 'Cette méthode est uniquement pour Binance'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            service = BrokerService(request.user)
            positions = service.get_positions(account)
            
            # Convertir en format sérialisable
            positions_data = []
            for pos in positions:
                positions_data.append({
                    'symbol': pos.symbol,
                    'quantity': float(pos.quantity),
                    'entry_price': float(pos.entry_price) if pos.entry_price else None,
                    'current_price': float(pos.current_price) if pos.current_price else None,
                    'unrealized_pnl': float(pos.unrealized_pnl) if pos.unrealized_pnl else None,
                    'currency': pos.currency,
                    'side': pos.side,
                    'broker_id': pos.broker_id,
                })
            
            return Response({
                'success': True,
                'count': len(positions_data),
                'positions': positions_data,
            })
        except Exception as e:
            logger.error(f"Error fetching Binance positions for account {account.id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], url_path='test-connection')
    def test_connection(self, request, pk=None):
        """
        POST /api/broker-accounts/1/test-connection/
        Teste la connexion au broker.
        """
        from apps.trading.services.broker_service import BrokerService
        
        account = self.get_object()
        
        try:
            broker_service = BrokerService(request.user)
            result = broker_service.test_connection(account)
            
            return Response({
                'success': result.get('success', False),
                'message': result.get('message', 'Test de connexion effectué'),
                'details': result.get('details', {}),
            })
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'message': f'Erreur lors du test de connexion: {str(e)}',
                    'error': str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """
        POST /api/broker-accounts/1/sync/
        Synchronise les données depuis le broker.
        Body: { "sync_type": "ASSETS" | "PRICES" | "POSITIONS" | "TRADES", "force": false }
        """
        from apps.trading.services.sync.asset_sync_service import AssetSyncService
        from apps.trading.services.sync.price_sync_service import PriceSyncService
        from apps.trading.services.sync.position_sync_service import PositionSyncService
        from apps.trading.services.sync.trade_sync_service import TradeSyncService
        from apps.trading.models import BrokerSyncLog
        from apps.trading.exceptions import SyncException
        from django.utils import timezone
        import logging
        
        logger = logging.getLogger('trading.api.brokers')
        
        account = self.get_object()
        sync_type = request.data.get('sync_type', 'ASSETS').upper()
        force = request.data.get('force', False)
        
        if sync_type not in ['ASSETS', 'PRICES', 'POSITIONS', 'TRADES']:
            return Response(
                {'error': f'Sync type invalide: {sync_type}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Créer un log de synchronisation
        sync_log = BrokerSyncLog.objects.create(
            broker_account=account,
            sync_type=sync_type,
            status='IN_PROGRESS',
            started_at=timezone.now(),
            error_message='',  # Toujours initialiser avec une chaîne vide
        )
        
        try:
            if sync_type == 'ASSETS':
                sync_service = AssetSyncService(request.user)
                # Utiliser sync_all_asset_types pour synchroniser tous les types d'assets
                # au lieu de seulement 'Stock' par défaut
                result = sync_service.sync_all_asset_types(account, limit_per_type=20000)
                # Adapter le format de réponse pour correspondre au format attendu
                if result.get('success'):
                    # Le format de sync_all_asset_types retourne total_created, total_updated
                    result['created'] = result.get('total_created', 0)
                    result['updated'] = result.get('total_updated', 0)
                    # Créer une copie des détails sans référence circulaire
                    import copy
                    result['details'] = {
                        'total_created': result.get('total_created', 0),
                        'total_updated': result.get('total_updated', 0),
                        'by_type': result.get('by_type', {}),
                        'errors_count': len(result.get('errors', [])),
                    }
            elif sync_type == 'PRICES':
                sync_service = PriceSyncService(request.user)
                # sync_current_prices est la méthode principale
                result = sync_service.sync_current_prices(account)
            elif sync_type == 'POSITIONS':
                sync_service = PositionSyncService(request.user)
                try:
                    result = sync_service.sync(account)
                except SyncException as e:
                    # Convertir SyncException en format de résultat
                    result = {
                        'success': False,
                        'message': str(e),
                        'error': str(e),
                        'records_synced': 0,
                    }
            elif sync_type == 'TRADES':
                sync_service = TradeSyncService(request.user)
                try:
                    result = sync_service.sync(account)
                except SyncException as e:
                    # Convertir SyncException en format de résultat
                    result = {
                        'success': False,
                        'message': str(e),
                        'error': str(e),
                        'records_synced': 0,
                    }
            else:
                result = {'success': False, 'message': 'Type de synchronisation inconnu'}
            
            # Mettre à jour le log
            sync_log.status = 'SUCCESS' if result.get('success') else 'FAILED'
            # records_synced peut être dans différents champs selon le service
            sync_log.records_synced = (
                result.get('records_synced', 0) or 
                result.get('created', 0) + result.get('updated', 0) or
                result.get('records', 0) or
                0
            )
            sync_log.completed_at = timezone.now()
            # Toujours utiliser une chaîne vide au lieu de None
            sync_log.error_message = result.get('error', '') if not result.get('success') else ''
            # Convertir details en format JSON-sérialisable (éviter les références circulaires)
            details = result.get('details', {})
            if details:
                # Créer une copie propre sans références circulaires
                import json
                import copy
                try:
                    # Tester si c'est sérialisable en JSON
                    json_str = json.dumps(details)
                    # Parser pour avoir une copie propre
                    sync_log.details = json.loads(json_str)
                except (TypeError, ValueError):
                    # Si non sérialisable, créer une version simplifiée
                    sync_log.details = {
                        'created': result.get('created', result.get('total_created', 0)),
                        'updated': result.get('updated', result.get('total_updated', 0)),
                        'records_synced': result.get('records_synced', 0),
                    }
            else:
                sync_log.details = {}
            sync_log.save()
            
            # Mettre à jour last_sync du compte
            account.last_sync = timezone.now()
            account.save()
            
            # Déterminer le code de statut HTTP approprié
            status_code = status.HTTP_200_OK
            if not result.get('success', False):
                status_code = status.HTTP_400_BAD_REQUEST
            
            return Response({
                'success': result.get('success', False),
                'message': result.get('message', 'Synchronisation terminée'),
                'error': result.get('error') if not result.get('success') else None,
                'sync_log': {
                    'id': sync_log.id,
                    'status': sync_log.status,
                    'records_synced': sync_log.records_synced,
                    'started_at': sync_log.started_at.isoformat(),
                    'completed_at': sync_log.completed_at.isoformat() if sync_log.completed_at else None,
                    'error_message': sync_log.error_message if sync_log.error_message else None,
                },
                'details': result.get('details', {}),
            }, status=status_code)
        except Exception as e:
            sync_log.status = 'FAILED'
            sync_log.completed_at = timezone.now()
            sync_log.error_message = str(e)
            sync_log.save()
            
            return Response(
                {
                    'success': False,
                    'message': f'Erreur lors de la synchronisation: {str(e)}',
                    'error': str(e),
                    'sync_log': {
                        'id': sync_log.id,
                        'status': sync_log.status,
                        'error_message': sync_log.error_message,
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================
# VUE DATATREE - ASSETS AVEC POSITIONS ET ORDERS
# ============================================

from rest_framework.decorators import api_view, permission_classes as perms

logger = logging.getLogger(__name__)


@api_view(['GET'])
@perms([permissions.IsAuthenticated])
def get_assets_with_positions_orders(request):
    """
    GET /api/assets/overview/
    
    Retourne les assets avec leurs positions et orders groupés
    Structure hiérarchique pour DataTree (comme Tabulator v3)
    
    Chaque asset est un parent avec un champ 'children' contenant :
    - Toutes les positions (ouvertes + fermées)
    - Tous les orders (tous statuts)
    
    Si une Position.all_asset n'a pas d'Asset correspondant, 
    on crée automatiquement l'Asset.
    """
    try:
        user = request.user
        
        # =============================================
        # 1. Récupérer tous les Assets concernés
        # =============================================
        
        # Assets qui ont des orders
        order_asset_ids = Order.objects.filter(
            user=user
        ).values_list('asset_id', flat=True).distinct()
        
        # Assets qui ont des positions (via Position.asset)
        position_asset_ids = Position.objects.filter(
            user=user,
            asset__isnull=False
        ).values_list('asset_id', flat=True).distinct()
        
        # AllAssets qui ont des positions mais pas d'Asset correspondant
        # On doit créer les Asset manquants
        positions_without_asset = Position.objects.filter(
            user=user,
            asset__isnull=True,
            all_asset__isnull=False
        ).select_related('all_asset')
        
        # Créer les Assets manquants
        created_asset_ids = []
        for position in positions_without_asset:
            all_asset = position.all_asset
            # Vérifier si un Asset avec ce symbol existe déjà
            existing_asset = Asset.objects.filter(symbol=all_asset.symbol).first()
            if existing_asset:
                # Lier la position à l'Asset existant
                position.asset = existing_asset
                position.save(update_fields=['asset'])
                created_asset_ids.append(existing_asset.id)
            else:
                # Créer un nouvel Asset depuis AllAssets
                new_asset = Asset.create_from_all_asset(all_asset)
                position.asset = new_asset
                position.save(update_fields=['asset'])
                created_asset_ids.append(new_asset.id)
        
        # Combiner tous les IDs d'assets
        all_asset_ids = set(list(order_asset_ids) + list(position_asset_ids) + created_asset_ids)
        
        # Récupérer tous les Assets
        assets = Asset.objects.filter(id__in=all_asset_ids).order_by('symbol')
        
        # =============================================
        # 2. Précharger les données pour éviter N+1
        # =============================================
        
        # Positions par asset_id
        positions_by_asset = {}
        all_positions = Position.objects.filter(
            user=user,
            asset_id__in=all_asset_ids
        ).select_related('broker', 'strategy', 'all_asset')
        
        for pos in all_positions:
            if pos.asset_id not in positions_by_asset:
                positions_by_asset[pos.asset_id] = []
            positions_by_asset[pos.asset_id].append(pos)
        
        # Orders par asset_id
        orders_by_asset = {}
        all_orders = Order.objects.filter(
            user=user,
            asset_id__in=all_asset_ids
        ).select_related('broker')
        
        for order in all_orders:
            if order.asset_id not in orders_by_asset:
                orders_by_asset[order.asset_id] = []
            orders_by_asset[order.asset_id].append(order)
        
        # =============================================
        # 3. Construire la structure hiérarchique
        # =============================================
        
        result_data = []
        
        for asset in assets:
            positions = positions_by_asset.get(asset.id, [])
            orders = orders_by_asset.get(asset.id, [])
            
            # Calculer les totaux
            total_position_size = sum(float(pos.quantity) for pos in positions if pos.is_open)
            total_pending_quantity = sum(
                float(order.quantity) for order in orders 
                if order.status in ['PENDING', 'OPEN']
            )
            
            # Calculer le net position (LONG = +, SHORT = -)
            net_position = 0.0
            for pos in positions:
                if pos.is_open:
                    if pos.side == 'LONG':
                        net_position += float(pos.quantity)
                    else:
                        net_position -= float(pos.quantity)
            
            # Compter positions et orders
            open_positions_count = sum(1 for pos in positions if pos.is_open)
            closed_positions_count = sum(1 for pos in positions if not pos.is_open)
            pending_orders_count = sum(1 for o in orders if o.status in ['PENDING', 'OPEN'])
            
            # Calculer P&L total
            total_pnl = sum(float(pos.pnl or 0) for pos in positions if pos.is_open)
            
            # =============================================
            # 3.1 Créer la ligne PARENT (Asset)
            # =============================================
            asset_row = {
                'id': f"asset_{asset.id}",
                'type': 'asset',
                'asset_id': asset.id,
                'symbol': asset.symbol,
                'name': asset.name,
                'asset_type': asset.asset_type,
                'currency': asset.currency,
                'current_price': float(asset.current_price) if asset.current_price else None,
                'total_position_size': total_position_size,
                'total_pending_quantity': total_pending_quantity,
                'net_position': net_position,
                'total_pnl': total_pnl,
                'positions_count': open_positions_count,
                'closed_positions_count': closed_positions_count,
                'pending_orders_count': pending_orders_count,
                'has_children': len(positions) > 0 or len(orders) > 0,
                'children': []
            }
            
            # =============================================
            # 3.2 Ajouter les POSITIONS comme enfants
            # =============================================
            for pos in positions:
                position_row = {
                    'id': f"position_{pos.id}",
                    'type': 'position',
                    'position_id': pos.id,
                    'symbol': asset.symbol,
                    'name': asset.name,
                    'side': pos.side,
                    'size': float(pos.quantity),
                    'entry_price': float(pos.entry_price) if pos.entry_price else 0.0,
                    'current_price': float(pos.current_price) if pos.current_price else None,
                    'pnl': float(pos.pnl) if pos.pnl else 0.0,
                    'pnl_percent': float(pos.pnl_percent) if pos.pnl_percent else 0.0,
                    'status': 'OPEN' if pos.is_open else 'CLOSED',
                    'stop_loss': float(pos.stop_loss) if pos.stop_loss else None,
                    'take_profit': float(pos.take_profit) if pos.take_profit else None,
                    'broker_name': pos.broker.name if pos.broker else None,
                    'strategy_name': pos.strategy.name if pos.strategy else None,
                    'opened_at': pos.opened_at.strftime('%d/%m/%Y %H:%M') if pos.opened_at else '',
                    'closed_at': pos.closed_at.strftime('%d/%m/%Y %H:%M') if pos.closed_at else None,
                }
                asset_row['children'].append(position_row)
            
            # =============================================
            # 3.3 Ajouter les ORDERS comme enfants
            # =============================================
            for order in orders:
                order_row = {
                    'id': f"order_{order.id}",
                    'type': 'order',
                    'order_id': order.id,
                    'symbol': asset.symbol,
                    'name': asset.name,
                    'side': order.side,
                    'quantity': float(order.quantity),
                    'filled_quantity': float(order.filled_quantity) if order.filled_quantity else 0.0,
                    'price': float(order.price) if order.price else None,
                    'stop_price': float(order.stop_price) if order.stop_price else None,
                    'order_type': order.order_type,
                    'status': order.status,
                    'broker_name': order.broker.name if order.broker else None,
                    'broker_order_id': order.broker_order_id or None,
                    'created_at': order.created_at.strftime('%d/%m/%Y %H:%M') if order.created_at else '',
                    'updated_at': order.updated_at.strftime('%d/%m/%Y %H:%M') if order.updated_at else None,
                }
                asset_row['children'].append(order_row)
            
            result_data.append(asset_row)
        
        # =============================================
        # 4. Ajouter les assets sans positions ni orders (optionnel)
        # =============================================
        
        # Paramètre pour inclure les assets vides
        include_empty = request.query_params.get('include_empty', 'true').lower() == 'true'
        
        if include_empty:
            # Récupérer tous les autres assets actifs
            other_assets = Asset.objects.filter(
                is_active=True
            ).exclude(
                id__in=all_asset_ids
            ).order_by('symbol')
            
            for asset in other_assets:
                asset_row = {
                    'id': f"asset_{asset.id}",
                    'type': 'asset',
                    'asset_id': asset.id,
                    'symbol': asset.symbol,
                    'name': asset.name,
                    'asset_type': asset.asset_type,
                    'currency': asset.currency,
                    'current_price': float(asset.current_price) if asset.current_price else None,
                    'total_position_size': 0,
                    'total_pending_quantity': 0,
                    'net_position': 0,
                    'total_pnl': 0,
                    'positions_count': 0,
                    'closed_positions_count': 0,
                    'pending_orders_count': 0,
                    'has_children': False,
                    'children': []
                }
                result_data.append(asset_row)
        
        # Trier par symbole
        result_data.sort(key=lambda x: x['symbol'])
        
        return Response({
            'success': True,
            'count': len(result_data),
            'data': result_data
        })
        
    except Exception as e:
        logger.error(f"Erreur dans get_assets_with_positions_orders: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': f'Erreur lors de la récupération des données: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ============================================
# VIEWSET ANALYTICS
# ============================================

class AnalyticsViewSet(viewsets.ViewSet):
    """
    ViewSet pour les analyses et statistiques du dashboard.
    """
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        GET /api/analytics/summary/
        Retourne les KPIs principaux pour le dashboard.
        """
        user = request.user
        
        # 1. Calculer la Valeur Totale (Cash + Investi)
        # ---------------------------------------------
        broker_accounts = BrokerAccount.objects.filter(user=user, is_active=True)
        open_positions = Position.objects.filter(user=user, is_open=True)
        
        # Cash: Somme des balances converties en EUR
        total_cash = sum(account.balance or 0 for account in broker_accounts)
        
        # Investi: Somme de (Quantité * Prix Actuel)
        total_invested = 0
        for pos in open_positions:
            price = pos.current_price or pos.entry_price or 0
            if price and pos.quantity:
                total_invested += float(price) * float(pos.quantity)
                
        total_value = float(total_cash) + total_invested
        
        # 2. Calculer le Taux de Réussite (Trades Fermés uniquement)
        # ----------------------------------------------------------
        closed_positions = Position.objects.filter(user=user, is_open=False)
        total_closed = closed_positions.count()
        
        # PnL est une property, on ne peut pas filtrer dessus directement via l'ORM
        # sans annotation complexe. On le fait en Python.
        winning_positions = 0
        for p in closed_positions:
            if p.pnl and p.pnl > 0:
                winning_positions += 1
        
        win_rate = (winning_positions / total_closed * 100) if total_closed > 0 else 0
        
        # 3. Breakdown par Broker
        # -----------------------
        breakdown = []
        for account in broker_accounts:
            # Cash du broker
            account_cash = float(account.balance or 0)
            
            # Valeur des positions sur ce broker
            account_positions = open_positions.filter(broker=account.broker)
            
            account_invested = 0
            # Filtrer les positions qui correspondent au broker de ce compte
            pos_for_broker = [p for p in open_positions if p.broker_id == account.broker_id]
            
            for pos in pos_for_broker:
                 price = pos.current_price or pos.entry_price or 0
                 if price and pos.quantity:
                    account_invested += float(price) * float(pos.quantity)
            
            breakdown.append({
                'broker_name': account.name or account.broker.name,
                'broker_id': account.broker_id,
                'broker_account_id': account.id,
                'total': account_cash + account_invested,
                'cash': account_cash,
                'invested': account_invested
            })

        # 4. Historique (Graphique Evolution)
        # -----------------------------------
        # Récupérer les 30 derniers snapshots
        snapshots = PortfolioSnapshot.objects.filter(user=user).order_by('date')[:30]
        history = [
            {
                'date': s.date.isoformat(),
                'total_value': float(s.total_value),
                'invested': float(s.total_invested),
                'cash': float(s.total_cash)
            }
            for s in snapshots
        ]
        
        # Ajouter le point actuel "Live" à l'historique pour que le graphe soit à jour
        from django.utils import timezone
        history.append({
            'date': timezone.now().isoformat(),
            'total_value': total_value,
            'invested': total_invested,
            'cash': float(total_cash)
        })

        return Response({
            'kpi': {
                'total_value': round(total_value, 2),
                'total_invested': round(total_invested, 2),
                'total_cash': round(float(total_cash), 2),
                'win_rate': round(win_rate, 2),
                'total_closed_positions': total_closed,
                'active_positions': open_positions.count()
            },
            'breakdown': breakdown,
            'history': history
        })
