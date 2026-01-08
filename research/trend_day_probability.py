import pandas as pd
import numpy as np
from datetime import datetime, time
import pytz
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.TimescaleDBSticksDao import get_sticks

def analyze_trend_days():
    symbol = "SI.D.SPY.DAILY.IP"
    interval = 1 # 1-minute data
    
    print(f"Fetching 1-minute data for {symbol}...")
    df = get_sticks(symbol, interval)
    if df.empty:
        print("No data found.")
        return

    # Prepare Data
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df = df.tz_convert('US/Eastern')
    df['price'] = (df['bid_close'] + df['ask_close']) / 2
    df['date'] = df.index.date
    df['time'] = df.index.time
    
    dates = df['date'].unique()
    print(f"Analyzing {len(dates)} trading days...")
    
    # Thresholds
    FIRST_HOUR_THRESHOLD = 0.005  # 0.5% move in first hour
    
    trend_stats = {
        'total_days': 0,
        'trend_days_detected': 0,
        'continuation_up': 0,
        'continuation_down': 0,
        'reversal': 0,
        'chopp_continuation': 0
    }
    
    results = []

    for d in dates:
        day_data = df[df['date'] == d]
        
        # Define Time Windows
        market_open = time(9, 30)
        one_hour_mark = time(10, 30)
        market_close = time(15, 55)
        
        open_data = day_data[day_data['time'] >= market_open]
        hour_data = day_data[day_data['time'] <= one_hour_mark]
        rest_of_day = day_data[(day_data['time'] > one_hour_mark) & (day_data['time'] <= market_close)]
        
        if open_data.empty or hour_data.empty or rest_of_day.empty:
            continue
            
        open_price = open_data.iloc[0]['price']
        hour_price = hour_data.iloc[-1]['price']
        close_price = rest_of_day.iloc[-1]['price']
        
        # Calculate First Hour Move
        first_hour_return = (hour_price - open_price) / open_price
        
        # Check for Trend Day signature (Large move in first hour)
        if abs(first_hour_return) >= FIRST_HOUR_THRESHOLD:
            trend_stats['trend_days_detected'] += 1
            
            # Calculate Continuation (Rest of Day Return)
            rest_of_day_return = (close_price - hour_price) / hour_price
            
            result = {
                'date': d,
                'first_hour_dir': 'UP' if first_hour_return > 0 else 'DOWN',
                'first_hour_pct': first_hour_return * 100,
                'rest_of_day_pct': rest_of_day_return * 100,
                'outcome': 'NEUTRAL'
            }
            
            # Did the trend continue?
            if first_hour_return > 0: # Bullish Open
                if rest_of_day_return > 0.001: # Continued Up
                    trend_stats['continuation_up'] += 1
                    result['outcome'] = 'CONTINUATION'
                elif rest_of_day_return < -0.001: # Reversed
                    trend_stats['reversal'] += 1
                    result['outcome'] = 'REVERSAL'
                else:
                    trend_stats['chopp_continuation'] += 1
                    
            else: # Bearish Open
                if rest_of_day_return < -0.001: # Continued Down
                    trend_stats['continuation_down'] += 1
                    result['outcome'] = 'CONTINUATION'
                elif rest_of_day_return > 0.001: # Reversed
                    trend_stats['reversal'] += 1
                    result['outcome'] = 'REVERSAL'
                else:
                    trend_stats['chopp_continuation'] += 1
            
            results.append(result)
            
        trend_stats['total_days'] += 1

    # Analysis
    print("\n" + "="*50)
    print("TREND DAY ANALYSIS (Hedge Feasibility)")
    print("="*50)
    print(f"Total Days Analyzed: {trend_stats['total_days']}")
    print(f"Trend Days Detected (>0.5% in 1st Hour): {trend_stats['trend_days_detected']}")
    
    if trend_stats['trend_days_detected'] > 0:
        continuations = trend_stats['continuation_up'] + trend_stats['continuation_down']
        cont_rate = (continuations / trend_stats['trend_days_detected']) * 100
        rev_rate = (trend_stats['reversal'] / trend_stats['trend_days_detected']) * 100
        chop_rate = (trend_stats['chopp_continuation'] / trend_stats['trend_days_detected']) * 100
        
        print(f"\nWhen the market moves >0.5% in the first hour:")
        print(f"  - Trend Continues (Hedge Pays): {cont_rate:.2f}%")
        print(f"  - Trend Reverses (Hedge Loses): {rev_rate:.2f}%")
        print(f"  - Market Stalls (Hedge Bleeds): {chop_rate:.2f}%")
        
        print("\nConclusion:")
        if cont_rate > 50:
            print("  STRONG EDGE found. Buying momentum after a volatile open")
            print("  is a statistically sound hedge for Short Vol strategies.")
        else:
            print("  WEAK EDGE. Chasing the first hour move is coin-flip.")
            print("  Better to look for Mean Reversion or options structures.")
            
    print("="*50)

if __name__ == "__main__":
    analyze_trend_days()
