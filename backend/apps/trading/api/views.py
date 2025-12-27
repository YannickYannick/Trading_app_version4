"""
Vues API REST pour l'application Trading.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count

from apps.trading.models import (
    Asset, AssetPrice, Position, Trade, Order,
    Strategy, Broker, BrokerAccount
)
from .serializers import (
    AssetSerializer, AssetPriceSerializer,
    PositionSerializer, TradeSerializer, OrderSerializer,
    StrategySerializer, BrokerSerializer, BrokerAccountSerializer
)


class AssetViewSet(viewsets.ModelViewSet):
    """ViewSet pour les assets."""
    queryset = Asset.objects.filter(is_active=True)
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtres optionnels
        asset_type = self.request.query_params.get('type')
        if asset_type:
            queryset = queryset.filter(asset_type=asset_type)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                symbol__icontains=search
            ) | queryset.filter(
                name__icontains=search
            )
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def prices(self, request, pk=None):
        """Récupère l'historique des prix d'un asset."""
        asset = self.get_object()
        prices = AssetPrice.objects.filter(asset=asset).order_by('-date')[:100]
        serializer = AssetPriceSerializer(prices, many=True)
        return Response(serializer.data)


class PositionViewSet(viewsets.ModelViewSet):
    """ViewSet pour les positions."""
    serializer_class = PositionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Position.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def open(self, request):
        """Récupère uniquement les positions ouvertes."""
        positions = self.get_queryset().filter(is_open=True)
        serializer = self.get_serializer(positions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Récupère un résumé des positions."""
        positions = self.get_queryset().filter(is_open=True)
        total_value = sum(
            (p.current_price or p.entry_price) * p.quantity 
            for p in positions
        )
        total_pnl = sum(p.pnl or 0 for p in positions)
        
        return Response({
            'total_positions': positions.count(),
            'total_value': total_value,
            'total_pnl': total_pnl,
        })


class TradeViewSet(viewsets.ModelViewSet):
    """ViewSet pour les trades."""
    serializer_class = TradeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Trade.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Récupère les trades récents."""
        trades = self.get_queryset()[:20]
        serializer = self.get_serializer(trades, many=True)
        return Response(serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet pour les ordres."""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Récupère les ordres en attente."""
        orders = self.get_queryset().filter(
            status__in=['PENDING', 'OPEN', 'PARTIALLY_FILLED']
        )
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Annule un ordre."""
        order = self.get_object()
        if order.status in ['FILLED', 'CANCELLED', 'EXPIRED']:
            return Response(
                {'error': 'Cannot cancel this order'},
                status=status.HTTP_400_BAD_REQUEST
            )
        order.status = 'CANCELLED'
        order.save()
        return Response({'status': 'Order cancelled'})


class StrategyViewSet(viewsets.ModelViewSet):
    """ViewSet pour les stratégies."""
    serializer_class = StrategySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Strategy.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BrokerViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les brokers (lecture seule)."""
    queryset = Broker.objects.filter(is_active=True)
    serializer_class = BrokerSerializer
    permission_classes = [permissions.IsAuthenticated]


class BrokerAccountViewSet(viewsets.ModelViewSet):
    """ViewSet pour les comptes broker."""
    serializer_class = BrokerAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return BrokerAccount.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

