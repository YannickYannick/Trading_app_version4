# 🔄 Serializers

## Qu'est-ce qu'un Serializer ?

Un Serializer convertit :
- **Modèle Django → JSON** (pour l'API)
- **JSON → Modèle Django** (pour créer/modifier)

## Structure

```
apps/trading/api/
└── serializers.py
```

## Serializers créés

### AllAssetsSerializer

```python
class AllAssetsSerializer(serializers.ModelSerializer):
    """Serializer pour le catalogue universel."""
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AllAssets
        fields = [
            'id', 'symbol', 'name', 'display_name', 'platform', 'asset_type',
            'market', 'currency', 'exchange', 'is_tradable',
            'saxo_uic', 'binance_base_asset',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_display_name(self, obj):
        return f"{obj.symbol} - {obj.name}"
```

### AssetSerializer

```python
class AssetSerializer(serializers.ModelSerializer):
    """Serializer pour les assets enrichis."""
    all_asset_symbol = serializers.CharField(source='all_asset.symbol', read_only=True)
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Asset
        fields = [
            'id', 'all_asset', 'all_asset_symbol',
            'symbol', 'name', 'display_name', 'asset_type', 'currency',
            'current_price', 'sector', 'industry', 'market_cap',
            'is_active', 'created_at', 'updated_at'
        ]
```

### AssetNestedSerializer (Léger)

```python
class AssetNestedSerializer(serializers.ModelSerializer):
    """Serializer léger pour les relations."""
    class Meta:
        model = Asset
        fields = ['id', 'symbol', 'name', 'current_price', 'currency']
```

### PositionSerializer

```python
class PositionSerializer(serializers.ModelSerializer):
    """Serializer pour les positions."""
    # Relations imbriquées (lecture)
    asset = AssetNestedSerializer(read_only=True)
    broker_name = serializers.CharField(source='broker.name', read_only=True)
    strategy = StrategyNestedSerializer(read_only=True)
    
    # IDs pour écriture
    asset_id = serializers.IntegerField(write_only=True, required=False)
    broker_id = serializers.IntegerField(write_only=True, required=False)
    strategy_id = serializers.IntegerField(write_only=True, required=False)
    
    # Champs calculés
    pnl = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    pnl_percent = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Position
        fields = [
            'id', 'asset', 'asset_id', 'broker_name', 'broker_id',
            'strategy', 'strategy_id', 'side', 'quantity', 'entry_price',
            'current_price', 'stop_loss', 'take_profit', 'is_open',
            'opened_at', 'closed_at', 'pnl', 'pnl_percent'
        ]
        read_only_fields = ['id', 'opened_at', 'pnl', 'pnl_percent']
    
    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("La quantité doit être positive")
        return value
```

### TradeSerializer

```python
class TradeSerializer(serializers.ModelSerializer):
    """Serializer pour les trades."""
    asset = AssetNestedSerializer(read_only=True)
    asset_id = serializers.IntegerField(write_only=True, required=False)
    total_value = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    
    class Meta:
        model = Trade
        fields = [
            'id', 'asset', 'asset_id', 'broker_name',
            'trade_type', 'quantity', 'price', 'fees',
            'total_value', 'executed_at'
        ]
```

### OrderSerializer

```python
class OrderSerializer(serializers.ModelSerializer):
    """Serializer pour les ordres."""
    asset = AssetNestedSerializer(read_only=True)
    fill_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'asset', 'asset_id',
            'order_type', 'side', 'status',
            'quantity', 'filled_quantity', 'fill_percentage',
            'price', 'stop_price', 'created_at'
        ]
    
    def get_fill_percentage(self, obj):
        if obj.quantity and obj.quantity > 0:
            return round((obj.filled_quantity / obj.quantity) * 100, 2)
        return 0
    
    def validate(self, data):
        """Validations multi-champs."""
        if data.get('order_type') == 'LIMIT' and not data.get('price'):
            raise serializers.ValidationError({'price': "Un ordre LIMIT nécessite un prix"})
        return data
```

## Techniques utilisées

### 1. Champs calculés (SerializerMethodField)

```python
display_name = serializers.SerializerMethodField()

def get_display_name(self, obj):
    return f"{obj.symbol} - {obj.name}"
```

### 2. Champs en lecture seule depuis relations

```python
broker_name = serializers.CharField(source='broker.name', read_only=True)
```

### 3. Champs write_only pour les IDs

```python
asset_id = serializers.IntegerField(write_only=True, required=False)
```

### 4. Serializers imbriqués

```python
asset = AssetNestedSerializer(read_only=True)
```

### 5. Validations personnalisées

```python
def validate_quantity(self, value):
    if value <= 0:
        raise serializers.ValidationError("Doit être positif")
    return value

def validate(self, data):
    # Validation multi-champs
    return data
```

## JSON produit

```json
{
  "id": 1,
  "asset": {
    "id": 1,
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "current_price": "150.50",
    "currency": "USD"
  },
  "side": "LONG",
  "quantity": "10.00",
  "entry_price": "145.00",
  "current_price": "150.50",
  "pnl": "55.00",
  "pnl_percent": "3.79",
  "is_open": true
}
```

