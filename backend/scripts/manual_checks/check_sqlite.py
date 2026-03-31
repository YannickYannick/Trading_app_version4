import os
import sqlite3

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
os.chdir(_BACKEND_ROOT)
_db = os.path.join(_BACKEND_ROOT, "db.sqlite3")

try:
    conn = sqlite3.connect(_db)
    cursor = conn.cursor()
    
    print("Checking for asset 101173 in trading_allassets...")
    cursor.execute("SELECT id, symbol, platform FROM trading_allassets WHERE id=101173")
    row = cursor.fetchone()
    
    if row:
        print(f"FOUND: ID={row[0]}, Symbol={row[1]}, Platform={row[2]}")
    else:
        print("NOT FOUND in trading_allassets")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
