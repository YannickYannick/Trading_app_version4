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
    """
    serializer_class = BrokerAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    filterset_fields = ['broker', 'is_active', 'is_demo']
    ordering = ['broker__name']
    
    def get_queryset(self):
        return BrokerAccount.objects.filter(user=self.request.user)
    
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
                    'items_synced': log.items_synced,
                    'started_at': log.started_at.isoformat(),
                    'error': log.error_message if log.status == 'FAILED' else None,
                }
                for log in logs
            ]
        })
    
    @action(detail=True, methods=['post'])
    def refresh_balance(self, request, pk=None):
        """
        POST /api/broker-accounts/1/refresh_balance/
        Rafraîchit la balance du compte.
        (À implémenter avec le service broker)
        """
        account = self.get_object()
        
        # TODO: Appeler le service broker pour rafraîchir la balance
        # balance = broker_service.get_balance(account)
        # account.balance = balance
        # account.balance_updated_at = timezone.now()
        # account.save()
        
        return Response({
            'status': 'Balance refresh requested',
            'account': BrokerAccountSerializer(account).data
        })
