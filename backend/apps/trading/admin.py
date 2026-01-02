from django.contrib import admin
from django.forms import Textarea
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Count, Min, Max
from .models import (
    AllAssets, Asset, AssetPrice, AllAssetPriceHistory,
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


class AllAssetPriceHistoryInline(admin.TabularInline):
    """
    Inline pour afficher l'historique complet des prix dans AllAssetsAdmin.
    Affiche TOUS les prix historiques dans un tableau, ordonnés du plus récent au plus ancien.
    """
    model = AllAssetPriceHistory
    extra = 0
    readonly_fields = ['date', 'open_price', 'high_price', 'low_price', 'close_price', 'volume', 'source']
    fields = ['date', 'open_price', 'high_price', 'low_price', 'close_price', 'volume', 'source']
    ordering = ['-date']  # Plus récent en premier
    can_delete = False
    can_add = False  # Empêcher l'ajout depuis l'inline (utiliser la commande de sync)
    show_change_link = False
    verbose_name = "Historique des prix"
    verbose_name_plural = "Historique complet des prix (toutes les dates)"
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False  # Lecture seule
    
    def get_queryset(self, request):
        """
        Retourner TOUS les prix historiques, sans limite.
        Ordonné du plus récent au plus ancien pour voir l'historique complet.
        """
        qs = super().get_queryset(request)
        # Pas de limite - afficher tous les enregistrements
        return qs.select_related('all_asset').order_by('-date')


@admin.register(AllAssets)
class AllAssetsAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'name', 'platform', 'asset_type', 'market', 'currency', 'is_tradable', 'symbole_yahoo', 'price_history_count', 'last_updated']
    list_filter = ['platform', 'asset_type', 'market', 'is_tradable', 'currency', YahooValidationFilter]
    search_fields = ['symbol', 'name', 'saxo_uic', 'symbole_yahoo']
    ordering = ['symbol']
    readonly_fields = ['last_updated', 'created_at', 'yahoo_validated_at', 'price_history_json_display', 'price_history_info']
    # inlines = [AllAssetPriceHistoryInline]  # Désactivé - utilise maintenant JSONB
    
    # Template personnalisé pour ajouter les boutons d'action
    change_form_template = 'admin/trading/allassets/change_form.html'
    
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
        ('Historique des prix (JSONB)', {
            'fields': ('price_history_info', 'price_history_json_display', 'price_history_updated_at', 'price_history_days'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'last_updated'),
            'classes': ('collapse',)
        }),
    )
    
    def price_history_count(self, obj):
        """Affiche le nombre de jours d'historique stockés dans JSONB."""
        if obj.has_price_history:
            days_count = obj.price_history_days or obj.get_price_history_count()
            dates = obj.get_price_history_dates()
            if dates:
                date_range = f" ({dates[-1]} → {dates[0]})" if len(dates) > 1 else f" ({dates[0]})"
                return format_html(
                    '<span style="color: green; font-weight: bold;">{} jours{}</span>',
                    days_count,
                    date_range
                )
            return format_html('<span style="color: green; font-weight: bold;">{} jours</span>', days_count)
        return mark_safe('<span style="color: gray;">Aucun</span>')
    price_history_count.short_description = 'Historique prix'
    
    def price_history_info(self, obj):
        """Affiche des informations sur l'historique des prix."""
        if not obj.has_price_history:
            return mark_safe('<span style="color: gray;">Aucun historique disponible</span>')
        
        days_count = obj.price_history_days or obj.get_price_history_count()
        dates = obj.get_price_history_dates()
        updated_at = obj.price_history_updated_at
        
        info_lines = [
            f"<strong>Nombre de jours:</strong> {days_count}",
        ]
        
        if dates:
            info_lines.append(f"<strong>Période:</strong> {dates[-1]} → {dates[0]}")
        
        if updated_at:
            info_lines.append(f"<strong>Dernière mise à jour:</strong> {updated_at.strftime('%d/%m/%Y %H:%M')}")
        
        return mark_safe('<br>'.join(info_lines))
    price_history_info.short_description = 'Informations'
    
    def price_history_json_display(self, obj):
        """Affiche l'historique des prix formaté (lecture seule)."""
        if not obj.has_price_history:
            return mark_safe('<span style="color: gray;">Aucun historique disponible</span>')
        
        import json
        history_json = obj.price_history_json or {}
        
        # Limiter l'affichage aux 50 premières dates pour ne pas surcharger l'admin
        sorted_dates = sorted(history_json.keys(), reverse=True)[:50]
        limited_history = {date: history_json[date] for date in sorted_dates}
        
        json_str = json.dumps(limited_history, indent=2, ensure_ascii=False)
        
        if len(sorted_dates) < len(history_json):
            warning = f"<p style='color: orange;'><strong>Note:</strong> Affichage des 50 dates les plus récentes sur {len(history_json)} au total.</p>"
        else:
            warning = ""
        
        return mark_safe(
            f'{warning}<textarea readonly rows="15" cols="100" style="font-family: monospace; font-size: 11px; width: 100%;">{json_str}</textarea>'
        )
    price_history_json_display.short_description = 'Historique des prix (JSON)'


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


@admin.register(AllAssetPriceHistory)
class AllAssetPriceHistoryAdmin(admin.ModelAdmin):
    list_display = ['all_asset', 'date', 'open_price', 'high_price', 'low_price', 'close_price', 'volume', 'source', 'created_at']
    list_filter = ['date', 'source', 'all_asset__platform', 'all_asset__asset_type']
    search_fields = ['all_asset__symbol', 'all_asset__name']
    ordering = ['-date']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 100  # Afficher plus de lignes par page
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('all_asset', 'date', 'source')
        }),
        ('Prix', {
            'fields': ('open_price', 'high_price', 'low_price', 'close_price', 'volume')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimiser les requêtes."""
        qs = super().get_queryset(request)
        return qs.select_related('all_asset')


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
