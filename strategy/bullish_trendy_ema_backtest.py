#!/usr/bin/env python3
"""
Backtest for Bullish TrendyEMA signals
Processes files with number prefixes (e.g., "70-", "100-") from /Users/benny/git/happy-machine-report/2025-06-13/usBatch/bullishTrendyEMA/
Simulates opening positions on 2025-06-13 with risk management
Each position is normalized to $1000 investment value for fair comparison across symbols

File Pattern: Uses regex to match files like "70-SYMBOL.jpg" or "100-SYMBOL.jpg"
Extracts symbol by removing number prefix and .jpg suffix

Risk Management:
- Take profit: 7.5% gain
- Stop loss: 5% loss
- Maximum holding period: 14 days
- Daily monitoring for early exit conditions

Price Logic:
- Entry: Uses ask price (buy at ask)
- Exit: Uses bid price (sell at bid)
- If ask/bid is zero, uses the alternative price as fallback
- Tracks which price type was used for transparency
"""

import os
import sys
import pandas as pd
import re
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Tuple, Optional

# Add the parent directory to the path so we can import from data module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.TimescaleDBSticksDao import get_sticks


class BullishTrendyEMABacktest:
    def __init__(self, signals_folder: str):
        self.signals_folder = signals_folder
        self.start_date = datetime(2025, 6, 13, tzinfo=pytz.UTC)
        self.end_date = self.start_date + timedelta(days=14)
        self.take_profit_pct = 7.5   # 7.5% take profit
        self.stop_loss_pct = 5.0     # 5% stop loss
        self.results = []
        
    def extract_symbol_from_filename(self, filename: str) -> str:
        """Extract symbol from filename like '70-AC.D.2800HK.DAILY.IP.jpg' or '100-AC.D.2800HK.DAILY.IP.jpg' -> 'AC.D.2800HK.DAILY.IP'"""
        # Use regex to match pattern: number-symbol.jpg
        # Pattern: start with one or more digits, followed by dash, then symbol, ending with .jpg
        pattern = r'^(\d+)-(.+)\.jpg$'
        match = re.match(pattern, filename)
        
        if not match:
            return None
        
        # Extract the symbol part (group 2)
        symbol = match.group(2)
        
        # Return None if symbol is empty (e.g., "70-.jpg")
        if not symbol:
            return None
            
        return symbol
    
    def get_bullish_signals(self) -> List[str]:
        """Get all symbols from files with number prefix (e.g., '70-', '100-') and .jpg extension"""
        symbols = []
        
        if not os.path.exists(self.signals_folder):
            print(f"Error: Signals folder {self.signals_folder} does not exist")
            return symbols
        
        files = os.listdir(self.signals_folder)
        # Use regex to find files matching pattern: number-*.jpg
        pattern = r'^\d+-.*\.jpg$'
        bullish_files = [f for f in files if re.match(pattern, f)]
        
        print(f"Found {len(bullish_files)} bullish signal files")
        
        for filename in bullish_files:
            symbol = self.extract_symbol_from_filename(filename)
            if symbol:
                symbols.append(symbol)
        
        return symbols
    
    def simulate_trade(self, symbol: str) -> Dict:
        """Simulate a 14-day trade for a given symbol.
        Uses ask price for entry and bid price for exit.
        If ask/bid is zero, uses the alternative price instead.
        """
        try:
            # Get price data from start date to end date (1440 minutes = 1 day)
            sticks_df = get_sticks(symbol, 1440, self.start_date, self.end_date)
            
            if sticks_df.empty:
                return {
                    'symbol': symbol,
                    'status': 'NO_DATA',
                    'entry_price': None,
                    'exit_price': None,
                    'pnl': None,
                    'pnl_pct': None,
                    'days_held': None,
                    'error': 'No data available for the specified date range'
                }
            
            # Entry: Buy at ask price on the first available day (should be 2025-06-13 or close to it)
            entry_row = sticks_df.iloc[0]
            entry_price = entry_row['ask_close']  # Use ask_close for entry
            entry_price_note = "ask"
            
            # If ask price is zero, use bid price instead
            if entry_price == 0:
                entry_price = entry_row['bid_close']
                entry_price_note = "bid_fallback"
                if entry_price == 0:
                    return {
                        'symbol': symbol,
                        'status': 'ERROR',
                        'entry_price': None,
                        'exit_price': None,
                        'pnl': None,
                        'pnl_pct': None,
                        'days_held': None,
                        'error': 'Both ask and bid prices are zero at entry'
                    }
            
            entry_date = sticks_df.index[0]
            
            # Calculate position size for $1000 investment
            position_size = 1000.0 / entry_price
            
            # Check daily for take profit/stop loss conditions
            exit_row = None
            exit_date = None
            exit_reason = "time_limit"
            
            # Loop through each day to check for early exit conditions
            for i in range(1, len(sticks_df)):
                current_row = sticks_df.iloc[i]
                current_date = sticks_df.index[i]
                
                # Get current price (use bid for exit simulation)
                current_price = current_row['bid_close']
                if current_price == 0:
                    current_price = current_row['ask_close']
                
                # Skip if current price is still zero
                if current_price == 0:
                    continue
                
                # Calculate current P&L percentage
                current_pnl_pct = ((current_price - entry_price) / entry_price) * 100
                
                # Check take profit condition
                if current_pnl_pct >= self.take_profit_pct:
                    exit_row = current_row
                    exit_date = current_date
                    exit_reason = "take_profit"
                    break
                
                # Check stop loss condition
                if current_pnl_pct <= -self.stop_loss_pct:
                    exit_row = current_row
                    exit_date = current_date
                    exit_reason = "stop_loss"
                    break
            
            # If no early exit, use the last available day (time limit)
            if exit_row is None:
                if len(sticks_df) >= 14:
                    exit_row = sticks_df.iloc[13]  # 14th day (0-indexed)
                    exit_date = sticks_df.index[13]
                else:
                    # Use the last available day if less than 14 days of data
                    exit_row = sticks_df.iloc[-1]
                    exit_date = sticks_df.index[-1]
                exit_reason = "time_limit"
            
            # Final exit price calculation
            exit_price = exit_row['bid_close']  # Use bid_close for exit
            exit_price_note = "bid"
            
            # If bid price is zero, use ask price instead
            if exit_price == 0:
                exit_price = exit_row['ask_close']
                exit_price_note = "ask_fallback"
                if exit_price == 0:
                    return {
                        'symbol': symbol,
                        'status': 'ERROR',
                        'entry_price': None,
                        'exit_price': None,
                        'pnl': None,
                        'pnl_pct': None,
                        'days_held': None,
                        'error': 'Both bid and ask prices are zero at exit'
                    }
            
            # Calculate P&L based on normalized $1000 position
            pnl = (exit_price - entry_price) * position_size
            pnl_pct = (pnl / 1000.0) * 100  # P&L percentage based on $1000 investment
            
            days_held = (exit_date - entry_date).days
            
            return {
                'symbol': symbol,
                'status': 'SUCCESS',
                'entry_date': entry_date,
                'exit_date': exit_date,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'entry_price_type': entry_price_note,
                'exit_price_type': exit_price_note,
                'position_size': position_size,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'days_held': days_held,
                'exit_reason': exit_reason,
                'error': None
            }
            
        except Exception as e:
            return {
                'symbol': symbol,
                'status': 'ERROR',
                'entry_price': None,
                'exit_price': None,
                'pnl': None,
                'pnl_pct': None,
                'days_held': None,
                'error': str(e)
            }
    
    def run_backtest(self) -> pd.DataFrame:
        """Run the backtest on all bullish signals with normalized $1000 position sizes and risk management"""
        print(f"Starting backtest for period: {self.start_date.date()} to {self.end_date.date()}")
        print(f"Using normalized $1000 position size per trade")
        print(f"Risk management: Take profit {self.take_profit_pct}%, Stop loss {self.stop_loss_pct}%")
        
        symbols = self.get_bullish_signals()
        print(f"Processing {len(symbols)} symbols...")
        
        results = []
        successful_trades = 0
        
        for i, symbol in enumerate(symbols):
            if i % 10 == 0:
                print(f"Processing symbol {i+1}/{len(symbols)}: {symbol}")
            
            result = self.simulate_trade(symbol)
            results.append(result)
            
            if result['status'] == 'SUCCESS':
                successful_trades += 1
            elif i < 5:  # Show first 5 errors for debugging
                print(f"  Error for {symbol}: {result['error']}")
        
        print(f"\nBacktest completed!")
        print(f"Total symbols processed: {len(symbols)}")
        print(f"Successful trades: {successful_trades}")
        print(f"Failed trades: {len(symbols) - successful_trades}")
        
        self.results = results
        return pd.DataFrame(results)
    
    def analyze_results(self, results_df: pd.DataFrame) -> Dict:
        """Analyze backtest results and provide summary statistics"""
        successful_trades = results_df[results_df['status'] == 'SUCCESS']
        
        if successful_trades.empty:
            return {
                'total_trades': len(results_df),
                'successful_trades': 0,
                'failed_trades': len(results_df),
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_pnl': 0,
                'avg_pnl_pct': 0,
                'total_pnl': 0,
                'best_trade': None,
                'worst_trade': None,
                'median_pnl_pct': 0,
                'std_pnl_pct': 0
            }
        
        winning_trades = successful_trades[successful_trades['pnl'] > 0]
        losing_trades = successful_trades[successful_trades['pnl'] < 0]
        
        analysis = {
            'total_trades': len(results_df),
            'successful_trades': len(successful_trades),
            'failed_trades': len(results_df) - len(successful_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(successful_trades) * 100 if len(successful_trades) > 0 else 0,
            'avg_pnl': successful_trades['pnl'].mean(),
            'avg_pnl_pct': successful_trades['pnl_pct'].mean(),
            'total_pnl': successful_trades['pnl'].sum(),
            'best_trade': successful_trades.loc[successful_trades['pnl'].idxmax()] if not successful_trades.empty else None,
            'worst_trade': successful_trades.loc[successful_trades['pnl'].idxmin()] if not successful_trades.empty else None,
            'median_pnl_pct': successful_trades['pnl_pct'].median(),
            'std_pnl_pct': successful_trades['pnl_pct'].std()
        }
        
        return analysis


def main():
    # Path to the bullish signals folder
    signals_folder = "/Users/benny/git/happy-machine-report/2025-06-13/usBatch/bullishTrendyEMA"
    
    # Create backtest instance
    backtest = BullishTrendyEMABacktest(signals_folder)
    
    # Run backtest
    results_df = backtest.run_backtest()
    
    # Analyze results
    analysis = backtest.analyze_results(results_df)
    
    # Print summary
    print("\n" + "="*60)
    print("BACKTEST RESULTS SUMMARY")
    print("(Normalized to $1000 position size per trade)")
    print("(Risk Management: 7.5% Take Profit, 5% Stop Loss)")
    print("="*60)
    print(f"Total trades: {analysis['total_trades']}")
    print(f"Successful trades: {analysis['successful_trades']}")
    print(f"Failed trades: {analysis['failed_trades']}")
    print(f"Winning trades: {analysis['winning_trades']}")
    print(f"Losing trades: {analysis['losing_trades']}")
    print(f"Win rate: {analysis['win_rate']:.2f}%")
    print(f"Average P&L: ${analysis['avg_pnl']:.2f}")
    print(f"Average P&L %: {analysis['avg_pnl_pct']:.2f}%")
    print(f"Median P&L %: {analysis['median_pnl_pct']:.2f}%")
    print(f"Std Dev P&L %: {analysis['std_pnl_pct']:.2f}%")
    print(f"Total P&L: ${analysis['total_pnl']:.2f}")
    
    if analysis['best_trade'] is not None:
        print(f"\nBest trade:")
        print(f"  Symbol: {analysis['best_trade']['symbol']}")
        print(f"  P&L: ${analysis['best_trade']['pnl']:.2f} ({analysis['best_trade']['pnl_pct']:.2f}%)")
        
    if analysis['worst_trade'] is not None:
        print(f"\nWorst trade:")
        print(f"  Symbol: {analysis['worst_trade']['symbol']}")
        print(f"  P&L: ${analysis['worst_trade']['pnl']:.2f} ({analysis['worst_trade']['pnl_pct']:.2f}%)")
    
    # Save detailed results to CSV
    output_file = "strategy/bullish_trendy_ema_backtest_results.csv"
    results_df.to_csv(output_file, index=False)
    print(f"\nDetailed results saved to: {output_file}")
    
    # Show sample of successful trades
    successful_trades = results_df[results_df['status'] == 'SUCCESS']
    if not successful_trades.empty:
        print(f"\nSample of successful trades:")
        print(successful_trades[['symbol', 'entry_price', 'exit_price', 'pnl', 'pnl_pct', 'days_held', 'exit_reason']].head(10).to_string(index=False))
        
        # Show fallback price usage statistics
        entry_fallbacks = successful_trades[successful_trades['entry_price_type'] == 'bid_fallback']
        exit_fallbacks = successful_trades[successful_trades['exit_price_type'] == 'ask_fallback']
        print(f"\nPrice fallback usage:")
        print(f"Entry price fallbacks (used bid instead of ask): {len(entry_fallbacks)}")
        print(f"Exit price fallbacks (used ask instead of bid): {len(exit_fallbacks)}")
        if len(entry_fallbacks) > 0:
            print(f"Entry fallback symbols: {entry_fallbacks['symbol'].tolist()}")
        if len(exit_fallbacks) > 0:
            print(f"Exit fallback symbols: {exit_fallbacks['symbol'].tolist()}")
        
        # Show exit reason statistics
        take_profit_trades = successful_trades[successful_trades['exit_reason'] == 'take_profit']
        stop_loss_trades = successful_trades[successful_trades['exit_reason'] == 'stop_loss']
        time_limit_trades = successful_trades[successful_trades['exit_reason'] == 'time_limit']
        print(f"\nExit reason statistics:")
        print(f"Take profit exits (7.5%): {len(take_profit_trades)} ({len(take_profit_trades)/len(successful_trades)*100:.1f}%)")
        print(f"Stop loss exits (5%): {len(stop_loss_trades)} ({len(stop_loss_trades)/len(successful_trades)*100:.1f}%)")
        print(f"Time limit exits (14 days): {len(time_limit_trades)} ({len(time_limit_trades)/len(successful_trades)*100:.1f}%)")
        if len(take_profit_trades) > 0:
            print(f"Average days to take profit: {take_profit_trades['days_held'].mean():.1f}")
        if len(stop_loss_trades) > 0:
            print(f"Average days to stop loss: {stop_loss_trades['days_held'].mean():.1f}")
    
    # Show failed trades
    failed_trades = results_df[results_df['status'] != 'SUCCESS']
    if not failed_trades.empty:
        print(f"\nFailed trades ({len(failed_trades)} total):")
        print(failed_trades[['symbol', 'status', 'error']].head(10).to_string(index=False))


if __name__ == "__main__":
    main() 