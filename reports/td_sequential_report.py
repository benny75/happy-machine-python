#!/usr/bin/env python3
"""
TD Sequential (神奇九转) Signal Scanner

Scans all symbols in the hot_stocks table for TD Sequential signals on daily sticks.
Outputs both bullish (buy setup) and bearish (sell setup) signals to a CSV file.

TD Sequential Setup Rules:
- Bullish Setup (Buy): 9 consecutive bars where each close is lower than the close 4 bars earlier
- Bearish Setup (Sell): 9 consecutive bars where each close is higher than the close 4 bars earlier

The signal is triggered on the 9th bar completion.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

# Add the parent directory to the path so we can import from data module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.TimescaleDBSticksDao import get_sticks
from data.db_config import get_db_connection


def get_hot_stock_symbols() -> List[str]:
    """Get all symbols from the hot_stocks table"""
    connection = get_db_connection()

    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        query = "SELECT symbol FROM hot_stocks ORDER BY symbol"
        cursor.execute(query)
        rows = cursor.fetchall()
    connection.close()

    return [row['symbol'] for row in rows]


def calculate_td_sequential(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate TD Sequential (神奇九转) counts for a DataFrame of price data.

    Args:
        df: DataFrame with 'bid_close' and 'ask_close' columns, indexed by datetime

    Returns:
        DataFrame with additional columns for TD Sequential counts and signals
    """
    if df.empty or len(df) < 13:  # Need at least 13 bars (4 for comparison + 9 for setup)
        return df

    df = df.copy()

    # Use mid price (average of bid and ask close) for comparison
    df['close'] = (df['bid_close'] + df['ask_close']) / 2

    # TD Sequential Setup counts - initialize as float to avoid dtype issues
    td_buy_setup = [0] * len(df)
    td_sell_setup = [0] * len(df)

    # Calculate setup counts
    buy_count = 0
    sell_count = 0

    for i in range(4, len(df)):
        current_close = df['close'].iloc[i]
        compare_close = df['close'].iloc[i - 4]

        # Bullish setup: close < close 4 bars ago
        if current_close < compare_close:
            buy_count += 1
            sell_count = 0  # Reset sell count
        # Bearish setup: close > close 4 bars ago
        elif current_close > compare_close:
            sell_count += 1
            buy_count = 0  # Reset buy count
        else:
            # Equal - reset both counts
            buy_count = 0
            sell_count = 0

        # Cap counts at 9 (and reset after completing a setup)
        if buy_count > 9:
            buy_count = 1  # Start new count
        if sell_count > 9:
            sell_count = 1  # Start new count

        td_buy_setup[i] = buy_count
        td_sell_setup[i] = sell_count

    df['td_buy_setup'] = td_buy_setup
    df['td_sell_setup'] = td_sell_setup

    return df


def find_td_signals(symbol: str) -> List[Dict]:
    """
    Find TD Sequential signals for a given symbol on the last trading day only.

    Args:
        symbol: Stock symbol

    Returns:
        List of signal dictionaries with signal details (0 or 1 signal)
    """
    import pytz

    signals = []

    try:
        # Get daily sticks - need at least 13 bars for TD Sequential calculation
        end_date = datetime.now(pytz.UTC)
        start_date = end_date - timedelta(days=30)  # Get enough data for calculation

        df = get_sticks(symbol, 1440, start_date, end_date)

        if df.empty:
            return signals

        # Sort by date
        df = df.sort_index()

        # Calculate TD Sequential
        df = calculate_td_sequential(df)

        if len(df) == 0:
            return signals

        # Only check the last stick (last trading day)
        last_idx = df.index[-1]
        last_row = df.iloc[-1]

        # Bullish signal (buy setup completed)
        if 'td_buy_setup' in last_row and last_row['td_buy_setup'] == 9:
            signals.append({
                'symbol': symbol,
                'date': last_idx.strftime('%Y-%m-%d'),
                'signal_type': 'BULLISH',
                'signal_name': 'TD Buy Setup 9',
                'close_price': last_row.get('close', 0),
                'bid_close': last_row.get('bid_close', 0),
                'ask_close': last_row.get('ask_close', 0),
                'volume': last_row.get('volume', 0)
            })

        # Bearish signal (sell setup completed)
        if 'td_sell_setup' in last_row and last_row['td_sell_setup'] == 9:
            signals.append({
                'symbol': symbol,
                'date': last_idx.strftime('%Y-%m-%d'),
                'signal_type': 'BEARISH',
                'signal_name': 'TD Sell Setup 9',
                'close_price': last_row.get('close', 0),
                'bid_close': last_row.get('bid_close', 0),
                'ask_close': last_row.get('ask_close', 0),
                'volume': last_row.get('volume', 0)
            })

    except Exception as e:
        # Silently skip symbols without data
        if "stick_datetime" not in str(e):
            print(f"Error processing {symbol}: {e}")

    return signals


def generate_report() -> pd.DataFrame:
    """
    Generate TD Sequential report for all hot stocks.
    Only checks the last trading day for signals.

    Returns:
        DataFrame with all found signals
    """
    print("Fetching symbols from hot_stocks table...")
    symbols = get_hot_stock_symbols()
    print(f"Found {len(symbols)} symbols")

    all_signals = []

    for i, symbol in enumerate(symbols):
        if i % 50 == 0:
            print(f"Processing {i+1}/{len(symbols)}: {symbol}")

        signals = find_td_signals(symbol)
        all_signals.extend(signals)

    print(f"\nFound {len(all_signals)} total signals")

    if all_signals:
        df = pd.DataFrame(all_signals)
        # Calculate dollar volume and sort by it descending
        df['dollar_volume'] = df['close_price'] * df['volume']
        df = df.sort_values('dollar_volume', ascending=False)
        return df
    else:
        return pd.DataFrame(columns=['symbol', 'date', 'signal_type', 'signal_name',
                                     'close_price', 'bid_close', 'ask_close', 'volume'])


def main():
    import argparse

    parser = argparse.ArgumentParser(description='TD Sequential (神奇九转) Signal Scanner - Last Trading Day Only')
    parser.add_argument('--output-dir', type=str, default='reports',
                        help='Output directory for the CSV file (default: reports)')
    args = parser.parse_args()

    print("="*60)
    print("TD Sequential (神奇九转) Signal Scanner")
    print("Checking last trading day only")
    print("="*60)
    print()

    # Generate report
    results_df = generate_report()

    # Create output filename with date
    today = datetime.now().strftime('%Y-%m-%d')
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f'td_sequential_signals_{today}.csv')

    # Save to CSV
    results_df.to_csv(output_file, index=False)
    print(f"\nResults saved to: {output_file}")

    # Print summary
    if not results_df.empty:
        print("\n" + "="*60)
        print("SUMMARY - Signals for Trading Today")
        print("="*60)

        bullish_signals = results_df[results_df['signal_type'] == 'BULLISH']
        bearish_signals = results_df[results_df['signal_type'] == 'BEARISH']

        print(f"Total signals found: {len(results_df)}")
        print(f"Bullish signals (Buy Setup 9): {len(bullish_signals)}")
        print(f"Bearish signals (Sell Setup 9): {len(bearish_signals)}")

    else:
        print("\nNo TD Sequential signals found on the last trading day.")


if __name__ == "__main__":
    main()
