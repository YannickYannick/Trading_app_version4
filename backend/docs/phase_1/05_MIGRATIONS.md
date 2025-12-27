# 🔄 Migrations Django

## Qu'est-ce qu'une migration ?

Les migrations sont des fichiers Python qui décrivent les changements à appliquer à la base de données (créer des tables, ajouter des colonnes, etc.).

## Workflow des migrations

```bash
# 1. Créer les migrations (après modification des modèles)
python manage.py makemigrations

# 2. Voir le SQL qui sera exécuté
python manage.py sqlmigrate trading 0001

# 3. Appliquer les migrations
python manage.py migrate

# 4. Voir le statut des migrations
python manage.py showmigrations
```

## Migrations créées

### `0001_initial.py`

Migration initiale créant toutes les tables :

```
- trading_allassets
- trading_asset
- trading_assetprice
- trading_position
- trading_trade
- trading_order
- trading_strategy
- trading_strategyperformance
- trading_broker
- trading_brokeraccount
- trading_brokersynclog
- trading_scheduledtask
- trading_taskexecutionlog
```

### `0002_...` (évolutions)

Migrations pour les champs ajoutés après la création initiale :
- Champs enrichis sur Asset (sector, industry, market_cap)
- Champs spécifiques Saxo/Binance sur AllAssets

## Structure d'une migration

```python
from django.db import migrations, models

class Migration(migrations.Migration):
    
    dependencies = [
        ('trading', '0001_initial'),  # Dépend de la migration précédente
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='sector',
            field=models.CharField(max_length=100, blank=True),
        ),
        migrations.CreateModel(
            name='NewModel',
            fields=[
                ('id', models.BigAutoField(primary_key=True)),
                # ...
            ],
        ),
    ]
```

## Commandes utiles

```bash
# Créer une migration vide (pour des opérations personnalisées)
python manage.py makemigrations trading --empty --name my_migration

# Annuler une migration
python manage.py migrate trading 0001  # Revenir à 0001

# Voir les migrations non appliquées
python manage.py showmigrations --plan

# Fusionner des migrations conflictuelles
python manage.py makemigrations --merge
```

## Bonnes pratiques

1. **Toujours vérifier les migrations avant de les appliquer**
   ```bash
   python manage.py sqlmigrate trading 0002
   ```

2. **Commiter les migrations avec le code**
   - Les migrations font partie du code source

3. **Ne jamais modifier une migration déjà appliquée**
   - Créer une nouvelle migration pour les corrections

4. **Utiliser `--fake` avec précaution**
   ```bash
   # Marquer comme appliquée sans exécuter
   python manage.py migrate trading 0002 --fake
   ```

## Base de données Supabase

Les migrations sont appliquées sur la base PostgreSQL Supabase :

```
Host: db.lowncckbivxmiakzmsxq.supabase.co
Port: 5432
Database: postgres
```

Pour voir les tables créées :
1. Aller sur https://supabase.com/dashboard
2. Ouvrir le projet
3. Table Editor → Voir les tables `trading_*`

