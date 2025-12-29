# Generated manually

from django.db import migrations, models
import django.db.models.deletion


def migrate_position_data(apps, schema_editor):
    """
    Migration des données: remplir all_asset depuis asset.all_asset ou créer AllAsset.
    """
    Position = apps.get_model('trading', 'Position')
    AllAssets = apps.get_model('trading', 'AllAssets')
    Asset = apps.get_model('trading', 'Asset')
    
    positions_to_update = []
    created_count = 0
    updated_count = 0
    
    for position in Position.objects.filter(all_asset__isnull=True):
        # Essayer de récupérer all_asset depuis asset.all_asset
        if position.asset and position.asset.all_asset:
            position.all_asset = position.asset.all_asset
            updated_count += 1
        else:
            # Créer un AllAsset minimal à partir de asset
            if position.asset:
                # Chercher si un AllAsset existe déjà avec ce symbol
                # On ne connaît pas la platform, donc on cherche dans toutes
                all_asset = AllAssets.objects.filter(
                    symbol=position.asset.symbol
                ).first()
                
                if not all_asset:
                    # Créer un AllAsset minimal (platform=UNKNOWN car on ne connaît pas)
                    all_asset = AllAssets.objects.create(
                        symbol=position.asset.symbol,
                        name=position.asset.name or position.asset.symbol,
                        platform='OTHER',  # On ne connaît pas la platform exacte
                        asset_type=position.asset.asset_type or 'UNKNOWN',
                        market='',
                        currency=position.asset.currency or 'USD',
                        is_tradable=True,
                    )
                    created_count += 1
                
                position.all_asset = all_asset
                updated_count += 1
            else:
                # Position sans asset ni all_asset - on ne peut pas la migrer
                # Elle sera mise à jour lors de la prochaine sync
                print(f"Warning: Position {position.id} has no asset or all_asset. Skipping.")
                continue
        
        positions_to_update.append(position)
    
    # Bulk update pour performance
    if positions_to_update:
        Position.objects.bulk_update(positions_to_update, ['all_asset'])
    
    print(f"Migration completed: {updated_count} positions updated, {created_count} AllAssets created")


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0006_fix_brokersynclog_error_message_default'),
    ]

    operations = [
        # Ajouter all_asset comme ForeignKey (nullable temporairement pour migration)
        migrations.AddField(
            model_name='position',
            name='all_asset',
            field=models.ForeignKey(
                help_text='Asset depuis le catalogue universel AllAssets',
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='positions',
                to='trading.allassets'
            ),
        ),
        
        # Rendre asset optionnel (nullable)
        migrations.AlterField(
            model_name='position',
            name='asset',
            field=models.ForeignKey(
                blank=True,
                help_text='Asset enrichi optionnel (pour données supplémentaires)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='positions',
                to='trading.asset'
            ),
        ),
        
        # Créer une migration de données pour remplir all_asset depuis asset
        migrations.RunPython(
            code=migrate_position_data,
            reverse_code=migrations.RunPython.noop,
        ),
        
        # Rendre all_asset obligatoire après migration des données
        migrations.AlterField(
            model_name='position',
            name='all_asset',
            field=models.ForeignKey(
                help_text='Asset depuis le catalogue universel AllAssets',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='positions',
                to='trading.allassets'
            ),
        ),
    ]

