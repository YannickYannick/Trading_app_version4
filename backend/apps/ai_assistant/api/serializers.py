"""
Serializers pour les modèles AI Assistant.
"""
from rest_framework import serializers
from apps.ai_assistant.models import AIAnalysis
from apps.trading.api.serializers import StrategyNestedSerializer


class AIAnalysisSerializer(serializers.ModelSerializer):
    """Serializer complet pour AIAnalysis."""
    
    analysis_type_display = serializers.CharField(
        source='get_analysis_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    scope_description = serializers.CharField(
        source='get_scope_description',
        read_only=True
    )
    
    # Nested serializers
    strategy_detail = StrategyNestedSerializer(source='strategy', read_only=True)
    
    class Meta:
        model = AIAnalysis
        fields = [
            'id',
            'user',
            'analysis_type',
            'analysis_type_display',
            'status',
            'status_display',
            'scope_description',
            'strategy',
            'strategy_detail',
            'all_asset',
            'prompt',
            'response',
            'summary',
            'recommendations',
            'insights',
            'risks',
            'opportunities',
            'confidence_score',
            'metadata',
            'error_message',
            'is_daily_report',
            'is_archived',
            'created_at',
            'updated_at',
            'completed_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
            'completed_at',
        ]


class AIAnalysisListSerializer(serializers.ModelSerializer):
    """Serializer optimisé pour les listes d'analyses."""
    
    analysis_type_display = serializers.CharField(
        source='get_analysis_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    scope_description = serializers.CharField(
        source='get_scope_description',
        read_only=True
    )
    
    # Informations minimales de la stratégie
    strategy_name = serializers.CharField(
        source='strategy.name',
        read_only=True,
        allow_null=True
    )
    asset_symbol = serializers.SerializerMethodField()
    
    class Meta:
        model = AIAnalysis
        fields = [
            'id',
            'analysis_type',
            'analysis_type_display',
            'status',
            'status_display',
            'scope_description',
            'strategy',
            'strategy_name',
            'asset_symbol',
            'summary',
            'error_message',
            'confidence_score',
            'is_daily_report',
            'created_at',
            'completed_at',
        ]
    
    def get_asset_symbol(self, obj):
        """Retourne le symbole de l'actif."""
        if obj.all_asset:
            return obj.all_asset.symbol
        elif obj.strategy and obj.strategy.all_asset:
            return obj.strategy.all_asset.symbol
        return None


class AIAnalysisCreateSerializer(serializers.Serializer):
    """Serializer pour la création d'analyses (validation des requêtes)."""
    
    strategy_id = serializers.IntegerField(required=False, allow_null=True)
    asset_id = serializers.IntegerField(required=False, allow_null=True)
    force_new = serializers.BooleanField(
        default=False,
        help_text="Force la création d'une nouvelle analyse même si une récente existe"
    )
    
    def validate(self, data):
        """Valide que soit strategy_id soit asset_id est fourni (ou aucun pour portfolio)."""
        strategy_id = data.get('strategy_id')
        asset_id = data.get('asset_id')
        
        if strategy_id and asset_id:
            raise serializers.ValidationError(
                "Vous ne pouvez spécifier qu'une stratégie OU un actif, pas les deux."
            )
        
        return data


class AIAnalysisQuickSerializer(serializers.ModelSerializer):
    """Serializer ultra-léger pour les widgets."""
    
    scope_description = serializers.CharField(
        source='get_scope_description',
        read_only=True
    )
    
    class Meta:
        model = AIAnalysis
        fields = [
            'id',
            'analysis_type',
            'scope_description',
            'summary',
            'confidence_score',
            'created_at',
        ]
