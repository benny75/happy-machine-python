import pandas as pd
import numpy as np
from datetime import datetime, time
import pytz
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.TimescaleDBSticksDao import get_sticks

def run_backtest():
    symbol = "SI.D.SPY.DAILY.IP"
    interval = 1 # 1-minute data
    
    print(f"Fetching 1-minute data for {symbol}...")
    # Fetch all available data
    df = get_sticks(symbol, interval)
    if df.empty:
        print("No data found.")
        return

    # Ensure index is datetime and localized to UTC, then convert to US/Eastern
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df = df.tz_convert('US/Eastern')
    
    # Calculate mid price
    df['price'] = (df['bid_close'] + df['ask_close']) / 2
    
    # Extract date and time
    df['date'] = df.index.date
    df['time'] = df.index.time
    
    dates = df['date'].unique()
    print(f"Analyzing {len(dates)} trading days...")
    
    results = []
    
    # Strategy Parameters
    ENTRY_TIME = time(10, 0)
    EXIT_TIME = time(15, 55)
    STRIKE_DISTANCE_PCT = 0.015  # 1.5% OTM
    CREDIT_COLLECTED = 0.40      # $0.40 per spread (Premium is lower for further OTM)
    STOP_LOSS_MULT = 3.0        # 3x Stop Loss
    STOP_LOSS_VAL = CREDIT_COLLECTED * STOP_LOSS_MULT
    
    for d in dates:
        day_data = df[df['date'] == d]
        
        # 1. Entry
        entry_candidates = day_data[day_data['time'] >= ENTRY_TIME]
        if entry_candidates.empty:
            continue
            
        entry_row = entry_candidates.iloc[0]
        entry_price = entry_row['price']
        
        upper_strike = entry_price * (1 + STRIKE_DISTANCE_PCT)
        lower_strike = entry_price * (1 - STRIKE_DISTANCE_PCT)
        
        # 2. Monitoring (Intraday)
        # We check every minute from entry until market close
        monitoring_data = day_data[day_data.index > entry_row.name]
        
        day_result = {
            'date': d,
            'entry_price': entry_price,
            'upper_strike': upper_strike,
            'lower_strike': lower_strike,
            'status': 'WIN',
            'pnl': CREDIT_COLLECTED,
            'exit_time': EXIT_TIME,
            'exit_reason': 'Expiration'
        }
        
        for idx, row in monitoring_data.iterrows():
            current_high = (row['bid_high'] + row['ask_high']) / 2
            current_low = (row['bid_low'] + row['ask_low']) / 2
            
            # Simplified Stop Loss: 
            # In a real option, hitting the strike doesn't mean a 3x loss immediately.
            # However, if it moves 1% against us (touching strike), the 0DTE delta 
            # and gamma would likely push the premium to the stop loss level.
            if current_high >= upper_strike or current_low <= lower_strike:
                day_result['status'] = 'LOSS'
                day_result['pnl'] = -STOP_LOSS_VAL
                day_result['exit_time'] = row['time']
                day_result['exit_reason'] = 'Stop Loss Hit'
                break
            
            # End of day check
            if row['time'] >= EXIT_TIME:
                break
                
        results.append(day_result)
    
    # 3. Summary Statistics
    results_df = pd.DataFrame(results)
    if results_df.empty:
        print("No trades executed.")
        return

    total_trades = len(results_df)
    wins = len(results_df[results_df['status'] == 'WIN'])
    losses = len(results_df[results_df['status'] == 'LOSS'])
    win_rate = (wins / total_trades) * 100
    total_pnl = results_df['pnl'].sum()
    
    print("\n" + "="*40)
    print("0DTE INTRADAY STRANGLE BACKTEST")
    print("="*40)
    print(f"Period:         {dates[0]} to {dates[-1]}")
    print(f"Total Trades:   {total_trades}")
    print(f"Wins:           {wins}")
    print(f"Losses:         {losses}")
    print(f"Win Rate:       {win_rate:.2f}%")
    print(f"Avg PnL/Trade:  ${results_df['pnl'].mean():.2f}")
    print(f"Total PnL:      ${total_pnl:.2f} (per 1 contract)")
    print("-" * 40)
    
    # Drawdown calculation
    results_df['cum_pnl'] = results_df['pnl'].cumsum()
    results_df['max_cum_pnl'] = results_df['cum_pnl'].cummax()
    results_df['drawdown'] = results_df['cum_pnl'] - results_df['max_cum_pnl']
    max_drawdown = results_df['drawdown'].min()
    
    print(f"Max Drawdown:   ${max_drawdown:.2f}")
    print("="*40)

if __name__ == "__main__":
    run_backtest()
