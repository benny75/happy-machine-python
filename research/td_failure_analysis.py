import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.TimescaleDBSticksDao import get_sticks
from data.db_config import get_db_connection

def get_liquid_symbols(limit=50):
    """Get top liquid symbols to test"""
    connection = get_db_connection()
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        query = """
            SELECT symbol FROM stock_metadata 
            WHERE status = 'Active' AND dollar_volume > 500000000
            ORDER BY dollar_volume DESC LIMIT %s
        """
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
    connection.close()
    return [row['symbol'] for row in rows]

def calculate_td_sequential(df):
    """Calculate TD Setup 9"""
    close = df['close'].values
    buy_setup = np.zeros(len(df), dtype=int)
    sell_setup = np.zeros(len(df), dtype=int)
    
    b_count = 0
    s_count = 0
    
    for i in range(4, len(df)):
        if close[i] < close[i-4]:
            b_count += 1
            s_count = 0
        elif close[i] > close[i-4]:
            s_count += 1
            b_count = 0
        else:
            b_count = 0
            s_count = 0
            
        if b_count == 9:
            buy_setup[i] = 9
            b_count = 0 # Reset for simplicity in this specific test
        if s_count == 9:
            sell_setup[i] = 9
            s_count = 0
            
    df['td_buy'] = buy_setup
    df['td_sell'] = sell_setup
    return df

def analyze_failures():
    symbols = get_liquid_symbols(50)
    print(f"Analyzing 'Failed 9' moves for {len(symbols)} symbols...")
    
    results = []
    
    for symbol in symbols:
        try:
            # Get 2 years of daily data
            df = get_sticks(symbol, 1440, limit=700)
            if df.empty or len(df) < 50:
                continue
                
            df = df.sort_index()
            # Calculate close (mid)
            df['close'] = (df['bid_close'] + df['ask_close']) / 2
            df['high'] = (df['bid_high'] + df['ask_high']) / 2
            df['low'] = (df['bid_low'] + df['ask_low']) / 2
            
            df = calculate_td_sequential(df)
            
            # --- Analyze BUY SETUP 9 Failures (Bull Put Spread Risk) ---
            # Failure = Price closes BELOW the Low of the 9th bar within next 5 days
            buy_signals = df[df['td_buy'] == 9]
            
            for date, row in buy_signals.iterrows():
                idx = df.index.get_loc(date)
                if idx + 10 >= len(df): continue
                
                # The "Support" of the Setup 9 candle
                setup_low = row['low']
                
                # Check next 5 days for failure
                failed = False
                failure_idx = -1
                failure_price = 0
                
                for i in range(1, 6):
                    current_bar = df.iloc[idx + i]
                    if current_bar['close'] < setup_low:
                        failed = True
                        failure_idx = idx + i
                        failure_price = current_bar['close']
                        break
                
                if failed:
                    # Measure the "Waterfall" after failure
                    # Look at the NEXT 5 days after the failure occurred
                    post_fail_low = failure_price
                    for k in range(1, 6):
                        if failure_idx + k < len(df):
                            post_fail_low = min(post_fail_low, df.iloc[failure_idx + k]['low'])
                    
                    drop_pct = (post_fail_low - failure_price) / failure_price
                    results.append({
                        'type': 'BUY_FAIL',
                        'symbol': symbol,
                        'fail_date': df.index[failure_idx],
                        'move_pct': drop_pct * 100 # This will be negative
                    })

            # --- Analyze SELL SETUP 9 Failures (Bear Call Spread Risk) ---
            # Failure = Price closes ABOVE the High of the 9th bar
            sell_signals = df[df['td_sell'] == 9]
            
            for date, row in sell_signals.iterrows():
                idx = df.index.get_loc(date)
                if idx + 10 >= len(df): continue
                
                setup_high = row['high']
                
                failed = False
                failure_idx = -1
                failure_price = 0
                
                for i in range(1, 6):
                    current_bar = df.iloc[idx + i]
                    if current_bar['close'] > setup_high:
                        failed = True
                        failure_idx = idx + i
                        failure_price = current_bar['close']
                        break
                        
                if failed:
                    post_fail_high = failure_price
                    for k in range(1, 6):
                        if failure_idx + k < len(df):
                            post_fail_high = max(post_fail_high, df.iloc[failure_idx + k]['high'])
                            
                    rise_pct = (post_fail_high - failure_price) / failure_price
                    results.append({
                        'type': 'SELL_FAIL',
                        'symbol': symbol,
                        'fail_date': df.index[failure_idx],
                        'move_pct': rise_pct * 100 # This will be positive
                    })
                    
        except Exception as e:
            # print(f"Skipping {symbol}: {e}")
            pass

    # --- Summary ---
    res_df = pd.DataFrame(results)
    if res_df.empty:
        print("No failures found.")
        return

    print("\n" + "="*50)
    print("TD SETUP 9 FAILURE ANALYSIS (Hedge Validation)")
    print("="*50)
    
    # Buy Failures (We held Bull Put Spreads, Market crashed)
    buy_fails = res_df[res_df['type'] == 'BUY_FAIL']
    avg_drop = buy_fails['move_pct'].mean()
    median_drop = buy_fails['move_pct'].median()
    
    print(f"\nFAILED BUY SETUPS (Downside Breakout):")
    print(f"  Count: {len(buy_fails)}")
    print(f"  Avg Drop after Failure (5 Days): {avg_drop:.2f}%")
    print(f"  Median Drop: {median_drop:.2f}%")
    print(f"  Big Crash Probability (>5% drop): {len(buy_fails[buy_fails['move_pct'] < -5]) / len(buy_fails) * 100:.1f}%")

    # Sell Failures (We held Bear Call Spreads, Market melted up)
    sell_fails = res_df[res_df['type'] == 'SELL_FAIL']
    avg_rise = sell_fails['move_pct'].mean()
    median_rise = sell_fails['move_pct'].median()
    
    print(f"\nFAILED SELL SETUPS (Upside Breakout):")
    print(f"  Count: {len(sell_fails)}")
    print(f"  Avg Rise after Failure (5 Days): {avg_rise:.2f}%")
    print(f"  Median Rise: {median_rise:.2f}%")
    print(f"  Big Melt-up Probability (>5% rise): {len(sell_fails[sell_fails['move_pct'] > 5]) / len(sell_fails) * 100:.1f}%")
    
    print("\nCONCLUSION:")
    if abs(avg_drop) > 3 or avg_rise > 3:
        print("  STRONG HEDGE CANDIDATE.")
        print("  When the 9 Fails, the moves are large enough to generate")
        print("  significant profits on a Long Option hedge to offset spread losses.")
    else:
        print("  WEAK HEDGE. Post-failure moves are too small to pay for the hedge.")

if __name__ == "__main__":
    analyze_failures()
