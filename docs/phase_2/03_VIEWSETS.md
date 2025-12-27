# 🎯 ViewSets

## Qu'est-ce qu'un ViewSet ?

Un ViewSet crée automatiquement tous les endpoints CRUD :
- `GET /assets/` → list()
- `POST /assets/` → create()
- `GET /assets/{id}/` → retrieve()
- `PUT /assets/{id}/` → update()
- `PATCH /assets/{id}/` → partial_update()
- `DELETE /assets/{id}/` → destroy()

## Structure

```
apps/trading/api/
└── views.py
```

## ViewSets créés

### AllAssetsViewSet

```python
class AllAssetsViewSet(viewsets.ModelViewSet):
    """Catalogue universel des assets."""
    queryset = AllAssets.objects.all()
    serializer_class = AllAssetsSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LargePagination
    
    filterset_fields = ['platform', 'asset_type', 'market', 'is_tradable']
    search_fields = ['symbol', 'name']
    ordering_fields = ['symbol', 'name', 'platform']
    ordering = ['symbol']
    
    @action(detail=False, methods=['get'])
    def saxo(self, request):
        """GET /api/all-assets/saxo/"""
        assets = self.filter_queryset(self.get_queryset().filter(platform='SAXO'))
        # ...
    
    @action(detail=False, methods=['get'])
    def binance(self, request):
        """GET /api/all-assets/binance/"""
        # ...
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """GET /api/all-assets/stats/"""
        queryset = self.get_queryset()
        return Response({
            'total': queryset.count(),
            'by_platform': list(queryset.values('platform').annotate(count=Count('id'))),
            'by_type': list(queryset.values('asset_type').annotate(count=Count('id'))),
        })
    
    @action(detail=False, methods=['get'], url_path='search')
    def search_assets(self, request):
        """GET /api/all-assets/search/?q=AAPL"""
        query = request.query_params.get('q', '')
        if len(query) < 2:
            return Response({'error': 'Min 2 characters'}, status=400)
        assets = self.get_queryset().filter(
            Q(symbol__icontains=query) | Q(name__icontains=query)
        )[:50]
        return Response({...})
```

### AssetViewSet

```python
class AssetViewSet(viewsets.ModelViewSet):
    """Assets enrichis avec données Yahoo Finance."""
    queryset = Asset.objects.filter(is_active=True)
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=True, methods=['get'])
    def prices(self, request, pk=None):
        """GET /api/assets/{id}/prices/"""
        asset = self.get_object()
        prices = AssetPrice.objects.filter(asset=asset).order_by('-date')[:100]
        return Response(AssetPriceSerializer(prices, many=True).data)
    
    @action(detail=True, methods=['get'])
    def positions(self, request, pk=None):
        """GET /api/assets/{id}/positions/"""
        # ...
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """GET /api/assets/{id}/summary/"""
        asset = self.get_object()
        positions = Position.objects.filter(asset=asset, user=request.user)
        return Response({
            'asset': AssetSerializer(asset).data,
            'positions': {...},
            'trades': {...}
        })
    
    @action(detail=True, methods=['post'])
    def update_price(self, request, pk=None):
        """POST /api/assets/{id}/update_price/"""
        asset = self.get_object()
        asset.current_price = request.data.get('price')
        asset.save()
        return Response(AssetSerializer(asset).data)
```

### PositionViewSet

```python
class PositionViewSet(viewsets.ModelViewSet):
    """Positions de trading."""
    serializer_class = PositionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filtrer par utilisateur."""
        return Position.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Ajouter l'utilisateur automatiquement."""
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def open(self, request):
        """GET /api/positions/open/"""
        positions = self.get_queryset().filter(is_open=True)
        return Response(self.get_serializer(positions, many=True).data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """GET /api/positions/summary/"""
        positions = self.get_queryset().filter(is_open=True)
        return Response({
            'total_positions': positions.count(),
            'total_value': sum(...),
            'total_pnl': sum(...),
        })
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """POST /api/positions/{id}/close/"""
        position = self.get_object()
        position.is_open = False
        position.closed_at = timezone.now()
        position.save()
        return Response(PositionSerializer(position).data)
```

### TradeViewSet

```python
class TradeViewSet(viewsets.ModelViewSet):
    serializer_class = TradeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Trade.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """GET /api/trades/recent/"""
        trades = self.get_queryset()[:20]
        return Response(self.get_serializer(trades, many=True).data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """GET /api/trades/stats/"""
        trades = self.get_queryset()
        return Response({
            'total_trades': trades.count(),
            'buy_trades': trades.filter(trade_type='BUY').count(),
            'sell_trades': trades.filter(trade_type='SELL').count(),
        })
```

### OrderViewSet

```python
class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """GET /api/orders/pending/"""
        orders = self.get_queryset().filter(status__in=['PENDING', 'OPEN'])
        return Response(self.get_serializer(orders, many=True).data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """POST /api/orders/{id}/cancel/"""
        order = self.get_object()
        if order.status in ['FILLED', 'CANCELLED']:
            return Response({'error': 'Cannot cancel'}, status=400)
        order.status = 'CANCELLED'
        order.save()
        return Response({'status': 'Order cancelled'})
```

### StrategyViewSet

```python
class StrategyViewSet(viewsets.ModelViewSet):
    serializer_class = StrategySerializer
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """POST /api/strategies/{id}/activate/"""
        strategy = self.get_object()
        strategy.is_active = True
        strategy.save()
        return Response({'status': 'Strategy activated'})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """POST /api/strategies/{id}/deactivate/"""
        # ...
```

## Pagination personnalisée

```python
class StandardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200

class LargePagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 500
```

## Décorateur @action

```python
@action(
    detail=True,              # Sur un objet spécifique (/assets/1/action/)
    detail=False,             # Sur la collection (/assets/action/)
    methods=['get', 'post'],  # Méthodes HTTP
    url_path='custom-name',   # Nom personnalisé dans l'URL
    permission_classes=[...], # Permissions spécifiques
)
def my_action(self, request, pk=None):
    pass
```

