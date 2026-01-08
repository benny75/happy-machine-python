import psycopg2
import psycopg2.errors
import pandas as pd
from io import StringIO
import sys
import os

# Add the parent directory to the path so we can import from data module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.db_config import get_db_connection

def populate_hot_stocks():
    """
    Connects to the PostgreSQL database, creates a 'hot_stocks' table if it doesn't exist,
    and populates it with data from 'us_high_volume_stocks.csv'.
    """
    connection = None
    try:
        # Connection parameters from TimescaleDBSticksDao.py
        connection = get_db_connection()
        cursor = connection.cursor()

        # Create table if it doesn't exist
        table_name = 'hot_stocks'
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            symbol VARCHAR(16) PRIMARY KEY,
            name VARCHAR(255),
            epic VARCHAR(32) DEFAULT ''
        );
        """
        cursor.execute(create_table_query)
        print(f"Table '{table_name}' created or already exists.")

        # Add the 'type' column if it doesn't exist
        # try:
        #     cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN type VARCHAR(32) DEFAULT '';")
        #     print(f"Added 'type' column to '{table_name}' table.")
        # except psycopg2.errors.DuplicateColumn:
        #     print(f"'type' column already exists in '{table_name}' table.")
        # except Exception as e:
        #     print(f"Error adding 'type' column: {e}")

        # Read data from CSV, ensuring 'NA' is not treated as NaN
        csv_path = 'us_high_volume_stocks.csv'
        df = pd.read_csv(csv_path, keep_default_na=False)

        # Add the EPIC column with a default empty value
        df['epic'] = ''
        
        # Add the TYPE column and set it to 'STOCK' for this data source
        df['type'] = 'STOCK'
        
        # Prepare data for bulk insert
        # Using StringIO and copy_from for efficient insertion
        buffer = StringIO()
        df.to_csv(buffer, index=False, header=False)
        buffer.seek(0)

        # Truncate the table to avoid duplicate key errors on re-run
        # cursor.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY;")
        # print(f"Table '{table_name}' truncated.")

        # Bulk insert data
        cursor.copy_expert(f"COPY {table_name}(symbol, name, epic, type) FROM STDIN WITH (FORMAT CSV)", buffer)
        print(f"{len(df)} rows inserted into '{table_name}'.")

        connection.commit()

    except (Exception, psycopg2.Error) as error:
        print(f"Error while connecting to PostgreSQL or populating data: {error}")
        if connection:
            connection.rollback()

    finally:
        # Closing database connection.
        if connection:
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")

if __name__ == "__main__":
    populate_hot_stocks()
