# Generated manually

from django.db import migrations, models
import django.db.models.deletion


def migrate_trade_data(apps, schema_editor):
    """
    Migration des données: remplir all_asset depuis asset.all_asset ou créer AllAsset.
    """
    Trade = apps.get_model('trading', 'Trade')
    AllAssets = apps.get_model('trading', 'AllAssets')
    Asset = apps.get_model('trading', 'Asset')
    
    trades_to_update = []
    created_count = 0
    updated_count = 0
    
    for trade in Trade.objects.filter(all_asset__isnull=True):
        # Essayer de récupérer all_asset depuis asset.all_asset
        if trade.asset and trade.asset.all_asset:
            trade.all_asset = trade.asset.all_asset
            updated_count += 1
        else:
            # Créer un AllAsset minimal à partir de asset
            if trade.asset:
                # Chercher si un AllAsset existe déjà avec ce symbol
                # On ne connaît pas la platform, donc on cherche dans toutes
                all_asset = AllAssets.objects.filter(
                    symbol=trade.asset.symbol
                ).first()
                
                if not all_asset:
                    # Créer un AllAsset minimal (platform=UNKNOWN car on ne connaît pas)
                    all_asset = AllAssets.objects.create(
                        symbol=trade.asset.symbol,
                        name=trade.asset.name or trade.asset.symbol,
                        platform='OTHER',  # On ne connaît pas la platform exacte
                        asset_type=trade.asset.asset_type or 'UNKNOWN',
                        market='',
                        currency=trade.asset.currency or 'USD',
                        is_tradable=True,
                    )
                    created_count += 1
                
                trade.all_asset = all_asset
                updated_count += 1
            else:
                # Trade sans asset ni all_asset - on ne peut pas la migrer
                # Il sera mis à jour lors de la prochaine sync
                print(f"Warning: Trade {trade.id} has no asset or all_asset. Skipping.")
                continue
        
        trades_to_update.append(trade)
    
    # Bulk update pour performance
    if trades_to_update:
        Trade.objects.bulk_update(trades_to_update, ['all_asset'])
    
    print(f"Migration completed: {updated_count} trades updated, {created_count} AllAssets created")


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0007_add_all_asset_to_position'),
    ]

    operations = [
        # Ajouter all_asset comme ForeignKey (nullable temporairement pour migration)
        migrations.AddField(
            model_name='trade',
            name='all_asset',
            field=models.ForeignKey(
                help_text='Asset depuis le catalogue universel AllAssets',
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='trades',
                to='trading.allassets'
            ),
        ),
        
        # Rendre asset optionnel (nullable)
        migrations.AlterField(
            model_name='trade',
            name='asset',
            field=models.ForeignKey(
                blank=True,
                help_text='Asset enrichi optionnel (pour données supplémentaires)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='trades',
                to='trading.asset'
            ),
        ),
        
        # Créer une migration de données pour remplir all_asset depuis asset
        migrations.RunPython(
            code=migrate_trade_data,
            reverse_code=migrations.RunPython.noop,
        ),
        
        # Rendre all_asset obligatoire après migration des données
        migrations.AlterField(
            model_name='trade',
            name='all_asset',
            field=models.ForeignKey(
                help_text='Asset depuis le catalogue universel AllAssets',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='trades',
                to='trading.allassets'
            ),
        ),
    ]

