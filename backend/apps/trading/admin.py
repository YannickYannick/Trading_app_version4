from django.contrib import admin
from .models import (
    AllAssets, Asset, AssetPrice,
    Position, Trade, Order,
    Strategy, StrategyPerformance,
    Broker, BrokerAccount, BrokerSyncLog,
    ScheduledTask, TaskExecutionLog
)

# ============== ASSETS ==============

@admin.register(AllAssets)
class AllAssetsAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'name', 'platform', 'asset_type', 'market', 'currency', 'is_tradable', 'last_updated']
    list_filter = ['platform', 'asset_type', 'market', 'is_tradable', 'currency']
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
    list_display = ['user', 'broker', 'account_id', 'balance', 'currency', 'is_active', 'is_demo']
    list_filter = ['broker', 'is_active', 'is_demo']
    search_fields = ['user__username', 'account_id']


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
