import psycopg2
from datetime import datetime, timedelta
from psycopg2.extras import RealDictCursor
import pandas as pd
from typing import Optional, List, Dict, Any
from data.db_config import get_db_connection

# Category mappings for common asset types
CATEGORY_MAPPINGS = {
    "fx": [
        "CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",
        "SWISS FRANC - CHICAGO MERCANTILE EXCHANGE", 
        "BRITISH POUND - CHICAGO MERCANTILE EXCHANGE",
        "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE",
        "EURO FX - CHICAGO MERCANTILE EXCHANGE",
        "AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",
        "EURO FX/BRITISH POUND XRATE - CHICAGO MERCANTILE EXCHANGE",
        "MEXICAN PESO - CHICAGO MERCANTILE EXCHANGE",
        "BRAZILIAN REAL - CHICAGO MERCANTILE EXCHANGE",
        "NZ DOLLAR - CHICAGO MERCANTILE EXCHANGE",
        "SO AFRICAN RAND - CHICAGO MERCANTILE EXCHANGE"
    ],
    "stock_index": [
        "DJIA Consolidated - CHICAGO BOARD OF TRADE",
        "DJIA x $5 - CHICAGO BOARD OF TRADE",
        "S&P 500 Consolidated - CHICAGO MERCANTILE EXCHANGE",
        "E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE",
        "NASDAQ-100 Consolidated - CHICAGO MERCANTILE EXCHANGE",
        "NASDAQ MINI - CHICAGO MERCANTILE EXCHANGE",
        "RUSSELL E-MINI - CHICAGO MERCANTILE EXCHANGE",
        "MICRO E-MINI S&P 500 INDEX - CHICAGO MERCANTILE EXCHANGE",
        "MICRO E-MINI NASDAQ-100 INDEX - CHICAGO MERCANTILE EXCHANGE",
        "MICRO E-MINI RUSSELL 2000 INDX - CHICAGO MERCANTILE EXCHANGE"
    ],
    "commodities": ["CRUDE OIL", "GOLD", "SILVER", "COPPER", "NATURAL GAS"],
    "bonds": [
        "UST BOND - CHICAGO BOARD OF TRADE",
        "ULTRA UST BOND - CHICAGO BOARD OF TRADE", 
        "UST 2Y NOTE - CHICAGO BOARD OF TRADE",
        "UST 10Y NOTE - CHICAGO BOARD OF TRADE",
        "ULTRA UST 10Y - CHICAGO BOARD OF TRADE",
        "UST 5Y NOTE - CHICAGO BOARD OF TRADE",
        "FED FUNDS - CHICAGO BOARD OF TRADE"
    ],
    "crypto": ["BITCOIN", "ETHEREUM"]
}

def get_assets_by_category(category: str) -> List[str]:
    """Get list of assets for a given category."""
    category_lower = category.lower()
    if category_lower in CATEGORY_MAPPINGS:
        return CATEGORY_MAPPINGS[category_lower]
    else:
        # If not a predefined category, treat as a single asset name
        return [category]

def get_cot_data(
    category: str,
    days_back: int = 30,
    limit: Optional[int] = None
) -> pd.DataFrame:
    """
    Query COT data for a specific category within the specified time period.
    
    Args:
        category: Asset category (fx, stock_index, commodities, bonds, crypto) or specific asset name
        days_back: Number of days to look back from today (default: 30)
        limit: Maximum number of records to return (optional)
    
    Returns:
        pandas DataFrame containing COT data
    """
    assets = get_assets_by_category(category)
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    # Build the query
    placeholders = ','.join(['%s'] * len(assets))
    query = f"""
        SELECT 
            asset,
            report_date,
            as_of_date,
            open_interest,
            delta_open_interest,
            asset_mgr_long,
            asset_mgr_short,
            asset_mgr_delta_long,
            asset_mgr_delta_short,
            asset_mgr_long_pct,
            asset_mgr_short_pct,
            asset_mgr_net,
            dealer_long,
            dealer_short,
            dealer_delta_long,
            dealer_delta_short,
            dealer_long_pct,
            dealer_short_pct,
            dealer_net,
            lev_money_long,
            lev_money_short,
            lev_money_delta_long,
            lev_money_delta_short,
            lev_money_long_pct,
            lev_money_short_pct,
            lev_money_net,
            other_rept_long,
            other_rept_short,
            other_rept_delta_long,
            other_rept_delta_short,
            other_rept_long_pct,
            other_rept_short_pct,
            other_rept_net,
            ingest_ts
        FROM cot_data_all 
        WHERE asset IN ({placeholders})
        AND report_date >= %s
        ORDER BY report_date DESC, asset
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    params = assets + [cutoff_date.strftime('%Y-%m-%d')]
    
    connection = get_db_connection()
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Convert to DataFrame
            if results:
                df = pd.DataFrame([dict(row) for row in results])
                
                # Convert date columns to proper datetime types
                if 'report_date' in df.columns:
                    df['report_date'] = pd.to_datetime(df['report_date'])
                if 'as_of_date' in df.columns:
                    df['as_of_date'] = pd.to_datetime(df['as_of_date'])
                if 'ingest_ts' in df.columns:
                    df['ingest_ts'] = pd.to_datetime(df['ingest_ts'])
                
                return df
            else:
                # Return empty DataFrame with expected columns
                columns = [
                    'asset', 'report_date', 'as_of_date', 'open_interest', 'delta_open_interest',
                    'asset_mgr_long', 'asset_mgr_short', 'asset_mgr_delta_long', 'asset_mgr_delta_short',
                    'asset_mgr_long_pct', 'asset_mgr_short_pct', 'asset_mgr_net',
                    'dealer_long', 'dealer_short', 'dealer_delta_long', 'dealer_delta_short',
                    'dealer_long_pct', 'dealer_short_pct', 'dealer_net',
                    'lev_money_long', 'lev_money_short', 'lev_money_delta_long', 'lev_money_delta_short',
                    'lev_money_long_pct', 'lev_money_short_pct', 'lev_money_net',
                    'other_rept_long', 'other_rept_short', 'other_rept_delta_long', 'other_rept_delta_short',
                    'other_rept_long_pct', 'other_rept_short_pct', 'other_rept_net', 'ingest_ts'
                ]
                return pd.DataFrame(columns=columns)
                
    finally:
        connection.close()

def get_available_assets() -> List[str]:
    """Get list of all available assets in the database."""
    query = "SELECT DISTINCT asset FROM cot_data_all ORDER BY asset"
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
            return [row[0] for row in results]
    finally:
        connection.close()

def get_date_range() -> Dict[str, Any]:
    """Get the date range of available data."""
    query = """
        SELECT 
            MIN(report_date) as earliest_date,
            MAX(report_date) as latest_date,
            COUNT(*) as total_records
        FROM cot_data_all
    """
    
    connection = get_db_connection()
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            result = cursor.fetchone()
            
            return {
                "earliest_date": result['earliest_date'].isoformat() if result['earliest_date'] else None,
                "latest_date": result['latest_date'].isoformat() if result['latest_date'] else None,
                "total_records": result['total_records']
            }
    finally:
        connection.close()
