import psycopg2
import sys
import os

# Add parent dir to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.db_config import get_db_connection

def create_table():
    connection = get_db_connection()
    
    cursor = connection.cursor()
    
    create_table_query = """
    CREATE TABLE IF NOT EXISTS stock_metadata (
        symbol TEXT PRIMARY KEY,
        status TEXT,
        last_stick_datetime TIMESTAMPTZ,
        dollar_volume DOUBLE PRECISION,
        
        -- Filtering columns
        avg_volume_30d DOUBLE PRECISION,   -- Filter by liquidity (average volume)
        close_price DOUBLE PRECISION,      -- Filter by price range
        
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    """
    
    try:
        cursor.execute(create_table_query)
        connection.commit()
        print("Table 'stock_metadata' updated successfully.")
        
    except Exception as e:
        print(f"Error creating table: {e}")
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    create_table()