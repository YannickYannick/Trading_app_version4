from django.contrib import admin
from django.forms import Textarea
from django.utils.translation import gettext_lazy as _
from .models import (
    AllAssets, Asset, AssetPrice,
    Position, Trade, Order,
    Strategy, StrategyPerformance,
    Broker, BrokerAccount, BrokerSyncLog,
    ScheduledTask, TaskExecutionLog
)

# ============== ASSETS ==============

class YahooValidationFilter(admin.SimpleListFilter):
    """Filtre personnalisé pour les assets validés par Yahoo Finance."""
    title = _('Validation Yahoo')
    parameter_name = 'yahoo_validation'

    def lookups(self, request, model_admin):
        """Définit les options du filtre."""
        return (
            ('validated', _('✅ Validés')),
            ('not_searched', _('⏳ Non recherchés')),
            ('not_found', _('❌ Non trouvés')),
            ('manual', _('✋ Validation manuelle')),
        )

    def queryset(self, request, queryset):
        """Applique le filtre selon la sélection."""
        if self.value() == 'validated':
            # Assets validés : symbole_yahoo n'est pas 'Not_searched', 'not_found', ou 'manual'
            return queryset.exclude(
                symbole_yahoo__in=['Not_searched', 'not_found', 'manual']
            ).exclude(symbole_yahoo='')
        elif self.value() == 'not_searched':
            return queryset.filter(symbole_yahoo='Not_searched')
        elif self.value() == 'not_found':
            return queryset.filter(symbole_yahoo='not_found')
        elif self.value() == 'manual':
            return queryset.filter(symbole_yahoo='manual')
        return queryset


@admin.register(AllAssets)
class AllAssetsAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'name', 'platform', 'asset_type', 'market', 'currency', 'is_tradable', 'symbole_yahoo', 'last_updated']
    list_filter = ['platform', 'asset_type', 'market', 'is_tradable', 'currency', YahooValidationFilter]
    search_fields = ['symbol', 'name', 'saxo_uic', 'symbole_yahoo']
    ordering = ['symbol']
    readonly_fields = ['last_updated', 'created_at', 'yahoo_validated_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('symbol', 'name', 'platform', 'asset_type', 'market', 'currency', 'exchange', 'is_tradable')
        }),
        ('Yahoo Finance', {
            'fields': ('symbole_yahoo', 'yahoo_validation_method', 'yahoo_validated_at'),
            'classes': ('collapse',)
        }),
        ('Saxo Bank', {
            'fields': ('saxo_uic', 'saxo_exchange_id', 'saxo_country_code'),
            'classes': ('collapse',)
        }),
        ('Binance', {
            'fields': ('binance_base_asset', 'binance_quote_asset', 'binance_status'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'last_updated'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'name', 'asset_type', 'current_price', 'currency', 'is_active']
    list_filter = ['asset_type', 'currency', 'is_active']
    search_fields = ['symbol', 'name']
    ordering = ['symbol']


@admin.register(AssetPrice)
class AssetPriceAdmin(admin.ModelAdmin):
    list_display = ['asset', 'date', 'open_price', 'close_price', 'volume']
    list_filter = ['date', 'asset']
    search_fields = ['asset__symbol']
    ordering = ['-date']


# ============== TRADING ==============

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['asset', 'user', 'side', 'quantity', 'entry_price', 'current_price', 'is_open', 'opened_at']
    list_filter = ['side', 'is_open', 'broker']
    search_fields = ['asset__symbol', 'user__username']
    ordering = ['-opened_at']


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ['asset', 'user', 'trade_type', 'quantity', 'price', 'fees', 'executed_at']
    list_filter = ['trade_type', 'broker', 'executed_at']
    search_fields = ['asset__symbol', 'user__username']
    ordering = ['-executed_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['asset', 'user', 'order_type', 'side', 'status', 'quantity', 'price', 'created_at']
    list_filter = ['order_type', 'side', 'status', 'broker']
    search_fields = ['asset__symbol', 'user__username']
    ordering = ['-created_at']


# ============== STRATEGIES ==============

@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'risk_level', 'is_active', 'is_automated', 'created_at']
    list_filter = ['risk_level', 'is_active', 'is_automated']
    search_fields = ['name', 'user__username']
    ordering = ['name']


@admin.register(StrategyPerformance)
class StrategyPerformanceAdmin(admin.ModelAdmin):
    list_display = ['strategy', 'date', 'total_trades', 'winning_trades', 'net_pnl']
    list_filter = ['date', 'strategy']
    ordering = ['-date']


# ============== BROKERS ==============

@admin.register(Broker)
class BrokerAdmin(admin.ModelAdmin):
    list_display = ['name', 'broker_type', 'is_active', 'supports_stocks', 'supports_crypto']
    list_filter = ['broker_type', 'is_active']
    search_fields = ['name']


@admin.register(BrokerAccount)
class BrokerAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'broker', 'account_id', 'balance', 'currency', 'is_active', 'is_demo', 'environment']
    list_filter = ['broker', 'is_active', 'is_demo', 'environment']
    search_fields = ['user__username', 'account_id', 'name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('user', 'broker', 'name', 'broker_type', 'account_id', 'environment', 'is_active', 'is_demo', 'is_sandbox')
        }),
        ('Balance', {
            'fields': ('balance', 'currency', 'balance_updated_at', 'last_sync'),
        }),
        ('Credentials Saxo Bank', {
            'fields': (
                'saxo_client_id',
                'saxo_client_secret',
                'saxo_redirect_uri',
                'saxo_environment',
                'saxo_access_token',
                'saxo_refresh_token',
                'saxo_token_expires_at',
            ),
            'classes': ('collapse',)  # Collapsible par défaut pour la sécurité
        }),
        ('Credentials Binance', {
            'fields': (
                'binance_api_key',
                'binance_api_secret',
                'binance_testnet',
            ),
            'classes': ('collapse',)
        }),
        ('Auto-refresh (Saxo)', {
            'fields': ('auto_refresh_enabled', 'auto_refresh_frequency'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Permettre de voir les tokens complets en utilisant des widgets textarea
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Rendre les champs de tokens éditables avec des textarea plus grands
        if 'saxo_access_token' in form.base_fields:
            form.base_fields['saxo_access_token'].widget = Textarea(attrs={'rows': 5, 'cols': 100, 'style': 'font-family: monospace; font-size: 11px;'})
        if 'saxo_refresh_token' in form.base_fields:
            form.base_fields['saxo_refresh_token'].widget = Textarea(attrs={'rows': 5, 'cols': 100, 'style': 'font-family: monospace; font-size: 11px;'})
        if 'saxo_client_secret' in form.base_fields:
            form.base_fields['saxo_client_secret'].widget = Textarea(attrs={'rows': 3, 'cols': 100, 'style': 'font-family: monospace; font-size: 11px;'})
        return form


@admin.register(BrokerSyncLog)
class BrokerSyncLogAdmin(admin.ModelAdmin):
    list_display = ['broker_account', 'sync_type', 'status', 'items_synced', 'started_at']
    list_filter = ['sync_type', 'status', 'started_at']
    ordering = ['-started_at']


# ============== AUTOMATION ==============

@admin.register(ScheduledTask)
class ScheduledTaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'task_type', 'trigger_type', 'is_active', 'last_run_at', 'next_run_at']
    list_filter = ['task_type', 'trigger_type', 'is_active']
    search_fields = ['name']


@admin.register(TaskExecutionLog)
class TaskExecutionLogAdmin(admin.ModelAdmin):
    list_display = ['task', 'status', 'started_at', 'completed_at', 'duration_seconds']
    list_filter = ['status', 'started_at']
    ordering = ['-started_at']
