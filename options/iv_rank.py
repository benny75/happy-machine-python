import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import psycopg2

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.db_config import get_db_connection

def get_iv_history(symbol: str) -> pd.DataFrame:
    """
    Retrieves the historical daily average IV for a symbol, 
    considering only near-the-money options (within 5% of underlying).
    """
    conn = get_db_connection()
    try:
        query = """
            SELECT 
                DATE(timestamp) as date,
                AVG(implied_vol) as avg_iv
            FROM options_prices
            WHERE symbol = %s
              AND implied_vol > 0
              AND underlying_price > 0
              AND ABS(strike - underlying_price) / underlying_price < 0.05
            GROUP BY DATE(timestamp)
            ORDER BY date
        """
        # using pandas read_sql for convenience
        df = pd.read_sql(query, conn, params=(symbol,))
        return df
    except Exception as e:
        print(f"Error fetching IV history: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def get_iv_rank(symbol: str):
    """
    Calculates the IV Rank for a given symbol based on historical data.
    
    IV Rank = (Current IV - 1 Year Low IV) / (1 Year High IV - 1 Year Low IV) * 100
    
    Returns:
        dict: {
            "symbol": str,
            "current_iv": float,
            "iv_rank": float,
            "year_high": float,
            "year_low": float,
            "data_start": date,
            "data_end": date
        }
    """
    df = get_iv_history(symbol)
    
    if df.empty:
        return {"error": f"No data found for symbol {symbol}"}
    
    # Ensure 'date' is datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Sort just in case
    df = df.sort_values('date')
    
    # Get the most recent IV
    current_iv = df.iloc[-1]['avg_iv']
    last_date = df.iloc[-1]['date']
    
    # Filter for the last 1 year relative to the last available date
    # (Since data might be stale, we define "1 Year" as the 365 days ending on the last data point)
    one_year_ago = last_date - timedelta(days=365)
    df_year = df[df['date'] >= one_year_ago]
    
    if df_year.empty:
         return {"error": "Insufficient data for 1 year calculation"}
         
    year_low = df_year['avg_iv'].min()
    year_high = df_year['avg_iv'].max()
    
    if year_high == year_low:
        iv_rank = 0.0
    else:
        iv_rank = (current_iv - year_low) / (year_high - year_low) * 100
        
    return {
        "symbol": symbol,
        "current_iv": round(current_iv, 4),
        "iv_rank": round(iv_rank, 2),
        "year_high": round(year_high, 4),
        "year_low": round(year_low, 4),
        "data_start": df_year['date'].min().date(),
        "data_end": last_date.date(),
        "total_data_points": len(df_year)
    }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        sym = sys.argv[1]
        print(f"Calculating IV Rank for {sym}...")
        result = get_iv_rank(sym)
        import pprint
        pprint.pprint(result)
    else:
        print("Usage: python options/iv_rank.py <SYMBOL>")
