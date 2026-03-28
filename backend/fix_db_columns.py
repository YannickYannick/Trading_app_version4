import os
import django
from django.db import connection

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config_django.settings.production")
django.setup()

def fix_strategy_table():
    with connection.cursor() as cursor:
        print("Vérification des colonnes de la table trading_strategy...")
        
        # Liste des colonnes attendues
        columns_to_add = [
            ("asset_id", "integer NULL REFERENCES trading_asset(id) DEFERRABLE INITIALLY DEFERRED"),
            ("broker_account_id", "integer NULL REFERENCES trading_brokeraccount(id) DEFERRABLE INITIALLY DEFERRED"),
            ("budget", "numeric(20, 2) NULL"),
            ("check_frequency", "integer NOT NULL DEFAULT 45"),
            ("execution_mode", "varchar(20) NOT NULL DEFAULT 'simulation'"),
            ("max_quantity", "numeric(20, 10) NULL"),
            ("min_quantity", "numeric(20, 10) NULL"),
            ("portfolio_quantity", "numeric(20, 10) NOT NULL DEFAULT 0"),
        ]

        # Récupérer les colonnes existantes
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'trading_strategy'
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        print(f"Colonnes existantes : {existing_columns}")

        for col_name, col_def in columns_to_add:
            if col_name not in existing_columns:
                print(f"Ajout de la colonne manquante : {col_name}")
                try:
                    cursor.execute(f"ALTER TABLE trading_strategy ADD COLUMN {col_name} {col_def}")
                    print(f"✅ Colonne {col_name} ajoutée avec succès.")
                except Exception as e:
                    print(f"❌ Erreur lors de l'ajout de {col_name}: {e}")
            else:
                print(f"ℹ️ La colonne {col_name} existe déjà.")

        print("\nCréation des index manquants pour les Foreign Keys...")
        # Création simplifiée des index (nom généré automatiquement ou ignoré si existe)
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS trading_strategy_asset_id_idx ON trading_strategy(asset_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS trading_strategy_broker_account_id_idx ON trading_strategy(broker_account_id)")
            print("✅ Index créés.")
        except Exception as e:
             print(f"⚠️ Erreur index (peut être ignoré): {e}")

if __name__ == "__main__":
    fix_strategy_table()
