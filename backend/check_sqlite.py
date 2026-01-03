
import sqlite3
import os

try:
    conn = sqlite3.connect('db.sqlite3')
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
