# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0008_add_all_asset_to_trade'),
    ]

    operations = [
        migrations.CreateModel(
            name='AllAssetPriceHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('date', models.DateField(db_index=True)),
                ('open_price', models.DecimalField(decimal_places=8, max_digits=20)),
                ('high_price', models.DecimalField(decimal_places=8, max_digits=20)),
                ('low_price', models.DecimalField(decimal_places=8, max_digits=20)),
                ('close_price', models.DecimalField(decimal_places=8, max_digits=20)),
                ('volume', models.BigIntegerField(blank=True, null=True)),
                ('source', models.CharField(choices=[('YAHOO', 'Yahoo Finance'), ('SAXO', 'Saxo Bank'), ('BINANCE', 'Binance'), ('IB', 'Interactive Brokers'), ('MANUAL', 'Manuel')], default='YAHOO', help_text='Source des données de prix', max_length=10)),
                ('all_asset', models.ForeignKey(help_text='AllAsset pour lequel cet historique est enregistré', on_delete=django.db.models.deletion.CASCADE, related_name='price_history', to='trading.allassets')),
            ],
            options={
                'verbose_name': 'AllAsset Price History',
                'verbose_name_plural': 'AllAssets Price History',
                'ordering': ['-date'],
            },
        ),
        migrations.AddIndex(
            model_name='allassetpricehistory',
            index=models.Index(fields=['all_asset', 'date'], name='trading_all_all_asse_idx'),
        ),
        migrations.AddIndex(
            model_name='allassetpricehistory',
            index=models.Index(fields=['all_asset', '-date'], name='trading_all_all_asse_idx_desc'),
        ),
        migrations.AlterUniqueTogether(
            name='allassetpricehistory',
            unique_together={('all_asset', 'date', 'source')},
        ),
    ]



