"""
Serializers pour l'API REST Trading.

Un Serializer convertit automatiquement :
- Modèle Django → JSON (pour l'API)
- JSON → Modèle Django (pour créer/modifier)
"""
from rest_framework import serializers
from apps.trading.models import (
    AllAssets, Asset, AssetPrice, AllAssetPriceHistory, Position, Trade, Order,
    Strategy, StrategyPerformance, AlgorithmParameter, Broker, BrokerAccount,
    StrategyExecution
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
        # Perf: éviter de charger/itérer sur `price_history_json` (peut être volumineux)
        # sur les listes où AllAssets est imbriqué (positions/trades).
        if not (obj.price_history_days or obj.price_history_updated_at):
            return None
        return {
            'days_count': obj.price_history_days or 0,
            'updated_at': obj.price_history_updated_at.isoformat() if obj.price_history_updated_at else None,
            # Optionnel: coûteux à calculer si on doit inspecter un JSON volumineux.
            'date_range': None,
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
            'is_tracked', 'is_favorite', 'best_variant',
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

class AlgorithmParameterSerializer(serializers.ModelSerializer):
    """Serializer pour les paramètres d'algorithme."""
    
    class Meta:
        model = AlgorithmParameter
        fields = ['id', 'key', 'value', 'param_type', 'description']
        read_only_fields = ['id']
    
    def to_representation(self, instance):
        """Convertit la valeur selon le param_type pour l'API."""
        data = super().to_representation(instance)
        # La valeur est déjà convertie par get_value() si besoin
        # On peut aussi exposer la valeur convertie ici
        return data


class StrategySerializer(serializers.ModelSerializer):
    """Serializer pour les stratégies."""
    # Champs depuis all_asset
    all_asset_symbol = serializers.CharField(source='all_asset.symbol', read_only=True)
    all_asset_name = serializers.CharField(source='all_asset.name', read_only=True)
    all_asset_yahoo_symbol = serializers.CharField(source='all_asset.symbole_yahoo', read_only=True)
    
    # Champs depuis broker_account
    broker_account_id = serializers.PrimaryKeyRelatedField(
        source='broker_account',
        queryset=BrokerAccount.objects.all(),
        allow_null=True,
        required=False
    )
    broker_name = serializers.CharField(source='broker_account.name', read_only=True)
    
    # Champs depuis asset (Saxo)
    asset_id = serializers.PrimaryKeyRelatedField(
        source='asset',
        queryset=Asset.objects.all(),
        allow_null=True,
        required=False
    )
    asset_symbol = serializers.CharField(source='asset.symbol', read_only=True)
    
    # Aliases pour compatibilité frontend
    target_min_quantity = serializers.DecimalField(
        source='min_quantity',
        max_digits=20,
        decimal_places=10,
        required=False,
        allow_null=True
    )
    target_max_quantity = serializers.DecimalField(
        source='max_quantity',
        max_digits=20,
        decimal_places=10,
        required=False,
        allow_null=True
    )
    
    # Performance (calculés via SerializerMethodField)
    total_trades = serializers.SerializerMethodField()
    successful_trades = serializers.SerializerMethodField()
    total_pnl = serializers.SerializerMethodField()
    
    # Algorithm parameters
    algorithm_parameters = AlgorithmParameterSerializer(many=True, read_only=True)
    algorithm_parameters_data = AlgorithmParameterSerializer(many=True, write_only=True, required=False)
    
    class Meta:
        model = Strategy
        fields = [
            'id', 'name', 'description',
            # AllAssets
            'all_asset', 'all_asset_symbol', 'all_asset_name', 'all_asset_yahoo_symbol',
            # Assets Saxo (optionnel)
            'asset', 'asset_id', 'asset_symbol',
            # Broker
            'broker_account', 'broker_account_id', 'broker_name',
            # Configuration
            'algorithm_type', 'execution_mode', 'risk_level',
            # Quantités
            'min_quantity', 'max_quantity',
            'target_min_quantity', 'target_max_quantity',
            'budget', 'portfolio_quantity',
            # Fréquence
            'check_frequency',
            # Paramètres
            'parameters', 'algorithm_parameters', 'algorithm_parameters_data',
            # Performance
            'total_trades', 'successful_trades', 'total_pnl',
            # Statuts
            'is_active', 'is_automated',
            # Timestamps
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'all_asset_symbol', 'all_asset_name', 'all_asset_yahoo_symbol',
            'broker_name', 'asset_symbol',
            'total_trades', 'successful_trades', 'total_pnl',
            'algorithm_parameters'
        ]
    
    def get_total_trades(self, obj):
        """Calcule le nombre total de trades pour cette stratégie."""
        return Trade.objects.filter(strategy=obj).count()
    
    def get_successful_trades(self, obj):
        """Calcule le nombre de positions gagnantes (PnL > 0)."""
        # PnL est une propriété calculée, impossible de filtrer via l'ORM directement
        positions = Position.objects.filter(strategy=obj, is_open=False)
        return sum(1 for p in positions if p.pnl and p.pnl > 0)
    
    def get_total_pnl(self, obj):
        """Calcule le P&L total de toutes les positions fermées."""
        positions = Position.objects.filter(strategy=obj, is_open=False)
        return sum((p.pnl or 0) for p in positions)
    
    def update(self, instance, validated_data):
        """Mise à jour avec gestion des algorithm_parameters."""
        algorithm_parameters_data = validated_data.pop('algorithm_parameters_data', None)
        
        # Mise à jour standard
        instance = super().update(instance, validated_data)
        
        # Mettre à jour les algorithm_parameters si fournis
        if algorithm_parameters_data is not None:
            from apps.trading.models import AlgorithmParameter
            
            # Supprimer les anciens paramètres
            AlgorithmParameter.objects.filter(strategy=instance).delete()
            
            # Créer les nouveaux paramètres
            for param_data in algorithm_parameters_data:
                AlgorithmParameter.objects.create(
                    strategy=instance,
                    key=param_data['key'],
                    value=param_data['value'],
                    param_type=param_data['param_type'],
                    description=param_data.get('description', '')
                )
        
        return instance
    
    def create(self, validated_data):
        """Création avec gestion des algorithm_parameters."""
        algorithm_parameters_data = validated_data.pop('algorithm_parameters_data', None)
        
        # Création standard
        instance = super().create(validated_data)
        
        # Créer les algorithm_parameters si fournis
        if algorithm_parameters_data:
            from apps.trading.models import AlgorithmParameter
            
            for param_data in algorithm_parameters_data:
                AlgorithmParameter.objects.create(
                    strategy=instance,
                    key=param_data['key'],
                    value=param_data['value'],
                    param_type=param_data['param_type'],
                    description=param_data.get('description', '')
                )
        
        return instance
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Définir le queryset pour all_asset
        from apps.trading.models import AllAssets
        # Rendre all_asset optionnel pour permettre la création sans asset
        request = kwargs.get('context', {}).get('request')
        is_create = request and request.method == 'POST'
        
        self.fields['all_asset'] = serializers.PrimaryKeyRelatedField(
            queryset=AllAssets.objects.all(),
            required=False,  # Optionnel pour permettre création sans asset
            allow_null=True
        )
    



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
    # Champs calculés (propriétés du modèle ou calculé temps réel)
    pnl = serializers.SerializerMethodField()
    pnl_percent = serializers.SerializerMethodField()
    
    # Champ symbol pour compatibilité (utilise all_asset en priorité)
    symbol = serializers.SerializerMethodField()
    
    # Prix actuel calculé depuis Yahoo Finance
    yahoo_current_price = serializers.SerializerMethodField()
    
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
            'side', 'quantity', 'entry_price', 'current_price', 'yahoo_current_price',
            'stop_loss', 'take_profit', 'is_open',
            'opened_at', 'closed_at',
            # Calculés
            'symbol', 'pnl', 'pnl_percent'
        ]
        read_only_fields = ['id', 'opened_at', 'pnl', 'pnl_percent', 'yahoo_current_price']
    
    def get_symbol(self, obj):
        """Retourne le symbol depuis all_asset (ou asset en fallback)."""
        if obj.all_asset:
            return obj.all_asset.symbol
        elif obj.asset:
            return obj.asset.symbol
        return None
    
    def get_yahoo_current_price(self, obj):
        """
        Récupère le prix actuel depuis Yahoo Finance pour l'AllAsset.
        Retourne None si pas disponible.
        """
        if not self.context.get('include_yahoo_price'):
            return None
        if not obj.all_asset or not obj.all_asset.symbole_yahoo:
            return None
        
        if obj.all_asset.symbole_yahoo in ['Not_searched', 'not_found', 'manual']:
            return None
        
        try:
            from ..services.data_providers.yahoo_finance import YahooFinanceService
            yahoo_service = YahooFinanceService()
            price = yahoo_service.get_current_price(obj.all_asset.symbole_yahoo)
            
            if price is not None:
                return float(price)
            return None
        except Exception:
            # En cas d'erreur, retourner None silencieusement
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

    def get_pnl(self, obj):
        """Calcule le PnL avec le prix actuel (Yahoo ou DB)."""
        current_price = self.get_yahoo_current_price(obj)
        if current_price is None and obj.current_price:
            current_price = float(obj.current_price)
            
        if current_price is None or not obj.entry_price:
            return None
            
        entry_price = float(obj.entry_price)
        quantity = float(obj.quantity)
        
        if obj.side == 'LONG':
            return (current_price - entry_price) * quantity
        else:
            return (entry_price - current_price) * quantity

    def get_pnl_percent(self, obj):
        """Calcule le % PnL avec le prix actuel (Yahoo ou DB)."""
        current_price = self.get_yahoo_current_price(obj)
        if current_price is None and obj.current_price:
            current_price = float(obj.current_price)
            
        if current_price is None or not obj.entry_price:
            return None
            
        entry_price = float(obj.entry_price)
        if entry_price == 0:
            return 0.0
            
        if obj.side == 'LONG':
            return ((current_price - entry_price) / entry_price) * 100
        else:
            return ((entry_price - current_price) / entry_price) * 100


class PositionListSerializer(serializers.ModelSerializer):
    """
    Serializer "léger" pour les listes (perf).
    Évite l'objet `all_asset` imbriqué (très verbeux) et la plupart des relations.
    """
    all_asset_id = serializers.IntegerField(source='all_asset.id', read_only=True)
    all_asset_symbol = serializers.CharField(source='all_asset.symbol', read_only=True)
    all_asset_yahoo_symbol = serializers.CharField(source='all_asset.symbole_yahoo', read_only=True)

    # Compat: le frontend utilise `status` / `size`
    status = serializers.SerializerMethodField()
    size = serializers.DecimalField(source='quantity', max_digits=20, decimal_places=8, read_only=True)

    pnl = serializers.SerializerMethodField()
    pnl_percent = serializers.SerializerMethodField()

    class Meta:
        model = Position
        fields = [
            'id',
            'all_asset_id', 'all_asset_symbol', 'all_asset_yahoo_symbol',
            'side', 'quantity', 'size', 'entry_price', 'current_price',
            'opened_at', 'closed_at',
            'status',
            'pnl', 'pnl_percent',
        ]

    def get_status(self, obj):
        return 'OPEN' if getattr(obj, 'is_open', False) else 'CLOSED'

    def get_pnl(self, obj):
        # Utilise le prix DB (pas Yahoo) pour rester rapide.
        if obj.current_price is None or not obj.entry_price:
            return None
        current_price = float(obj.current_price)
        entry_price = float(obj.entry_price)
        quantity = float(obj.quantity)
        if obj.side == 'LONG':
            return (current_price - entry_price) * quantity
        return (entry_price - current_price) * quantity

    def get_pnl_percent(self, obj):
        if obj.current_price is None or not obj.entry_price:
            return None
        entry_price = float(obj.entry_price)
        if entry_price == 0:
            return 0.0
        current_price = float(obj.current_price)
        if obj.side == 'LONG':
            return ((current_price - entry_price) / entry_price) * 100
        return ((entry_price - current_price) / entry_price) * 100
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
    
    # Prix actuel calculé depuis Yahoo Finance
    yahoo_current_price = serializers.SerializerMethodField()
    
    # Champ symbol pour compatibilité (utilise all_asset en priorité)
    symbol = serializers.SerializerMethodField()
    
    # Champ side pour compatibilité frontend (mappe trade_type)
    side = serializers.CharField(source='trade_type', read_only=True)
    
    # Champ timestamp pour compatibilité frontend (mappe executed_at)
    timestamp = serializers.DateTimeField(source='executed_at', read_only=True)
    
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
            'trade_type', 'side', 'quantity', 'price', 'fees',  # side ajouté pour compatibilité
            'executed_at', 'timestamp', 'broker_trade_id',  # timestamp ajouté pour compatibilité
            # Calculés
            'symbol', 'total_value', 'yahoo_current_price'
        ]
        read_only_fields = ['id', 'total_value', 'side', 'timestamp', 'yahoo_current_price']
    
    def get_symbol(self, obj):
        """Retourne le symbol depuis all_asset (ou asset en fallback)."""
        if obj.all_asset:
            return obj.all_asset.symbol
        elif obj.asset:
            return obj.asset.symbol
        return None

    def get_yahoo_current_price(self, obj):
        """
        Récupère le prix actuel depuis Yahoo Finance pour l'AllAsset.
        Retourne None si pas disponible.

        Désactivé par défaut (évite N appels Yahoo sur les listes).
        Activer : GET .../trades/?include_yahoo_price=1
        """
        if not self.context.get('include_yahoo_price'):
            return None
        if not obj.all_asset or not obj.all_asset.symbole_yahoo:
            return None
        
        if obj.all_asset.symbole_yahoo in ['Not_searched', 'not_found', 'manual']:
            return None
        
        try:
            from ..services.data_providers.yahoo_finance import YahooFinanceService
            yahoo_service = YahooFinanceService()
            price = yahoo_service.get_current_price(obj.all_asset.symbole_yahoo)
            
            if price is not None:
                return float(price)
            return None
        except Exception:
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


class TradeListSerializer(serializers.ModelSerializer):
    """
    Serializer "léger" pour les listes (perf).
    Évite l'objet `all_asset` imbriqué (très verbeux) et les champs inutiles.
    """
    all_asset_id = serializers.IntegerField(source='all_asset.id', read_only=True)
    all_asset_symbol = serializers.CharField(source='all_asset.symbol', read_only=True)
    all_asset_yahoo_symbol = serializers.CharField(source='all_asset.symbole_yahoo', read_only=True)

    # Compat frontend
    side = serializers.CharField(source='trade_type', read_only=True)
    timestamp = serializers.DateTimeField(source='executed_at', read_only=True)
    size = serializers.DecimalField(source='quantity', max_digits=20, decimal_places=8, read_only=True)

    class Meta:
        model = Trade
        fields = [
            'id',
            'all_asset_id', 'all_asset_symbol', 'all_asset_yahoo_symbol',
            'trade_type', 'side',
            'quantity', 'size',
            'price', 'fees',
            'executed_at', 'timestamp',
            'broker_trade_id',
        ]


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer pour les ordres.
    
    Utilise AllAssets comme source de vérité principale.
    Asset est optionnel (pour compatibilité et enrichissement futur).
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
    
    # Champs calculés
    fill_percentage = serializers.SerializerMethodField()
    total_value = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id',
            'all_asset', 'all_asset_id', 'all_asset_symbol', 'all_asset_name', 
            'all_asset_platform', 'all_asset_yahoo_symbol',
            'asset', 'asset_id',
            'broker_name', 'broker_id',
            'order_type', 'side', 'status',
            'quantity', 'filled_quantity', 'fill_percentage',
            'price', 'stop_price',
            'broker_order_id', 'created_at', 'updated_at',
            'total_value'
        ]
        read_only_fields = ['id', 'filled_quantity', 'created_at', 'updated_at', 'total_value', 
                           'all_asset_symbol', 'all_asset_name', 'all_asset_platform', 'all_asset_yahoo_symbol']
    
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


class StrategyExecutionSerializer(serializers.ModelSerializer):
    """Serializer pour les logs d'exécution de stratégies."""
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    strategy_id = serializers.IntegerField(source='strategy.id', read_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = StrategyExecution
        fields = [
            'id', 'strategy', 'strategy_id', 'strategy_name',
            'started_at', 'completed_at', 'duration', 'status',
            'signal', 'signal_price', 'signal_quantity',
            'output', 'error'
        ]
        read_only_fields = ['id', 'started_at']
    
    def get_duration(self, obj):
        """Calcule la durée d'exécution en secondes."""
        if obj.completed_at and obj.started_at:
            delta = obj.completed_at - obj.started_at
            return round(delta.total_seconds(), 2)
        return None
