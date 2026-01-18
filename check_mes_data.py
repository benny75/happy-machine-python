import sys
import os
import pandas as pd

# Add project root to path
sys.path.append(os.getcwd())

from data.db_config import get_db_connection

def check_mes_data():
    conn = get_db_connection()
    try:
        # Check for MES symbol
        query = "SELECT count(*) FROM options_prices WHERE symbol = 'MES'"
        cur = conn.cursor()
        cur.execute(query)
        count = cur.fetchone()[0]
        print(f"Rows for MES in options_prices: {count}")
        
        if count == 0:
            # Check what symbols we do have
            cur.execute("SELECT DISTINCT symbol FROM options_prices LIMIT 10")
            rows = cur.fetchall()
            print("Available symbols:", [r[0] for r in rows])
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_mes_data()
