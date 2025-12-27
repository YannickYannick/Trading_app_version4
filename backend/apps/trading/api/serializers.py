"""
Serializers pour l'API REST Trading.
"""
from rest_framework import serializers
from apps.trading.models import (
    Asset, AssetPrice, Position, Trade, Order,
    Strategy, Broker, BrokerAccount
)


class AssetSerializer(serializers.ModelSerializer):
    """Serializer pour les assets."""
    
    class Meta:
        model = Asset
        fields = [
            'id', 'symbol', 'name', 'asset_type', 'currency', 'exchange',
            'current_price', 'price_updated_at', 'is_active', 'description',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AssetPriceSerializer(serializers.ModelSerializer):
    """Serializer pour l'historique des prix."""
    asset_symbol = serializers.CharField(source='asset.symbol', read_only=True)
    
    class Meta:
        model = AssetPrice
        fields = [
            'id', 'asset', 'asset_symbol', 'date',
            'open_price', 'high_price', 'low_price', 'close_price', 'volume'
        ]


class BrokerSerializer(serializers.ModelSerializer):
    """Serializer pour les brokers."""
    
    class Meta:
        model = Broker
        fields = [
            'id', 'name', 'broker_type', 'api_base_url', 'is_active',
            'supports_stocks', 'supports_crypto', 'supports_forex', 'supports_futures'
        ]


class BrokerAccountSerializer(serializers.ModelSerializer):
    """Serializer pour les comptes broker."""
    broker_name = serializers.CharField(source='broker.name', read_only=True)
    
    class Meta:
        model = BrokerAccount
        fields = [
            'id', 'broker', 'broker_name', 'account_id', 'account_name',
            'balance', 'currency', 'balance_updated_at',
            'is_active', 'is_demo'
        ]
        # Ne pas exposer les tokens
        extra_kwargs = {
            'access_token': {'write_only': True},
            'refresh_token': {'write_only': True},
        }


class StrategySerializer(serializers.ModelSerializer):
    """Serializer pour les stratégies."""
    
    class Meta:
        model = Strategy
        fields = [
            'id', 'name', 'description', 'risk_level',
            'max_position_size', 'max_daily_loss', 'parameters',
            'is_active', 'is_automated', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PositionSerializer(serializers.ModelSerializer):
    """Serializer pour les positions."""
    asset_symbol = serializers.CharField(source='asset.symbol', read_only=True)
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    broker_name = serializers.CharField(source='broker.name', read_only=True)
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    pnl = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    pnl_percent = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Position
        fields = [
            'id', 'asset', 'asset_symbol', 'asset_name',
            'broker', 'broker_name', 'strategy', 'strategy_name',
            'side', 'quantity', 'entry_price', 'current_price',
            'stop_loss', 'take_profit', 'is_open',
            'opened_at', 'closed_at', 'pnl', 'pnl_percent'
        ]


class TradeSerializer(serializers.ModelSerializer):
    """Serializer pour les trades."""
    asset_symbol = serializers.CharField(source='asset.symbol', read_only=True)
    broker_name = serializers.CharField(source='broker.name', read_only=True)
    total_value = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    
    class Meta:
        model = Trade
        fields = [
            'id', 'asset', 'asset_symbol', 'broker', 'broker_name',
            'position', 'trade_type', 'quantity', 'price', 'fees',
            'total_value', 'executed_at', 'broker_trade_id'
        ]


class OrderSerializer(serializers.ModelSerializer):
    """Serializer pour les ordres."""
    asset_symbol = serializers.CharField(source='asset.symbol', read_only=True)
    broker_name = serializers.CharField(source='broker.name', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'asset', 'asset_symbol', 'broker', 'broker_name',
            'order_type', 'side', 'status',
            'quantity', 'filled_quantity', 'price', 'stop_price',
            'broker_order_id', 'created_at', 'updated_at'
        ]

