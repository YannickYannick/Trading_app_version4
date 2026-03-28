from django.contrib import admin
"""
Admin configuration for AI Assistant models.
"""
from apps.ai_assistant.models import AIAnalysis


@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    """Admin interface for AI analyses."""
    
    list_display = [
        'id',
        'user',
        'analysis_type',
        'status',
        'get_scope',
        'confidence_score',
        'is_daily_report',
        'created_at',
        'completed_at',
    ]
    
    list_filter = [
        'analysis_type',
        'status',
        'is_daily_report',
        'is_archived',
        'created_at',
    ]
    
    search_fields = [
        'user__username',
        'summary',
        'response',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'completed_at',
    ]
    
    fieldsets = (
        ('Métadonnées', {
            'fields': ('user', 'analysis_type', 'status', 'is_daily_report', 'is_archived')
        }),
        ('Relations', {
            'fields': ('strategy', 'all_asset')
        }),
        ('Analyse', {
            'fields': ('prompt', 'response', 'summary')
        }),
        ('Résultats', {
            'fields': ('recommendations', 'insights', 'risks', 'opportunities', 'confidence_score')
        }),
        ('Métadonnées techniques', {
            'fields': ('metadata', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_scope(self, obj):
        """Retourne le scope de l'analyse."""
        return obj.get_scope_description()
    get_scope.short_description = 'Scope'
    
    def has_add_permission(self, request):
        """Désactive la création manuelle depuis l'admin."""
        return False
