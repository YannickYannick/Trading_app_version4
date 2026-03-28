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
    AlgorithmParameter, AlgorithmSchema, AlgorithmParameterDefinition,
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
    list_display = ['symbol', 'name', 'asset_type', 'current_price', 'currency', 'is_active', 'is_tracked', 'is_favorite']
    list_filter = ['is_tracked', 'is_favorite', 'asset_type', 'currency', 'is_active']
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
    list_display = ['all_asset_symbol', 'all_asset_name', 'all_asset_yahoo_symbol', 'user', 'side', 'quantity', 'entry_price', 'current_price', 'is_open', 'opened_at']
    list_filter = ['side', 'is_open', 'broker']
    search_fields = ['all_asset__symbol', 'all_asset__name', 'all_asset__symbole_yahoo', 'user__username']
    ordering = ['-opened_at']
    change_form_template = 'admin/trading/position/change_form.html'
    actions = ['validate_yahoo_bulk', 'sync_history_bulk']
    
    def all_asset_symbol(self, obj):
        """Affiche le symbole de l'AllAsset."""
        return obj.all_asset.symbol if obj.all_asset else '-'
    all_asset_symbol.short_description = 'Symbole'
    
    def all_asset_name(self, obj):
        """Affiche le nom de l'AllAsset."""
        return obj.all_asset.name if obj.all_asset else '-'
    all_asset_name.short_description = 'Nom'
    
    def all_asset_yahoo_symbol(self, obj):
        """Affiche le symbole Yahoo de l'AllAsset."""
        return obj.all_asset.symbole_yahoo if obj.all_asset and obj.all_asset.symbole_yahoo else '-'
    all_asset_yahoo_symbol.short_description = 'Symbole Yahoo'
    
    def validate_yahoo_bulk(self, request, queryset):
        """Action en lot : Valider les symboles Yahoo pour les AllAssets uniques."""
        from apps.trading.services.yahoo_validator import validate_single_asset
        from apps.trading.utils.yahoo_config import ValidationStatus
        from apps.trading.constants import DEFAULT_PRICE_TOLERANCE_PERCENT
        from apps.trading.services.broker_service import BrokerService
        from apps.trading.models import BrokerAccount
        from django.utils import timezone
        from django.contrib import messages
        import logging
        
        logger = logging.getLogger('trading.admin')
        all_assets = set()
        
        # Collecter les AllAssets uniques
        for position in queryset:
            if position.all_asset:
                all_assets.add(position.all_asset)
        
        if not all_assets:
            self.message_user(request, "Aucun AllAsset trouvé dans les positions sélectionnées.", messages.WARNING)
            return
        
        success_count = 0
        error_count = 0
        
        for all_asset in all_assets:
            try:
                broker_config = {}
                if all_asset.platform == 'SAXO':
                    saxo_account = BrokerAccount.objects.filter(
                        broker_type='SAXO',
                        user=request.user,
                        is_active=True
                    ).first()
                    if saxo_account:
                        try:
                            broker_service = BrokerService(request.user)
                            broker = broker_service.get_broker_instance(saxo_account, use_cache=True)
                            if broker.authenticate():
                                broker_config['access_token'] = broker.access_token
                                broker_config['base_url'] = broker.base_url
                        except Exception as e:
                            logger.warning(f"Could not get valid Saxo token for {all_asset.symbol}: {e}")
                
                result = validate_single_asset(
                    all_asset,
                    broker_config=broker_config,
                    tolerance_percent=DEFAULT_PRICE_TOLERANCE_PERCENT
                )
                
                # Sauvegarder le résultat si validé
                status_str = str(result.status) if result.status else ''
                is_validated = (
                    status_str == ValidationStatus.VALIDATED_Y4 or
                    status_str == ValidationStatus.VALIDATED_Y3 or
                    status_str == ValidationStatus.VALIDATED_Y0
                )
                if is_validated:
                    all_asset.symbole_yahoo = result.yahoo_symbol
                    all_asset.yahoo_validation_method = result.method
                    all_asset.yahoo_validated_at = timezone.now()
                    all_asset.save(update_fields=[
                        'symbole_yahoo',
                        'yahoo_validation_method',
                        'yahoo_validated_at'
                    ])
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                logger.error(f"Erreur lors de la validation Yahoo pour {all_asset.symbol}: {e}")
                error_count += 1
        
        self.message_user(
            request,
            f"Validation Yahoo terminée : {success_count} réussie(s), {error_count} erreur(s) sur {len(all_assets)} AllAsset(s) unique(s).",
            messages.SUCCESS if error_count == 0 else messages.WARNING
        )
    validate_yahoo_bulk.short_description = "🔍 Valider les symboles Yahoo des AllAssets sélectionnés"
    
    def sync_history_bulk(self, request, queryset):
        """Action en lot : Synchroniser l'historique des prix pour les AllAssets uniques."""
        from apps.trading.services.sync.all_asset_price_sync_service import AllAssetPriceSyncService
        from django.contrib import messages
        import logging
        
        logger = logging.getLogger('trading.admin')
        sync_service = AllAssetPriceSyncService()
        all_assets = set()
        
        # Collecter les AllAssets uniques
        for position in queryset:
            if position.all_asset:
                all_assets.add(position.all_asset)
        
        if not all_assets:
            self.message_user(request, "Aucun AllAsset trouvé dans les positions sélectionnées.", messages.WARNING)
            return
        
        success_count = 0
        error_count = 0
        total_records = 0
        
        for all_asset in all_assets:
            try:
                result = sync_service.sync_from_yahoo_finance(all_asset, days=365, interval='1d')
                if result.get('success'):
                    success_count += 1
                    total_records += result.get('records', 0)
                else:
                    error_count += 1
            except Exception as e:
                logger.error(f"Erreur lors de la synchronisation pour {all_asset.symbol}: {e}")
                error_count += 1
        
        self.message_user(
            request,
            f"Synchronisation terminée : {success_count} réussie(s), {error_count} erreur(s), {total_records} enregistrements sur {len(all_assets)} AllAsset(s) unique(s).",
            messages.SUCCESS if error_count == 0 else messages.WARNING
        )
    sync_history_bulk.short_description = "📊 Synchroniser l'historique des prix des AllAssets sélectionnés"


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ['all_asset_symbol', 'all_asset_name', 'all_asset_yahoo_symbol', 'user', 'trade_type', 'quantity', 'price', 'fees', 'executed_at']
    list_filter = ['trade_type', 'broker', 'executed_at']
    search_fields = ['all_asset__symbol', 'all_asset__name', 'all_asset__symbole_yahoo', 'user__username']
    ordering = ['-executed_at']
    change_form_template = 'admin/trading/trade/change_form.html'
    actions = ['validate_yahoo_bulk', 'sync_history_bulk']
    
    def all_asset_symbol(self, obj):
        """Affiche le symbole de l'AllAsset."""
        return obj.all_asset.symbol if obj.all_asset else '-'
    all_asset_symbol.short_description = 'Symbole'
    
    def all_asset_name(self, obj):
        """Affiche le nom de l'AllAsset."""
        return obj.all_asset.name if obj.all_asset else '-'
    all_asset_name.short_description = 'Nom'
    
    def all_asset_yahoo_symbol(self, obj):
        """Affiche le symbole Yahoo de l'AllAsset."""
        return obj.all_asset.symbole_yahoo if obj.all_asset and obj.all_asset.symbole_yahoo else '-'
    all_asset_yahoo_symbol.short_description = 'Symbole Yahoo'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['all_asset_symbol', 'all_asset_name', 'all_asset_yahoo_symbol', 'user', 'order_type', 'side', 'status', 'quantity', 'price', 'created_at']
    list_filter = ['order_type', 'side', 'status', 'broker']
    search_fields = ['all_asset__symbol', 'all_asset__name', 'all_asset__symbole_yahoo', 'user__username']
    ordering = ['-created_at']
    autocomplete_fields = ['all_asset']
    change_form_template = 'admin/trading/order/change_form.html'
    actions = ['validate_yahoo_bulk', 'sync_history_bulk']
    
    def all_asset_symbol(self, obj):
        """Affiche le symbole de l'AllAsset."""
        return obj.all_asset.symbol if obj.all_asset else '-'
    all_asset_symbol.short_description = 'Symbole'
    
    def all_asset_name(self, obj):
        """Affiche le nom de l'AllAsset."""
        return obj.all_asset.name if obj.all_asset else '-'
    all_asset_name.short_description = 'Nom'
    
    def all_asset_yahoo_symbol(self, obj):
        """Affiche le symbole Yahoo de l'AllAsset."""
        return obj.all_asset.symbole_yahoo if obj.all_asset and obj.all_asset.symbole_yahoo else '-'
    all_asset_yahoo_symbol.short_description = 'Symbole Yahoo'
    
    def validate_yahoo_bulk(self, request, queryset):
        """Action en lot : Valider les symboles Yahoo pour les AllAssets uniques."""
        from apps.trading.services.yahoo_validator import validate_single_asset
        from apps.trading.utils.yahoo_config import ValidationStatus
        from apps.trading.constants import DEFAULT_PRICE_TOLERANCE_PERCENT
        from apps.trading.services.broker_service import BrokerService
        from apps.trading.models import BrokerAccount
        from django.utils import timezone
        from django.contrib import messages
        import logging
        
        logger = logging.getLogger('trading.admin')
        all_assets = set()
        
        # Collecter les AllAssets uniques
        for order in queryset:
            if order.all_asset:
                all_assets.add(order.all_asset)
        
        if not all_assets:
            self.message_user(request, "Aucun AllAsset trouvé dans les ordres sélectionnés.", messages.WARNING)
            return
        
        success_count = 0
        error_count = 0
        
        for all_asset in all_assets:
            try:
                broker_config = {}
                if all_asset.platform == 'SAXO':
                    saxo_account = BrokerAccount.objects.filter(
                        broker_type='SAXO',
                        user=request.user,
                        is_active=True
                    ).first()
                    if saxo_account:
                        try:
                            broker_service = BrokerService(request.user)
                            broker = broker_service.get_broker_instance(saxo_account, use_cache=True)
                            if broker.authenticate():
                                broker_config['access_token'] = broker.access_token
                                broker_config['base_url'] = broker.base_url
                        except Exception as e:
                            logger.warning(f"Could not get valid Saxo token for {all_asset.symbol}: {e}")
                
                result = validate_single_asset(
                    all_asset,
                    broker_config=broker_config,
                    tolerance_percent=DEFAULT_PRICE_TOLERANCE_PERCENT
                )
                
                # Sauvegarder le résultat si validé
                status_str = str(result.status) if result.status else ''
                is_validated = (
                    status_str == ValidationStatus.VALIDATED_Y4 or
                    status_str == ValidationStatus.VALIDATED_Y3 or
                    status_str == ValidationStatus.VALIDATED_Y0
                )
                if is_validated:
                    all_asset.symbole_yahoo = result.yahoo_symbol
                    all_asset.yahoo_validation_method = result.method
                    all_asset.yahoo_validated_at = timezone.now()
                    all_asset.save(update_fields=[
                        'symbole_yahoo',
                        'yahoo_validation_method',
                        'yahoo_validated_at'
                    ])
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                logger.error(f"Erreur lors de la validation Yahoo pour {all_asset.symbol}: {e}")
                error_count += 1
        
        self.message_user(
            request,
            f"Validation Yahoo terminée : {success_count} réussie(s), {error_count} erreur(s) sur {len(all_assets)} AllAsset(s) unique(s).",
            messages.SUCCESS if error_count == 0 else messages.WARNING
        )
    validate_yahoo_bulk.short_description = "🔍 Valider les symboles Yahoo des AllAssets sélectionnés"
    
    def sync_history_bulk(self, request, queryset):
        """Action en lot : Synchroniser l'historique des prix pour les AllAssets uniques."""
        from apps.trading.services.sync.all_asset_price_sync_service import AllAssetPriceSyncService
        from django.contrib import messages
        import logging
        
        logger = logging.getLogger('trading.admin')
        sync_service = AllAssetPriceSyncService()
        all_assets = set()
        
        # Collecter les AllAssets uniques
        for order in queryset:
            if order.all_asset:
                all_assets.add(order.all_asset)
        
        if not all_assets:
            self.message_user(request, "Aucun AllAsset trouvé dans les ordres sélectionnés.", messages.WARNING)
            return
        
        success_count = 0
        error_count = 0
        total_records = 0
        
        for all_asset in all_assets:
            try:
                result = sync_service.sync_from_yahoo_finance(all_asset, days=365, interval='1d')
                if result.get('success'):
                    success_count += 1
                    total_records += result.get('records', 0)
                else:
                    error_count += 1
            except Exception as e:
                logger.error(f"Erreur lors de la synchronisation pour {all_asset.symbol}: {e}")
                error_count += 1
        
        self.message_user(
            request,
            f"Synchronisation terminée : {success_count} réussie(s), {error_count} erreur(s), {total_records} enregistrements sur {len(all_assets)} AllAsset(s) unique(s).",
            messages.SUCCESS if error_count == 0 else messages.WARNING
        )
    sync_history_bulk.short_description = "📊 Synchroniser l'historique des prix des AllAssets sélectionnés"


# ============== STRATEGIES ==============

class AlgorithmParameterInline(admin.TabularInline):
    """Inline pour les paramètres d'algorithme."""
    model = AlgorithmParameter
    extra = 0
    fields = ('key', 'value', 'param_type', 'description')
    verbose_name = 'Paramètre d\'algorithme'
    verbose_name_plural = 'Paramètres d\'algorithme'


class AlgorithmParameterDefinitionInline(admin.TabularInline):
    """Inline pour les définitions de paramètres."""
    model = AlgorithmParameterDefinition
    extra = 0
    fields = ('key', 'param_type', 'default_value', 'required', 'description', 'min_value', 'max_value')
    verbose_name = 'Définition de paramètre'
    verbose_name_plural = 'Définitions de paramètres'


@admin.register(AlgorithmSchema)
class AlgorithmSchemaAdmin(admin.ModelAdmin):
    """Admin pour les schémas d'algorithmes."""
    list_display = ['algorithm_type', 'name']
    search_fields = ['algorithm_type', 'name', 'description']
    ordering = ['algorithm_type']
    inlines = [AlgorithmParameterDefinitionInline]


@admin.register(AlgorithmParameter)
class AlgorithmParameterAdmin(admin.ModelAdmin):
    """Admin pour les paramètres d'algorithme."""
    list_display = ['strategy', 'key', 'value', 'param_type']
    list_filter = ['param_type', 'strategy']
    search_fields = ['strategy__name', 'key', 'description']
    ordering = ['strategy', 'key']


@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'all_asset_symbol', 'all_asset_name', 'all_asset_yahoo_symbol', 'algorithm_type', 'risk_level', 'is_active', 'is_automated', 'created_at']
    list_filter = ['risk_level', 'algorithm_type', 'is_active', 'is_automated', 'all_asset__platform']
    search_fields = ['name', 'user__username', 'all_asset__symbol', 'all_asset__name', 'all_asset__symbole_yahoo']
    ordering = ['name']
    autocomplete_fields = ['all_asset']
    change_form_template = 'admin/trading/strategy/change_form.html'
    actions = ['validate_yahoo_bulk', 'sync_history_bulk']
    inlines = [AlgorithmParameterInline]
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'user', 'all_asset', 'description')
        }),
        ('Algorithme', {
            'fields': ('algorithm_type',)
        }),
        ('Configuration', {
            'fields': ('risk_level', 'parameters')
        }),
        ('Statut', {
            'fields': ('is_active', 'is_automated')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    
    def all_asset_symbol(self, obj):
        """Affiche le symbole de l'AllAsset."""
        return obj.all_asset.symbol if obj.all_asset else '-'
    all_asset_symbol.short_description = 'Symbole'
    
    def all_asset_name(self, obj):
        """Affiche le nom de l'AllAsset."""
        return obj.all_asset.name if obj.all_asset else '-'
    all_asset_name.short_description = 'Nom'
    
    def all_asset_yahoo_symbol(self, obj):
        """Affiche le symbole Yahoo de l'AllAsset."""
        return obj.all_asset.symbole_yahoo if obj.all_asset and obj.all_asset.symbole_yahoo else '-'
    all_asset_yahoo_symbol.short_description = 'Symbole Yahoo'
    
    def validate_yahoo_bulk(self, request, queryset):
        """Action en lot : Valider les symboles Yahoo pour les AllAssets uniques."""
        from apps.trading.services.yahoo_validator import validate_single_asset
        from apps.trading.utils.yahoo_config import ValidationStatus
        from apps.trading.constants import DEFAULT_PRICE_TOLERANCE_PERCENT
        from apps.trading.services.broker_service import BrokerService
        from apps.trading.models import BrokerAccount
        from django.utils import timezone
        from django.contrib import messages
        import logging
        
        logger = logging.getLogger('trading.admin')
        all_assets = set()
        
        # Collecter les AllAssets uniques
        for strategy in queryset:
            if strategy.all_asset:
                all_assets.add(strategy.all_asset)
        
        if not all_assets:
            self.message_user(request, "Aucun AllAsset trouvé dans les stratégies sélectionnées.", messages.WARNING)
            return
        
        success_count = 0
        error_count = 0
        
        for all_asset in all_assets:
            try:
                broker_config = {}
                if all_asset.platform == 'SAXO':
                    saxo_account = BrokerAccount.objects.filter(
                        broker_type='SAXO',
                        user=request.user,
                        is_active=True
                    ).first()
                    if saxo_account:
                        try:
                            broker_service = BrokerService(request.user)
                            broker = broker_service.get_broker_instance(saxo_account, use_cache=True)
                            if broker.authenticate():
                                broker_config['access_token'] = broker.access_token
                                broker_config['base_url'] = broker.base_url
                        except Exception as e:
                            logger.warning(f"Could not get valid Saxo token for {all_asset.symbol}: {e}")
                
                result = validate_single_asset(
                    all_asset,
                    broker_config=broker_config,
                    tolerance_percent=DEFAULT_PRICE_TOLERANCE_PERCENT
                )
                
                # Sauvegarder le résultat si validé
                status_str = str(result.status) if result.status else ''
                is_validated = (
                    status_str == ValidationStatus.VALIDATED_Y4 or
                    status_str == ValidationStatus.VALIDATED_Y3 or
                    status_str == ValidationStatus.VALIDATED_Y0
                )
                if is_validated:
                    all_asset.symbole_yahoo = result.yahoo_symbol
                    all_asset.yahoo_validation_method = result.method
                    all_asset.yahoo_validated_at = timezone.now()
                    all_asset.save(update_fields=[
                        'symbole_yahoo',
                        'yahoo_validation_method',
                        'yahoo_validated_at'
                    ])
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                logger.error(f"Erreur lors de la validation Yahoo pour {all_asset.symbol}: {e}")
                error_count += 1
        
        self.message_user(
            request,
            f"Validation Yahoo terminée : {success_count} réussie(s), {error_count} erreur(s) sur {len(all_assets)} AllAsset(s) unique(s).",
            messages.SUCCESS if error_count == 0 else messages.WARNING
        )
    validate_yahoo_bulk.short_description = "🔍 Valider les symboles Yahoo des AllAssets sélectionnés"
    
    def sync_history_bulk(self, request, queryset):
        """Action en lot : Synchroniser l'historique des prix pour les AllAssets uniques."""
        from apps.trading.services.sync.all_asset_price_sync_service import AllAssetPriceSyncService
        from django.contrib import messages
        import logging
        
        logger = logging.getLogger('trading.admin')
        sync_service = AllAssetPriceSyncService()
        all_assets = set()
        
        # Collecter les AllAssets uniques
        for strategy in queryset:
            if strategy.all_asset:
                all_assets.add(strategy.all_asset)
        
        if not all_assets:
            self.message_user(request, "Aucun AllAsset trouvé dans les stratégies sélectionnées.", messages.WARNING)
            return
        
        success_count = 0
        error_count = 0
        total_records = 0
        
        for all_asset in all_assets:
            try:
                result = sync_service.sync_from_yahoo_finance(all_asset, days=365, interval='1d')
                if result.get('success'):
                    success_count += 1
                    total_records += result.get('records', 0)
                else:
                    error_count += 1
            except Exception as e:
                logger.error(f"Erreur lors de la synchronisation pour {all_asset.symbol}: {e}")
                error_count += 1
        
        self.message_user(
            request,
            f"Synchronisation terminée : {success_count} réussie(s), {error_count} erreur(s), {total_records} enregistrements sur {len(all_assets)} AllAsset(s) unique(s).",
            messages.SUCCESS if error_count == 0 else messages.WARNING
        )
    sync_history_bulk.short_description = "📊 Synchroniser l'historique des prix des AllAssets sélectionnés"


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
