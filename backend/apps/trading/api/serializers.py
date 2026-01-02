"""
Serializers pour l'API REST Trading.

Un Serializer convertit automatiquement :
- Modèle Django → JSON (pour l'API)
- JSON → Modèle Django (pour créer/modifier)
"""
from rest_framework import serializers
from apps.trading.models import (
    AllAssets, Asset, AssetPrice, AllAssetPriceHistory, Position, Trade, Order,
    Strategy, StrategyPerformance, Broker, BrokerAccount
)


# ============================================
# SERIALIZERS DE BASE
# ============================================

class AllAssetsSerializer(serializers.ModelSerializer):
    """
    Serializer pour AllAssets (catalogue universel).
    
    Convertit automatiquement un AllAssets en JSON :
    {
        "id": 1,
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "platform": "SAXO",
        ...
    }
    """
    # Champ calculé : nom d'affichage
    display_name = serializers.SerializerMethodField()
    # Champ calculé : informations sur l'historique des prix
    price_history_info = serializers.SerializerMethodField()
    
    class Meta:
        model = AllAssets
        fields = [
            'id', 'symbol', 'name', 'display_name', 'platform', 'asset_type', 'market',
            'currency', 'exchange', 'is_tradable', 'last_updated', 'created_at',
            'saxo_uic', 'saxo_exchange_id', 'saxo_country_code',
            'symbole_yahoo', 'yahoo_validation_method', 'yahoo_validated_at',
            'price_history_days', 'price_history_updated_at', 'price_history_info',
            'binance_base_asset', 'binance_quote_asset', 'binance_status'
        ]
        read_only_fields = ['id', 'last_updated', 'created_at']
    
    def get_display_name(self, obj):
        """Champ calculé : symbole + nom."""
        return f"{obj.symbol} - {obj.name}"
    
    def get_price_history_info(self, obj):
        """Informations sur l'historique des prix."""
        if not obj.has_price_history:
            return None
        return {
            'days_count': obj.price_history_days or obj.get_price_history_count(),
            'updated_at': obj.price_history_updated_at.isoformat() if obj.price_history_updated_at else None,
            'date_range': {
                'first': obj.get_price_history_dates()[-1] if obj.get_price_history_dates() else None,
                'last': obj.get_price_history_dates()[0] if obj.get_price_history_dates() else None
            }
        }


class AssetSerializer(serializers.ModelSerializer):
    """
    Serializer pour Asset (données enrichies).
    
    Inclut les infos de AllAssets si disponible.
    """
    # Infos de AllAssets (lecture seule)
    all_asset_symbol = serializers.CharField(source='all_asset.symbol', read_only=True)
    all_asset_platform = serializers.CharField(source='all_asset.platform', read_only=True)
    
    # Champs calculés
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Asset
        fields = [
            'id', 'all_asset', 'all_asset_symbol', 'all_asset_platform',
            'symbol', 'name', 'display_name', 'asset_type', 'currency', 'exchange',
            'current_price', 'price_updated_at', 'is_active', 'description',
            'sector', 'industry', 'market_cap', 'pe_ratio', 'dividend_yield',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_display_name(self, obj):
        return f"{obj.symbol} - {obj.name}"


class AssetNestedSerializer(serializers.ModelSerializer):
    """Serializer léger pour Asset (utilisé dans les relations)."""
    class Meta:
        model = Asset
        fields = ['id', 'symbol', 'name', 'current_price', 'currency']


class AssetPriceSerializer(serializers.ModelSerializer):
    """Serializer pour l'historique des prix."""
    asset_symbol = serializers.CharField(source='asset.symbol', read_only=True)
    
    class Meta:
        model = AssetPrice
        fields = [
            'id', 'asset', 'asset_symbol', 'date',
            'open_price', 'high_price', 'low_price', 'close_price', 'volume'
        ]


class AllAssetPriceHistorySerializer(serializers.ModelSerializer):
    """Serializer pour l'historique des prix d'un AllAsset."""
    all_asset_symbol = serializers.CharField(source='all_asset.symbol', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    
    class Meta:
        model = AllAssetPriceHistory
        fields = [
            'id', 'all_asset', 'all_asset_symbol', 'date',
            'open_price', 'high_price', 'low_price', 'close_price', 'volume',
            'source', 'source_display', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================
# SERIALIZERS BROKERS
# ============================================

class BrokerSerializer(serializers.ModelSerializer):
    """Serializer pour les brokers."""
    
    class Meta:
        model = Broker
        fields = [
            'id', 'name', 'broker_type', 'api_base_url', 'is_active',
            'supports_stocks', 'supports_crypto', 'supports_forex', 'supports_futures'
        ]


class BrokerAccountSerializer(serializers.ModelSerializer):
    """
    Serializer pour les comptes broker.
    Architecture compatible avec BrokerCredentials de la v3.
    
    ⚠️ Les tokens et secrets ne sont JAMAIS exposés dans l'API en lecture !
    """
    broker_name = serializers.CharField(source='broker.name', read_only=True, allow_null=True)
    broker_type_display = serializers.CharField(source='get_broker_type_display', read_only=True)
    environment_display = serializers.CharField(source='get_environment_display', read_only=True)
    
    class Meta:
        model = BrokerAccount
        fields = [
            # Identifiants
            'id', 'name', 'broker', 'broker_name', 'broker_type', 'broker_type_display',
            'account_id', 'environment', 'environment_display',
            
            # Credentials Saxo (write_only pour sécurité)
            'saxo_client_id', 'saxo_client_secret', 'saxo_redirect_uri', 'saxo_environment',
            'saxo_access_token', 'saxo_refresh_token', 'saxo_token_expires_at',
            
            # Credentials Binance (write_only pour sécurité)
            'binance_api_key', 'binance_api_secret', 'binance_testnet',
            
            # Credentials génériques
            'api_key', 'api_secret', 'client_id', 'client_secret',
            'access_token', 'refresh_token', 'token_expires_at',
            'extra_credentials',
            
            # Configuration auto-refresh
            'auto_refresh_enabled', 'auto_refresh_frequency',
            
            # Balance et statut
            'balance', 'currency', 'balance_updated_at', 'last_sync',
            'is_active', 'is_demo', 'is_sandbox',
            
            # Timestamps
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'balance_updated_at',
            'last_sync', 'broker_name', 'broker_type_display', 'environment_display'
        ]
        # Ne JAMAIS exposer les secrets en lecture
        extra_kwargs = {
            'saxo_client_secret': {'write_only': True},
            'saxo_access_token': {'write_only': True},
            'saxo_refresh_token': {'write_only': True},
            'binance_api_secret': {'write_only': True},
            'api_secret': {'write_only': True},
            'client_secret': {'write_only': True},
            'access_token': {'write_only': True},
            'refresh_token': {'write_only': True},
        }


# ============================================
# SERIALIZERS STRATEGIES
# ============================================

class StrategySerializer(serializers.ModelSerializer):
    """Serializer pour les stratégies."""
    all_asset_symbol = serializers.CharField(source='all_asset.symbol', read_only=True)
    all_asset_name = serializers.CharField(source='all_asset.name', read_only=True)
    
    class Meta:
        model = Strategy
        fields = [
            'id', 'name', 'description', 'all_asset', 'all_asset_symbol', 'all_asset_name',
            'risk_level', 'max_position_size', 'max_daily_loss', 'parameters',
            'is_active', 'is_automated', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'all_asset_symbol', 'all_asset_name']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Définir le queryset pour all_asset
        from apps.trading.models import AllAssets
        self.fields['all_asset'] = serializers.PrimaryKeyRelatedField(
            queryset=AllAssets.objects.all(),
            required=True
        )
    
    def validate_max_position_size(self, value):
        """Valider que la taille max est entre 0 et 100%."""
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError("La taille max doit être entre 0 et 100%")
        return value
    
    def validate_max_daily_loss(self, value):
        """Valider que la perte max est entre 0 et 100%."""
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError("La perte max doit être entre 0 et 100%")
        return value


class StrategyNestedSerializer(serializers.ModelSerializer):
    """Serializer léger pour Strategy (utilisé dans les relations)."""
    class Meta:
        model = Strategy
        fields = ['id', 'name', 'risk_level', 'is_active']


# ============================================
# SERIALIZERS TRADING
# ============================================

class PositionSerializer(serializers.ModelSerializer):
    """
    Serializer pour Position.
    
    Utilise AllAssets comme source de vérité principale.
    Asset est optionnel (pour enrichissement futur).
    """
    # Champs depuis AllAssets (source de vérité)
    all_asset = AllAssetsSerializer(read_only=True)
    all_asset_id = serializers.IntegerField(write_only=True, required=False)
    all_asset_symbol = serializers.CharField(source='all_asset.symbol', read_only=True)
    all_asset_name = serializers.CharField(source='all_asset.name', read_only=True)
    all_asset_platform = serializers.CharField(source='all_asset.platform', read_only=True)
    all_asset_yahoo_symbol = serializers.CharField(source='all_asset.symbole_yahoo', read_only=True)
    
    # Relations imbriquées (lecture) - Asset optionnel pour compatibilité
    asset = AssetNestedSerializer(read_only=True, allow_null=True)
    broker_name = serializers.CharField(source='broker.name', read_only=True)
    strategy = StrategyNestedSerializer(read_only=True, allow_null=True)
    
    # IDs pour création/modification
    asset_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    broker_id = serializers.IntegerField(write_only=True, required=False)
    strategy_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    # Champs calculés (propriétés du modèle)
    pnl = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    pnl_percent = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    # Champ symbol pour compatibilité (utilise all_asset en priorité)
    symbol = serializers.SerializerMethodField()
    
    class Meta:
        model = Position
        fields = [
            'id', 
            # Relations AllAssets (principal)
            'all_asset', 'all_asset_id', 'all_asset_symbol', 'all_asset_name', 
            'all_asset_platform', 'all_asset_yahoo_symbol',
            # Relations Asset (optionnel, compatibilité)
            'asset', 'asset_id',
            'broker_name', 'broker_id',
            'strategy', 'strategy_id',
            # Données
            'side', 'quantity', 'entry_price', 'current_price',
            'stop_loss', 'take_profit', 'is_open',
            'opened_at', 'closed_at',
            # Calculés
            'symbol', 'pnl', 'pnl_percent'
        ]
        read_only_fields = ['id', 'opened_at', 'pnl', 'pnl_percent']
    
    def get_symbol(self, obj):
        """Retourne le symbol depuis all_asset (ou asset en fallback)."""
        if obj.all_asset:
            return obj.all_asset.symbol
        elif obj.asset:
            return obj.asset.symbol
        return None
    
    def validate_quantity(self, value):
        """Valider que la quantité est positive."""
        if value <= 0:
            raise serializers.ValidationError("La quantité doit être positive")
        return value
    
    def validate_entry_price(self, value):
        """Valider que le prix d'entrée est positif."""
        if value <= 0:
            raise serializers.ValidationError("Le prix d'entrée doit être positif")
        return value


class TradeSerializer(serializers.ModelSerializer):
    """
    Serializer pour Trade.
    
    Utilise AllAssets comme source de vérité principale.
    Asset est optionnel (pour enrichissement futur).
    """
    # Champs depuis AllAssets (source de vérité)
    all_asset = AllAssetsSerializer(read_only=True)
    all_asset_id = serializers.IntegerField(write_only=True, required=False)
    all_asset_symbol = serializers.CharField(source='all_asset.symbol', read_only=True)
    all_asset_name = serializers.CharField(source='all_asset.name', read_only=True)
    all_asset_platform = serializers.CharField(source='all_asset.platform', read_only=True)
    all_asset_yahoo_symbol = serializers.CharField(source='all_asset.symbole_yahoo', read_only=True)
    
    # Relations imbriquées (lecture) - Asset optionnel pour compatibilité
    asset = AssetNestedSerializer(read_only=True, allow_null=True)
    broker_name = serializers.CharField(source='broker.name', read_only=True)
    
    # IDs pour création/modification
    asset_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    broker_id = serializers.IntegerField(write_only=True, required=False)
    
    # Champs calculés (propriétés du modèle)
    total_value = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    
    # Champ symbol pour compatibilité (utilise all_asset en priorité)
    symbol = serializers.SerializerMethodField()
    
    class Meta:
        model = Trade
        fields = [
            'id',
            # Relations AllAssets (principal)
            'all_asset', 'all_asset_id', 'all_asset_symbol', 'all_asset_name',
            'all_asset_platform', 'all_asset_yahoo_symbol',
            # Relations Asset (optionnel, compatibilité)
            'asset', 'asset_id',
            'broker_name', 'broker_id',
            'position',
            # Données
            'trade_type', 'quantity', 'price', 'fees',
            'executed_at', 'broker_trade_id',
            # Calculés
            'symbol', 'total_value'
        ]
        read_only_fields = ['id', 'total_value']
    
    def get_symbol(self, obj):
        """Retourne le symbol depuis all_asset (ou asset en fallback)."""
        if obj.all_asset:
            return obj.all_asset.symbol
        elif obj.asset:
            return obj.asset.symbol
        return None
    
    def validate_quantity(self, value):
        """Valider que la quantité est positive."""
        if value <= 0:
            raise serializers.ValidationError("La quantité doit être positive")
        return value
    
    def validate_price(self, value):
        """Valider que le prix est positif."""
        if value <= 0:
            raise serializers.ValidationError("Le prix doit être positif")
        return value


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer pour les ordres.
    
    Inclut les infos de l'asset et le statut.
    """
    # Relations imbriquées (lecture)
    asset = AssetNestedSerializer(read_only=True)
    broker_name = serializers.CharField(source='broker.name', read_only=True)
    
    # IDs pour création
    asset_id = serializers.IntegerField(write_only=True, required=False)
    broker_id = serializers.IntegerField(write_only=True, required=False)
    
    # Champs calculés
    fill_percentage = serializers.SerializerMethodField()
    total_value = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id',
            'asset', 'asset_id',
            'broker_name', 'broker_id',
            'order_type', 'side', 'status',
            'quantity', 'filled_quantity', 'fill_percentage',
            'price', 'stop_price',
            'broker_order_id', 'created_at', 'updated_at',
            'total_value'
        ]
        read_only_fields = ['id', 'filled_quantity', 'created_at', 'updated_at', 'total_value']
    
    def get_fill_percentage(self, obj):
        """Calcule le % de remplissage de l'ordre."""
        if obj.quantity and obj.quantity > 0:
            return round((obj.filled_quantity / obj.quantity) * 100, 2)
        return 0
    
    def get_total_value(self, obj):
        """Calcule la valeur totale de l'ordre (quantity × price)."""
        if obj.price and obj.quantity:
            return float(obj.quantity * obj.price)
        return 0.0
    
    def validate_quantity(self, value):
        """Valider que la quantité est positive."""
        if value <= 0:
            raise serializers.ValidationError("La quantité doit être positive")
        return value
    
    def validate(self, data):
        """Validations multi-champs."""
        order_type = data.get('order_type')
        price = data.get('price')
        stop_price = data.get('stop_price')
        
        # Limit orders nécessitent un prix
        if order_type == 'LIMIT' and not price:
            raise serializers.ValidationError({
                'price': "Un ordre LIMIT nécessite un prix"
            })
        
        # Stop orders nécessitent un stop_price
        if order_type in ['STOP', 'STOP_LIMIT'] and not stop_price:
            raise serializers.ValidationError({
                'stop_price': "Un ordre STOP nécessite un stop_price"
            })
        
        return data
