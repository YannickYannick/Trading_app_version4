# 🔧 Admin Django

## Configuration

L'interface admin est configurée dans `apps/trading/admin.py`.

## Accès

- URL : http://localhost:8000/admin/
- Créer un superuser : `python manage.py createsuperuser`

## Modèles enregistrés

### AllAssets

```python
@admin.register(AllAssets)
class AllAssetsAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name', 'platform', 'asset_type', 'market', 'is_tradable')
    list_filter = ('platform', 'asset_type', 'market', 'is_tradable')
    search_fields = ('symbol', 'name', 'saxo_uic')
    fieldsets = (
        (None, {
            'fields': ('symbol', 'name', 'platform', 'asset_type', 'market', 'currency', 'is_tradable')
        }),
        ('Saxo Specifics', {
            'classes': ('collapse',),
            'fields': ('saxo_uic', 'saxo_exchange_id', 'saxo_country_code'),
        }),
        ('Binance Specifics', {
            'classes': ('collapse',),
            'fields': ('binance_base_asset', 'binance_quote_asset', 'binance_status'),
        }),
    )
```

### Asset

```python
@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name', 'asset_type', 'current_price', 'is_active')
    list_filter = ('asset_type', 'is_active')
    search_fields = ('symbol', 'name', 'sector', 'industry')
    raw_id_fields = ('all_asset',)
```

### Position

```python
@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('asset', 'broker', 'strategy', 'quantity', 'entry_price', 'is_open', 'pnl')
    list_filter = ('is_open', 'broker', 'strategy', 'side')
    search_fields = ('asset__symbol', 'asset__name')
    raw_id_fields = ('asset', 'broker', 'strategy')
```

### Trade

```python
@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ('asset', 'broker', 'trade_type', 'quantity', 'price', 'executed_at')
    list_filter = ('trade_type', 'broker')
    search_fields = ('asset__symbol', 'broker_trade_id')
    raw_id_fields = ('asset', 'broker', 'position')
```

### Order

```python
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('asset', 'broker', 'order_type', 'side', 'status', 'quantity', 'price')
    list_filter = ('order_type', 'side', 'status', 'broker')
    search_fields = ('asset__symbol', 'broker_order_id')
```

### Strategy

```python
@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = ('name', 'risk_level', 'is_active', 'is_automated')
    list_filter = ('risk_level', 'is_active', 'is_automated')
    search_fields = ('name', 'description')
```

### Broker & BrokerAccount

```python
@admin.register(Broker)
class BrokerAdmin(admin.ModelAdmin):
    list_display = ('name', 'broker_type', 'is_active', 'supports_stocks', 'supports_crypto')
    list_filter = ('broker_type', 'is_active')

@admin.register(BrokerAccount)
class BrokerAccountAdmin(admin.ModelAdmin):
    list_display = ('broker', 'account_id', 'account_name', 'balance', 'is_active', 'is_demo')
    list_filter = ('broker', 'is_active', 'is_demo')
```

## Fonctionnalités utilisées

| Fonctionnalité | Description |
|----------------|-------------|
| `list_display` | Colonnes affichées dans la liste |
| `list_filter` | Filtres dans la sidebar |
| `search_fields` | Champs recherchables |
| `raw_id_fields` | Lookup rapide pour ForeignKey |
| `fieldsets` | Organisation des champs en groupes |
| `classes: collapse` | Groupes repliables |
| `readonly_fields` | Champs non modifiables |
| `date_hierarchy` | Navigation par date |

## Personnalisations

### Afficher un champ calculé

```python
@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('asset', 'pnl_display')
    
    @admin.display(description='P&L')
    def pnl_display(self, obj):
        pnl = obj.pnl
        color = 'green' if pnl >= 0 else 'red'
        return format_html('<span style="color: {}">{}</span>', color, pnl)
```

### Actions personnalisées

```python
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    actions = ['cancel_orders']
    
    @admin.action(description='Annuler les ordres sélectionnés')
    def cancel_orders(self, request, queryset):
        queryset.update(status='CANCELLED')
```

## Capture d'écran

L'admin Django permet de :
- Lister, créer, modifier, supprimer tous les modèles
- Filtrer et rechercher
- Exporter des données
- Voir l'historique des modifications

