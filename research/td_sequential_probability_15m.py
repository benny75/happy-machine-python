#!/usr/bin/env python3
"""
TD Sequential Probability Analyzer (15-Minute Timeframe)

Calculates the probability of a successful trade N bars after a TD Sequential 9 signal.
- Bullish Case: TD Buy Setup 9. Entry at Open of next bar (T+0). Success if Close of T+N > Entry Open * (1 - Buffer).
- Bearish Case: TD Sell Setup 9. Entry at Open of next bar (T+0). Success if Close of T+N < Entry Open * (1 + Buffer).
"""

import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
import pytz

# Add the parent directory to the path so we can import from data module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.TimescaleDBSticksDao import get_sticks
from data.db_config import get_db_connection

# Configuration Constants
TIME_HORIZON = 5  # T+n bars (5 * 15m = 75 minutes)
BUFFER_PCT = 0.001  # 0.1% buffer for option premium (kept same as daily, might be high for 15m but following "same selection")


def get_filtered_symbols() -> list[str]:
    """Get active symbols with dollar_volume > 100M from stock_metadata"""
    connection = get_db_connection()

    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        query = """
            SELECT symbol 
            FROM stock_metadata 
            WHERE status = 'Active' AND dollar_volume > 100000000
            ORDER BY dollar_volume DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
    connection.close()

    return [row['symbol'] for row in rows]


def calculate_td_sequential(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate TD Sequential (神奇九转) counts for a DataFrame of price data.
    """
    if df.empty or len(df) < 13:
        return df

    df = df.copy()
    # Use mid price (average of bid and ask close) for comparison
    df['close'] = (df['bid_close'] + df['ask_close']) / 2
    # We also need 'open' for the entry price. Let's use average open.
    df['open'] = (df['bid_open'] + df['ask_open']) / 2

    # TD Sequential Setup counts
    td_buy_setup = np.zeros(len(df), dtype=int)
    td_sell_setup = np.zeros(len(df), dtype=int)

    buy_count = 0
    sell_count = 0
    
    closes = df['close'].values
    
    for i in range(4, len(df)):
        current_close = closes[i]
        compare_close = closes[i - 4]

        if current_close < compare_close:
            buy_count += 1
            sell_count = 0
        elif current_close > compare_close:
            sell_count += 1
            buy_count = 0
        else:
            buy_count = 0
            sell_count = 0

        if buy_count > 9:
            buy_count = 1
        if sell_count > 9:
            sell_count = 1

        td_buy_setup[i] = buy_count
        td_sell_setup[i] = sell_count

    df['td_buy_setup'] = td_buy_setup
    df['td_sell_setup'] = td_sell_setup

    return df


def analyze_symbol(symbol: str, days_back: int = 365*3) -> dict:
    """
    Analyze a single symbol for TD signals and their outcomes.
    """
    stats = {
        'symbol': symbol,
        'bullish_signals': 0,
        'bullish_wins': 0,
        'bearish_signals': 0,
        'bearish_wins': 0
    }

    try:
        end_date = datetime.now(pytz.UTC)
        start_date = end_date - timedelta(days=days_back)

        # 15 minutes interval
        df = get_sticks(symbol, 15, start_date, end_date)

        if df.empty:
            return stats

        df = df.sort_index()
        df = calculate_td_sequential(df)

        if 'td_buy_setup' not in df.columns:
            return stats

        # Find signals
        # Signal is when count == 9
        
        # Bullish Analysis
        bullish_indices = np.where(df['td_buy_setup'] == 9)[0]
        for idx in bullish_indices:
            # Entry is next open (idx + 1)
            # Exit is T+n (idx + 1 + TIME_HORIZON)
            entry_idx = idx + 1
            exit_idx = idx + 1 + TIME_HORIZON
            
            if exit_idx < len(df):
                entry_open = df.iloc[entry_idx]['open']
                exit_close = df.iloc[exit_idx]['close']
                
                stats['bullish_signals'] += 1
                if exit_close > entry_open * (1 - BUFFER_PCT):
                    stats['bullish_wins'] += 1

        # Bearish Analysis
        bearish_indices = np.where(df['td_sell_setup'] == 9)[0]
        for idx in bearish_indices:
            entry_idx = idx + 1
            exit_idx = idx + 1 + TIME_HORIZON
            
            if exit_idx < len(df):
                entry_open = df.iloc[entry_idx]['open']
                exit_close = df.iloc[exit_idx]['close']
                
                stats['bearish_signals'] += 1
                if exit_close < entry_open * (1 + BUFFER_PCT):
                    stats['bearish_wins'] += 1

    except Exception as e:
        # print(f"Error processing {symbol}: {e}")
        pass

    return stats


def main():
    print("Fetching symbols from stock_metadata table (Active & Dollar Volume > 100M)...")
    symbols = get_filtered_symbols()
    print(f"Found {len(symbols)} symbols. Analyzing last 3 years of 15-minute data...")
    print(f"Time Horizon: {TIME_HORIZON} bars ({TIME_HORIZON * 15} minutes)")
    print(f"Buffer: {BUFFER_PCT*100:.0f}%")

    total_stats = {
        'bullish_signals': 0,
        'bullish_wins': 0,
        'bearish_signals': 0,
        'bearish_wins': 0
    }
    
    symbol_results = []

    # Process subset for testing if list is huge, but user said "same selection", so we do all.
    # However, for 15m data, this might be very slow.
    # I will process all but maybe print progress more frequently.
    
    for i, symbol in enumerate(symbols):
        if i % 10 == 0:
            print(f"Processing {i}/{len(symbols)}: {symbol}...")
            
        stats = analyze_symbol(symbol)
        
        total_stats['bullish_signals'] += stats['bullish_signals']
        total_stats['bullish_wins'] += stats['bullish_wins']
        total_stats['bearish_signals'] += stats['bearish_signals']
        total_stats['bearish_wins'] += stats['bearish_wins']
        
        if stats['bullish_signals'] > 0 or stats['bearish_signals'] > 0:
            symbol_results.append(stats)

    print("\n" + "="*60)
    print(f"TD SEQUENTIAL PROBABILITY REPORT (15m, T+{TIME_HORIZON} Bars, {BUFFER_PCT*100:.0f}% Buffer)")
    print("="*60)
    
    # Global Statistics
    print("\nGLOBAL STATISTICS:")
    
    # Bullish
    bull_signals = total_stats['bullish_signals']
    bull_wins = total_stats['bullish_wins']
    bull_rate = (bull_wins / bull_signals * 100) if bull_signals > 0 else 0
    
    print(f"\nBullish Setup (Buy 9) -> Expect Higher Close:")
    print(f"  Total Signals: {bull_signals}")
    print(f"  Successful Outcomes: {bull_wins}")
    print(f"  Success Rate: {bull_rate:.2f}%")
    
    # Bearish
    bear_signals = total_stats['bearish_signals']
    bear_wins = total_stats['bearish_wins']
    bear_rate = (bear_wins / bear_signals * 100) if bear_signals > 0 else 0
    
    print(f"\nBearish Setup (Sell 9) -> Expect Lower Close:")
    print(f"  Total Signals: {bear_signals}")
    print(f"  Successful Outcomes: {bear_wins}")
    print(f"  Success Rate: {bear_rate:.2f}%")
    
    print("\n" + "="*60)
    
    # Top Performers (min 5 signals)
    print("\nTOP PERFORMING SYMBOLS (Min 5 signals):")
    
    # Prepare DataFrame for easy sorting
    if symbol_results:
        results_df = pd.DataFrame(symbol_results)
        
        results_df['bull_rate'] = results_df.apply(
            lambda x: (x['bullish_wins'] / x['bullish_signals'] * 100) if x['bullish_signals'] > 0 else 0, axis=1
        )
        results_df['bear_rate'] = results_df.apply(
            lambda x: (x['bearish_wins'] / x['bearish_signals'] * 100) if x['bearish_signals'] > 0 else 0, axis=1
        )
        
        # Sort by best bullish rate
        print("\n--- Best Bullish Signals ---")
        bull_df = results_df[results_df['bullish_signals'] >= 5].sort_values('bull_rate', ascending=False).head(10)
        print(bull_df[['symbol', 'bullish_signals', 'bull_rate']].to_string(index=False))
        
        # Sort by best bearish rate
        print("\n--- Best Bearish Signals ---")
        bear_df = results_df[results_df['bearish_signals'] >= 5].sort_values('bear_rate', ascending=False).head(10)
        print(bear_df[['symbol', 'bearish_signals', 'bear_rate']].to_string(index=False))

if __name__ == "__main__":
    main()
