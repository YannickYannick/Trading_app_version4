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

from apps.trading.models import (
    AllAssets, Asset, AssetPrice, Position, Trade, Order,
    Strategy, StrategyPerformance, Broker, BrokerAccount, BrokerSyncLog,
    ScheduledTask, TaskExecutionLog
)
from .serializers import (
    AllAssetsSerializer, AssetSerializer, AssetNestedSerializer, AssetPriceSerializer,
    PositionSerializer, TradeSerializer, OrderSerializer,
    StrategySerializer, BrokerSerializer, BrokerAccountSerializer
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
    
    @action(detail=False, methods=['post'], url_path='validate-yahoo-symbols')
    def validate_yahoo_symbols(self, request):
        """
        POST /api/all-assets/validate-yahoo-symbols/
        Met à jour les symboles Yahoo Finance pour tous les assets.
        
        Query params optionnels:
        - reset: Si 'true', réinitialise tous les symboles avant validation
        - limit: Nombre max d'assets à traiter (défaut: 100)
        - platform: Filtrer par plateforme (SAXO, BINANCE, etc.)
        """
        from ..services.yahoo_validator import validate_single_asset, ValidationStats
        from django.utils import timezone
        import logging
        
        logger = logging.getLogger('trading.api.assets')
        
        try:
            # Récupérer les paramètres
            reset = request.query_params.get('reset', 'false').lower() == 'true'
            limit = int(request.query_params.get('limit', 100))
            platform = request.query_params.get('platform')
            
            # Construire le queryset
            queryset = AllAssets.objects.all()
            
            if platform:
                queryset = queryset.filter(platform=platform)
            
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
            
            # Valider chaque asset
            for asset in assets_list:
                try:
                    # Utiliser validate_single_asset qui ne nécessite pas broker_name
                    result = validate_single_asset(asset, broker_config={}, tolerance_percent=5.0)
                    
                    # Mettre à jour les statistiques
                    if result.status.value.startswith('VALIDATED'):
                        stats.validated_y4 += result.status.value == 'VALIDATED_Y4'
                        stats.validated_y3 += result.status.value == 'VALIDATED_Y3'
                        stats.validated_y0 += result.status.value == 'VALIDATED_Y0'
                    elif result.status.value == 'NOT_FOUND':
                        stats.not_found += 1
                    else:
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
                'processed': stats.processed_total,
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
    
    filterset_fields = ['asset_type', 'currency', 'is_active']
    search_fields = ['symbol', 'name', 'sector', 'industry']
    ordering_fields = ['symbol', 'name', 'current_price', 'market_cap', 'pe_ratio']
    ordering = ['symbol']
    
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
    search_fields = ['asset__symbol', 'asset__name']
    ordering_fields = ['opened_at', 'entry_price', 'quantity']
    ordering = ['-opened_at']
    
    def get_queryset(self):
        """Filtrer par utilisateur connecté."""
        return Position.objects.filter(user=self.request.user)
    
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
    search_fields = ['asset__symbol', 'broker_trade_id']
    ordering_fields = ['executed_at', 'price', 'quantity']
    ordering = ['-executed_at']
    
    def get_queryset(self):
        return Trade.objects.filter(user=self.request.user)
    
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
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """GET /api/orders/pending/ → Ordres en attente."""
        orders = self.filter_queryset(
            self.get_queryset().filter(status__in=['PENDING', 'OPEN', 'PARTIALLY_FILLED'])
        )
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)
    
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
        Annule un ordre en attente.
        """
        order = self.get_object()
        
        if order.status in ['FILLED', 'CANCELLED', 'EXPIRED']:
            return Response(
                {'error': f'Cannot cancel order with status {order.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'CANCELLED'
        order.save()
        
        return Response({
            'status': 'Order cancelled',
            'order': OrderSerializer(order).data
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
                # Pour Binance, utiliser directement EUR
                eur_balance = balances.get('EUR', Decimal('0'))
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
                # Pour Binance, utiliser directement EUR
                eur_balance = balances.get('EUR', Decimal('0'))
                currency = 'EUR'
            
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
