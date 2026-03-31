import os
import sys
import psycopg2
from decouple import config

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)
os.chdir(_BACKEND_ROOT)

# Charger les variables (comme dans settings.py)
DB_NAME = config('DB_NAME', default='postgres')
DB_USER = config('DB_USER', default='postgres')
DB_PASSWORD = config('DB_PASSWORD', default='')
DB_HOST = config('DB_HOST', default='')
DB_PORT = config('DB_PORT', default='5432')

print(f"Tentative de connexion à:")
print(f"HOST: {DB_HOST}")
print(f"PORT: {DB_PORT}")
print(f"USER: {DB_USER}")
print(f"DB  : {DB_NAME}")

try:
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        connect_timeout=5
    )
    print("SUCCESS: Connexion réussie à la base de données !")
    conn.close()
except Exception as e:
    print(f"FAILURE: Échec de la connexion : {e}")
