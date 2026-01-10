#!/usr/bin/env python3
"""
Populates the stock_metadata table with data from the local TimescaleDB stick table.
Columns: symbol, status, last_stick_datetime, dollar_volume, avg_volume_30d, close_price
"""

import os
import sys
import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add parent dir to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.TimescaleDBSticksDao import get_sticks
from data.db_config import get_db_connection

def get_hot_stocks():
    """Fetch all symbols from hot_stocks table"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT symbol FROM hot_stocks ORDER BY symbol")
    symbols = [row[0] for row in cur.fetchall()]
    conn.close()
    return symbols

def get_stick_metrics(symbol):
    """
    Get metrics from local stick data.
    Returns: {last_stick_datetime, close_price, dollar_volume, avg_volume_30d}
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60) 
        
        df = get_sticks(symbol, 1440, start_date, end_date)
        
        if df.empty:
            return None
            
        last_stick = df.iloc[-1]
        
        close_price = (last_stick['bid_close'] + last_stick['ask_close']) / 2
        volume = last_stick['volume']
        dollar_vol = close_price * volume
        last_date = df.index[-1].to_pydatetime()
        
        last_30 = df.tail(30)
        avg_vol = last_30['volume'].mean()
        
        return {
            'last_stick_datetime': last_date,
            'close_price': float(close_price),
            'dollar_volume': float(dollar_vol),
            'avg_volume_30d': float(avg_vol)
        }
        
    except Exception:
        return None

def upsert_metadata(data_list):
    """
    Upsert list of dicts into stock_metadata table.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    query = """
    INSERT INTO stock_metadata (
        symbol, status, last_stick_datetime, dollar_volume, 
        avg_volume_30d, close_price, updated_at
    ) VALUES %s
    ON CONFLICT (symbol) DO UPDATE SET
        status = EXCLUDED.status,
        last_stick_datetime = EXCLUDED.last_stick_datetime,
        dollar_volume = EXCLUDED.dollar_volume,
        avg_volume_30d = EXCLUDED.avg_volume_30d,
        close_price = EXCLUDED.close_price,
        updated_at = NOW()
    """
    
    values = []
    for item in data_list:
        values.append((
            item['symbol'],
            item['status'],
            item['last_stick_datetime'],
            item['dollar_volume'],
            item.get('avg_volume_30d'),
            item.get('close_price'),
            datetime.now()
        ))
        
    execute_values(cur, query, values)
    conn.commit()
    conn.close()

def main():
    print("Starting stock_metadata population...")
    symbols = get_hot_stocks()
    print(f"Found {len(symbols)} symbols in hot_stocks.")
    
    chunk_size = 100
    current_chunk = []
    
    print("Processing local stick data and updating DB...")
    
    for i, symbol in enumerate(symbols):
        stick_data = get_stick_metrics(symbol)
        
        record = {
            'symbol': symbol,
            'status': 'Active' if stick_data else 'Inactive',
        }
        
        if stick_data:
            record.update(stick_data)
        else:
            record['last_stick_datetime'] = None
            record['dollar_volume'] = 0
            record['avg_volume_30d'] = 0
            record['close_price'] = 0
            
        current_chunk.append(record)
        
        if len(current_chunk) >= chunk_size:
            upsert_metadata(current_chunk)
            current_chunk = []
            if (i+1) % 500 == 0:
                print(f"  Processed {i+1}/{len(symbols)}...")
            
    if current_chunk:
        upsert_metadata(current_chunk)
        
    print("Done!")

if __name__ == "__main__":
    main()