import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import datetime, timezone
import sys
import os

# Add parent dir to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.db_config import get_db_connection

def get_options_data(symbol, from_time=None, to_time=None, expiration=None, option_right=None, strike=None):
    """
    Retrieve options data from the database.
    
    Args:
        symbol (str): The ticker symbol (e.g., "SPY")
        from_time (datetime, optional): Start time for data retrieval
        to_time (datetime, optional): End time for data retrieval
        expiration (str, optional): Option expiration date string
        option_right (str, optional): Option right, 'C' for call or 'P' for put
        strike (float, optional): Strike price
        
    Returns:
        pandas.DataFrame: DataFrame containing options data
    """
    connection = get_db_connection()

    query_parts = ["SELECT * FROM options_prices WHERE symbol = %s"]
    params = [symbol]
    
    if from_time:
        query_parts.append("timestamp >= %s")
        params.append(from_time)
    
    if to_time:
        query_parts.append("timestamp <= %s")
        params.append(to_time)
    
    if expiration:
        query_parts.append("expiration = %s")
        params.append(expiration)
    
    if option_right:
        query_parts.append("option_right = %s")
        params.append(option_right)
    
    if strike:
        query_parts.append("strike = %s")
        params.append(strike)
    
    query = " AND ".join(query_parts) + " ORDER BY timestamp"
    
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
        if not rows:
            return pd.DataFrame()
            
        # Convert to DataFrame
        df = pd.DataFrame(rows)
        
        # Convert timestamp to datetime index with UTC timezone
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(timezone.utc)
            df = df.set_index('timestamp')
            
        return df
    
    except Exception as e:
        print(f"Error retrieving options data: {e}")
        return pd.DataFrame()
    
    finally:
        connection.close()


def get_option_chain(symbol, expiration=None, timestamp=None):
    """
    Get a complete option chain for a given symbol and expiration date.
    
    Args:
        symbol (str): The ticker symbol
        expiration (str, optional): Option expiration date string. If None, returns data for all expirations.
        timestamp (datetime, optional): Specific timestamp to get data for. If None, uses the latest data.
        
    Returns:
        tuple: (calls_df, puts_df) containing DataFrames for calls and puts
    """
    connection = get_db_connection()
    
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            # If no timestamp is provided, get the latest data for each option
            if not timestamp and not expiration:
                query = """
                WITH latest_timestamps AS (
                    SELECT 
                        expiration, 
                        option_right, 
                        strike, 
                        MAX(timestamp) as latest_timestamp
                    FROM 
                        options_prices
                    WHERE 
                        symbol = %s
                    GROUP BY 
                        expiration, option_right, strike
                )
                SELECT 
                    op.*
                FROM 
                    options_prices op
                JOIN 
                    latest_timestamps lt
                ON 
                    op.expiration = lt.expiration
                    AND op.option_right = lt.option_right
                    AND op.strike = lt.strike
                    AND op.timestamp = lt.latest_timestamp
                WHERE 
                    op.symbol = %s
                ORDER BY 
                    op.expiration, op.strike, op.option_right
                """
                cursor.execute(query, [symbol, symbol])
            elif not timestamp and expiration:
                query = """
                WITH latest_timestamps AS (
                    SELECT 
                        expiration, 
                        option_right, 
                        strike, 
                        MAX(timestamp) as latest_timestamp
                    FROM 
                        options_prices
                    WHERE 
                        symbol = %s
                        AND expiration = %s
                    GROUP BY 
                        expiration, option_right, strike
                )
                SELECT 
                    op.*
                FROM 
                    options_prices op
                JOIN 
                    latest_timestamps lt
                ON 
                    op.expiration = lt.expiration
                    AND op.option_right = lt.option_right
                    AND op.strike = lt.strike
                    AND op.timestamp = lt.latest_timestamp
                WHERE 
                    op.symbol = %s
                    AND op.expiration = %s
                ORDER BY 
                    op.expiration, op.strike, op.option_right
                """
                cursor.execute(query, [symbol, expiration, symbol, expiration])
            else:
                # Build the query for a specific timestamp
                query = "SELECT * FROM options_prices WHERE symbol = %s"
                params = [symbol]
                
                if expiration:
                    query += " AND expiration = %s"
                    params.append(expiration)
                    
                if timestamp:
                    query += " AND timestamp = %s"
                    params.append(timestamp)
                
                query += " ORDER BY expiration, strike, option_right"
                cursor.execute(query, params)
                
            rows = cursor.fetchall()
            
        if not rows:
            return pd.DataFrame(), pd.DataFrame()
            
        # Convert to DataFrame
        df = pd.DataFrame(rows)
        
        # Convert timestamp to datetime with UTC timezone
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(timezone.utc)
            
        # Split into calls and puts
        calls_df = df[df['option_right'] == 'C'].copy()
        puts_df = df[df['option_right'] == 'P'].copy()
        
        return calls_df, puts_df
    
    except Exception as e:
        print(f"Error retrieving option chain: {e}")
        return pd.DataFrame(), pd.DataFrame()
    
    finally:
        connection.close()


def get_available_expirations(symbol):
    """
    Get all available expiration dates for a given symbol.
    
    Args:
        symbol (str): The ticker symbol
        
    Returns:
        list: List of expiration dates as strings
    """
    connection = get_db_connection()
    
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            query = """
            SELECT DISTINCT expiration 
            FROM options_prices 
            WHERE symbol = %s
            ORDER BY expiration
            """
            cursor.execute(query, (symbol,))
            rows = cursor.fetchall()
            
        return [row['expiration'] for row in rows]
    
    except Exception as e:
        print(f"Error retrieving available expirations: {e}")
        return []
    
    finally:
        connection.close()


if __name__ == "__main__":
    # Example usage
    symbol = "ABBV"
    
    # Get available expirations
    expirations = get_available_expirations(symbol)
    if expirations:
        print(f"Available expirations for {symbol}: {expirations}")
        
        # Get the first expiration date
        expiration = expirations[0]
        
        # Get option chain for this expiration
        calls, puts = get_option_chain(symbol, expiration)
        
        if not calls.empty:
            print(f"\nCalls for {symbol} expiring {expiration}:")
            print(calls[['strike', 'bid', 'ask', 'delta', 'gamma', 'theta', 'vega', 'implied_vol', 'underlying_price']].head())
        
        if not puts.empty:
            print(f"\nPuts for {symbol} expiring {expiration}:")
            print(puts[['strike', 'bid', 'ask', 'delta', 'gamma', 'theta', 'vega', 'implied_vol', 'underlying_price']].head())
    else:
        print(f"No options data found for {symbol}") 