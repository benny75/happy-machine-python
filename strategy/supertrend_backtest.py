#!/usr/bin/env python3
"""
Backtest for Supertrend Strategy
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

# Add the parent directory to the path so we can import from data module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.TimescaleDBSticksDao import get_sticks

def calculate_supertrend(df: pd.DataFrame, period=10, multiplier=3) -> pd.DataFrame:
    """
    Calculates Supertrend indicator and returns a dataframe with 'supertrend' and 'supertrend_direction' columns.
    """
    sticks = df.copy()
    high = sticks['ask_high'].values
    low = sticks['ask_low'].values
    close = sticks['ask_close'].values
    
    # Calculate ATR
    m = len(close)
    tr = np.zeros(m)
    # TR[0] is just high - low
    tr[0] = high[0] - low[0]
    
    for i in range(1, m):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        tr[i] = max(hl, hc, lc)
        
    # Calculate ATR using EWMA
    atr_series = pd.Series(tr).ewm(alpha=1/period, adjust=False).mean()
    atr = atr_series.values
    
    # Calculate Basic Upper and Lower Bands
    hl2 = (high + low) / 2
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)
    
    final_upper = np.zeros(m)
    final_lower = np.zeros(m)
    supertrend = np.zeros(m)
    
    # Initialize first values
    final_upper[0] = basic_upper[0]
    final_lower[0] = basic_lower[0]
    supertrend[0] = final_upper[0]
    
    for i in range(1, m):
        # Final Upper Band
        if basic_upper[i] < final_upper[i-1] or close[i-1] > final_upper[i-1]:
            final_upper[i] = basic_upper[i]
        else:
            final_upper[i] = final_upper[i-1]
            
        # Final Lower Band
        if basic_lower[i] > final_lower[i-1] or close[i-1] < final_lower[i-1]:
            final_lower[i] = basic_lower[i]
        else:
            final_lower[i] = final_lower[i-1]
            
        # Supertrend
        if supertrend[i-1] == final_upper[i-1]:
            if close[i] <= final_upper[i]:
                supertrend[i] = final_upper[i]
            else:
                supertrend[i] = final_lower[i]
        else:
            if close[i] >= final_lower[i]:
                supertrend[i] = final_lower[i]
            else:
                supertrend[i] = final_upper[i]
                
    sticks['supertrend'] = supertrend
    # 1 for Bullish (Price > Supertrend), -1 for Bearish (Price < Supertrend)
    sticks['supertrend_direction'] = np.where(close > supertrend, 1, -1)
    
    return sticks

def add_ema(df: pd.DataFrame, span=200) -> pd.DataFrame:
    df['ema200'] = df['ask_close'].ewm(span=span, adjust=False).mean()
    return df

def calculate_rsi(df: pd.DataFrame, period=14) -> pd.DataFrame:
    delta = df['ask_close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1+rs))
    return df

def calculate_adx(df: pd.DataFrame, period=14) -> pd.DataFrame:
    """Calculate Average Directional Index (ADX)"""
    high = df['ask_high']
    low = df['ask_low']
    close = df['ask_close']
    
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    frames = [tr1, tr2, tr3]
    tr = pd.concat(frames, axis=1, join='inner').max(axis=1)
    atr = tr.rolling(period).mean()
    
    plus_di = 100 * (plus_dm.ewm(alpha=1/period).mean() / atr)
    minus_di = 100 * (abs(minus_dm).ewm(alpha=1/period).mean() / atr)
    dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
    adx = ((dx.shift(1) * (period - 1)) + dx) / period
    adx_smooth = adx.ewm(alpha=1/period).mean()
    
    df['adx'] = adx_smooth
    df['atr'] = atr
    return df

class SupertrendBacktest:
    def __init__(self, symbols: list, start_date: datetime, end_date: datetime):
        self.symbols = symbols
        self.start_date = start_date
        self.end_date = end_date
        self.results = []
        # Removed fixed stop_loss_pct, using ATR based
        
    def simulate_symbol(self, symbol: str) -> list:
        try:
            warmup_days = 200
            fetch_start = self.start_date - timedelta(days=warmup_days * 2) 
            
            df = get_sticks(symbol, 1440, fetch_start, self.end_date)
            
            if df.empty or 'ask_high' not in df.columns or 'volume' not in df.columns:
                return []
                
            df = df.sort_index()
            if len(df) < warmup_days:
                return []
            
            # Simple Volume Filter: Average volume > 10,000
            if df['volume'].mean() < 10000:
                return []
            
            # Add Indicators
            df = calculate_supertrend(df, period=10, multiplier=3)
            df = add_ema(df, span=200)
            df = calculate_rsi(df, period=14)
            df = calculate_adx(df, period=14)
            
            # Filter for the requested simulation period
            sim_df = df[df.index >= self.start_date]
            
            if sim_df.empty:
                return []
                
            trades = []
            position = None
            
            start_idx = df.index.get_loc(sim_df.index[0])
            
            for i in range(start_idx, len(df)):
                curr_date = df.index[i]
                curr_row = df.iloc[i]
                prev_row = df.iloc[i-1]
                
                price = curr_row['ask_close']
                atr = curr_row['atr']
                adx = curr_row['adx']
                
                if price <= 0 or np.isnan(price) or np.isnan(atr) or np.isnan(adx): continue
                
                # Signals
                supertrend_bullish = (prev_row['supertrend_direction'] == -1) and (curr_row['supertrend_direction'] == 1)
                supertrend_bearish = (prev_row['supertrend_direction'] == 1) and (curr_row['supertrend_direction'] == -1)
                
                is_uptrend = price > curr_row['ema200']
                rsi_not_overbought = curr_row['rsi'] < 70
                strong_trend = adx > 25
                
                if position is None:
                    # Entry Condition: Supertrend Flip + EMA Trend + RSI not overbought + Strong Trend (ADX)
                    if supertrend_bullish and is_uptrend and rsi_not_overbought and strong_trend:
                        initial_stop_dist = 3 * atr
                        position = {
                            'symbol': symbol,
                            'entry_date': curr_date,
                            'entry_price': price,
                            'stop_loss': price - initial_stop_dist,
                            'initial_stop_dist': initial_stop_dist
                        }
                else:
                    # Update Trailing Stop
                    # Logic: If price moves up, move SL up. SL never moves down.
                    new_stop_candidate = price - (3 * atr)
                    if new_stop_candidate > position['stop_loss']:
                        position['stop_loss'] = new_stop_candidate
                    
                    # Exit Conditions
                    hit_stop_loss = price <= position['stop_loss']
                    
                    if supertrend_bearish or hit_stop_loss:
                        exit_reason = 'Stop Loss' if hit_stop_loss else 'Supertrend Bearish'
                        pnl = price - position['entry_price']
                        pnl_pct = (pnl / position['entry_price']) * 100
                        
                        trades.append({
                            'symbol': symbol,
                            'entry_date': position['entry_date'],
                            'exit_date': curr_date,
                            'entry_price': position['entry_price'],
                            'exit_price': price,
                            'pnl': pnl,
                            'pnl_pct': pnl_pct,
                            'reason': exit_reason,
                            'initial_stop_dist': position['initial_stop_dist']
                        })
                        position = None
            
            if position is not None:
                 price = df.iloc[-1]['ask_close']
                 pnl = price - position['entry_price']
                 pnl_pct = (pnl / position['entry_price']) * 100
                 trades.append({
                    'symbol': symbol,
                    'entry_date': position['entry_date'],
                    'exit_date': df.index[-1],
                    'entry_price': position['entry_price'],
                    'exit_price': price,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'reason': 'End of Backtest',
                    'initial_stop_dist': position['initial_stop_dist']
                })

            return trades
            
        except Exception as e:
            # Only print if it's not a common "empty data" error
            if "stick_datetime" not in str(e):
                print(f"Error processing {symbol}: {e}")
            return []

    def run_portfolio_simulation(self, initial_balance=1000):
        print(f"Collecting potential trades for {len(self.symbols)} symbols...")
        all_potential_trades = []
        for idx, symbol in enumerate(self.symbols):
            if idx % 50 == 0:
                print(f"Scanning symbol {idx}/{len(self.symbols)}...")
            trades = self.simulate_symbol(symbol)
            all_potential_trades.extend(trades)
            
        # Sort by entry date
        all_potential_trades.sort(key=lambda x: x['entry_date'])
        
        print(f"Found {len(all_potential_trades)} potential trades. Starting portfolio simulation...")
        
        cash = initial_balance
        open_positions = [] # List of dicts
        closed_trades = []
        equity_curve = []
        
        # Get the full date range for the simulation
        if not all_potential_trades:
            print("No trades found.")
            return pd.DataFrame()

        start_date = all_potential_trades[0]['entry_date']
        end_date = self.end_date
        
        current_date = start_date
        trade_idx = 0
        
        while current_date <= end_date:
            # 1. Process Exits (Market Close)
            for i in range(len(open_positions) - 1, -1, -1):
                pos = open_positions[i]
                if pos['exit_date'].date() <= current_date.date():
                    shares = pos['shares']
                    exit_value = shares * pos['exit_price']
                    cash += exit_value
                    
                    closed_trades.append({
                        'symbol': pos['symbol'],
                        'entry_date': pos['entry_date'],
                        'exit_date': pos['exit_date'],
                        'entry_price': pos['entry_price'],
                        'exit_price': pos['exit_price'],
                        'shares': shares,
                        'pnl': exit_value - pos['cost_basis'],
                        'pnl_pct': (exit_value - pos['cost_basis']) / pos['cost_basis'] * 100,
                        'reason': pos['reason']
                    })
                    
                    open_positions.pop(i)
            
            # 2. Process Entries (Market Open/During Day)
            while trade_idx < len(all_potential_trades):
                trade = all_potential_trades[trade_idx]
                if trade['entry_date'].date() > current_date.date():
                    break
                
                if trade['entry_date'].date() == current_date.date():
                    current_equity = cash + sum(p['cost_basis'] for p in open_positions)
                    
                    # Volatility Adjusted Position Sizing
                    # Risk = 1% of Equity
                    risk_amount = 0.01 * current_equity
                    stop_dist = trade['initial_stop_dist']
                    
                    if stop_dist > 0:
                        shares_by_risk = risk_amount / stop_dist
                        
                        # Cap max position size to 20% of equity
                        max_position_value = 0.20 * current_equity
                        shares_by_cap = max_position_value / trade['entry_price']
                        
                        shares = min(shares_by_risk, shares_by_cap)
                        cost = shares * trade['entry_price']
                        
                        if cash >= cost and shares > 0:
                            cash -= cost
                            open_positions.append({
                                'symbol': trade['symbol'],
                                'entry_date': trade['entry_date'],
                                'exit_date': trade['exit_date'],
                                'entry_price': trade['entry_price'],
                                'exit_price': trade['exit_price'],
                                'shares': shares,
                                'cost_basis': cost,
                                'reason': trade['reason']
                            })
                
                trade_idx += 1
            
            current_equity = cash + sum(p['cost_basis'] for p in open_positions)
            equity_curve.append({'date': current_date, 'equity': current_equity})
            
            current_date += timedelta(days=1)
            
        self.results = pd.DataFrame(closed_trades)
        self.equity_curve = pd.DataFrame(equity_curve)
        return self.results

    def run(self):
        # Legacy method wrapper
        return self.run_portfolio_simulation()

import matplotlib.pyplot as plt

def main():
    try:
        stocks_df = pd.read_csv('hot_stock/us_high_volume_stocks.csv')
        # Use more symbols for better statistical significance
        symbols = stocks_df['symbol'].head(200).tolist()
    except Exception as e:
        print(f"Could not load symbols: {e}")
        return

    end_date = datetime.now(pytz.UTC)
    start_date = end_date - timedelta(days=730) # 2 Years
    
    bt = SupertrendBacktest(symbols, start_date, end_date)
    results = bt.run_portfolio_simulation(initial_balance=1000)
    
    if not results.empty:
        final_equity = bt.equity_curve.iloc[-1]['equity']
        print("\n=== Portfolio Backtest Results (2 Years) ===")
        print(f"Initial Balance: $1000.00")
        print(f"Final Balance:   ${final_equity:.2f}")
        print(f"Total Return:    {((final_equity - 1000) / 1000 * 100):.2f}%")
        print(f"Total Trades:    {len(results)}")
        
        win_trades = results[results['pnl'] > 0]
        print(f"Win Rate:        {(len(win_trades) / len(results) * 100):.2f}%")
        
        print("\nExit Reasons:")
        print(results['reason'].value_counts())
        
        print("\nTop 5 Portfolio Winners:")
        print(results.sort_values('pnl', ascending=False).head(5)[['symbol', 'entry_date', 'exit_date', 'pnl', 'reason']])
        
        # Plot Equity Curve
        plt.figure(figsize=(12, 6))
        plt.plot(bt.equity_curve['date'], bt.equity_curve['equity'], label='Portfolio Equity')
        plt.title('Supertrend Strategy Equity Curve (2 Years)')
        plt.xlabel('Date')
        plt.ylabel('Equity ($)')
        plt.grid(True)
        plt.legend()
        
        plot_path = 'strategy/supertrend_equity_curve.png'
        plt.savefig(plot_path)
        print(f"\nEquity curve plot saved to: {plot_path}")
        
        # Save results
        results.to_csv('strategy/supertrend_portfolio_trades.csv', index=False)
        bt.equity_curve.to_csv('strategy/supertrend_portfolio_equity.csv', index=False)
        print("Results saved to strategy/supertrend_portfolio_trades.csv and strategy/supertrend_portfolio_equity.csv")
    else:
        print("No trades executed.")

if __name__ == "__main__":
    main()
