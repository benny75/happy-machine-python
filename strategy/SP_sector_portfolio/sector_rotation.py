#!/usr/bin/env python3
"""
S&P 500 Sector Rotation Strategy - Core-Satellite Tilt

Objective: Beat SPY by holding a Core position in SPY and tilting towards momentum leaders,
           with a robust trend filter for downside protection.

Universe: All 11 SPDR Sector ETFs + SPY
Benchmarks: SPY

Strategy Logic (Monthly Rotation):
1.  **Ranking**: Rank Sectors by **3-month Momentum**.
2.  **Allocation** (Total 100%):
    -   **Core (50%)**: Allocated to **SPY**.
    -   **Satellite (50%)**: Allocated to **Top 2 Sectors** (25% each).
3.  **Trend Rules**:
    -   **If SPY > SMA200 (Bull)**:
        -   Core: Invest 50% in SPY.
        -   Satellite: Invest 50% in Top 2 Sectors.
    -   **If SPY < SMA200 (Bear)**:
        -   Core: Move to **CASH**.
        -   Satellite: Invest in Top 2 Sectors **ONLY IF** Sector Price > Sector SMA200. Else Cash.

Backtest Settings:
- Start Date: 2016-01-01
- Initial Capital: $10,000
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import warnings

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from data.TimescaleDBSticksDao import get_sticks
except ImportError:
    print("Could not import data.TimescaleDBSticksDao.")
    sys.exit(1)

warnings.filterwarnings('ignore')

# Configuration
SECTORS = ['XLK', 'XLY', 'XLC', 'XLF', 'XLI', 'XLB', 'XLP', 'XLU', 'XLV', 'XLRE', 'XLE']
BENCHMARK = 'SPY'
ALL_SYMBOLS = list(set(SECTORS + [BENCHMARK]))

INITIAL_CAPITAL = 10000.0
START_DATE = datetime(2015, 1, 1, tzinfo=pytz.UTC)
BACKTEST_START_DATE = datetime(2016, 1, 1, tzinfo=pytz.UTC)
RISK_FREE_RATE = 0.03

# Parameters
MOMENTUM_WINDOW = 63 # 3 months
SMA_WINDOW = 200
TOP_N = 2

def fetch_data(symbols, start_date):
    print(f"Fetching data for {len(symbols)} symbols starting from {start_date.date()}...")
    data = {}
    end_date = datetime.now(pytz.UTC)
    
    for symbol in symbols:
        try:
            df = get_sticks(symbol, 1440, start_date, end_date)
            if not df.empty:
                df['close'] = (df['bid_close'] + df['ask_close']) / 2
                df = df[~df.index.duplicated(keep='last')]
                data[symbol] = df['close']
            else:
                print(f"Warning: No data for {symbol}")
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")

    prices = pd.DataFrame(data)
    prices = prices.fillna(method='ffill') 
    prices = prices.dropna(how='all')
    return prices

def calculate_indicators(prices):
    print("Calculating technical indicators...")
    momentum = prices.pct_change(MOMENTUM_WINDOW)
    sma200 = prices.rolling(window=SMA_WINDOW).mean()
    return momentum, sma200

def get_rebalance_targets(date, prices, momentum, sma200):
    """
    Determine target weights.
    """
    day_mom = momentum.loc[date]
    day_sma = sma200.loc[date]
    day_prices = prices.loc[date]
    
    spy_price = day_prices[BENCHMARK]
    spy_sma_val = day_sma[BENCHMARK]
    
    spy_trend = spy_price > spy_sma_val
    regime = 'BULL' if spy_trend else 'BEAR'
    
    # Rank Sectors
    ranking = day_mom[SECTORS].dropna().sort_values(ascending=False)
    candidates = ranking.head(TOP_N).index.tolist()
    
    target_weights = {}
    
    # 1. Core Allocation (50%)
    if regime == 'BULL':
        target_weights[BENCHMARK] = 0.50
    else:
        # Bear Market: Core goes to Cash
        pass
        
    # 2. Satellite Allocation (50% -> 25% each)
    sat_weight = 0.25
    
    for sym in candidates:
        if regime == 'BULL':
            # In Bull, aggressive tilt
            target_weights[sym] = target_weights.get(sym, 0.0) + sat_weight
        else:
            # In Bear, safety check
            if day_prices[sym] > day_sma[sym]:
                target_weights[sym] = target_weights.get(sym, 0.0) + sat_weight
            else:
                # Cash
                pass
                
    return target_weights, regime, ranking

def backtest(prices, momentum, sma200):
    print(f"Running backtest from {BACKTEST_START_DATE.date()}...")
    
    sim_data = prices[prices.index >= BACKTEST_START_DATE].copy()
    if sim_data.empty: return None

    cash = INITIAL_CAPITAL
    holdings = {}
    portfolio_values = []
    current_month = None
    
    for date in sim_data.index:
        # Valuation
        daily_value = cash
        for sym, qty in holdings.items():
            if not np.isnan(sim_data.loc[date, sym]):
                daily_value += qty * sim_data.loc[date, sym]
        
        portfolio_values.append({
            'date': date,
            'value': daily_value,
            'cash': cash,
            'invested': daily_value - cash
        })

        # Rebalance
        if current_month != date.month:
            current_month = date.month
            
            target_weights, _, _ = get_rebalance_targets(date, prices, momentum, sma200)
            
            # Sell unwanted
            current_holdings = list(holdings.keys())
            for sym in current_holdings:
                if sym not in target_weights:
                    qty = holdings[sym]
                    price = sim_data.loc[date, sym]
                    proceeds = qty * price
                    cash += proceeds
                    del holdings[sym]
            
            # Rebalance/Buy
            total_equity = cash
            for sym, qty in holdings.items():
                total_equity += qty * sim_data.loc[date, sym]
            
            for sym, weight in target_weights.items():
                target_amt = total_equity * weight
                price = sim_data.loc[date, sym]
                if np.isnan(price): continue
                
                if sym in holdings:
                    current_val = holdings[sym] * price
                    diff = target_amt - current_val
                    qty_diff = diff / price
                    holdings[sym] += qty_diff
                    cash -= diff
                else:
                    qty = target_amt / price
                    holdings[sym] = qty
                    cash -= target_amt

    return pd.DataFrame(portfolio_values).set_index('date')

def calculate_max_drawdown(series):
    peak = series.cummax()
    drawdown = (series - peak) / peak
    return drawdown.min()

def evaluate_performance(portfolio, benchmark_prices):
    portfolio['returns'] = portfolio['value'].pct_change()
    
    benchmark = benchmark_prices.loc[portfolio.index]
    bench_returns = benchmark.pct_change()
    
    metrics_df = pd.DataFrame({
        'port_ret': portfolio['returns'],
        'bench_ret': bench_returns
    }).dropna()
    
    days = (portfolio.index[-1] - portfolio.index[0]).days
    years = days / 365.25 if days > 0 else 0
    
    port_total_ret = (portfolio['value'].iloc[-1] / portfolio['value'].iloc[0]) - 1
    bench_total_ret = (benchmark.iloc[-1] / benchmark.iloc[0]) - 1
    
    port_cagr = (portfolio['value'].iloc[-1] / portfolio['value'].iloc[0]) ** (1/years) - 1 if years > 0 else 0
    bench_cagr = (benchmark.iloc[-1] / benchmark.iloc[0]) ** (1/years) - 1 if years > 0 else 0
    
    port_vol = metrics_df['port_ret'].std() * np.sqrt(252)
    bench_vol = metrics_df['bench_ret'].std() * np.sqrt(252)
    
    port_sharpe = (port_cagr - RISK_FREE_RATE) / port_vol if port_vol > 0 else 0
    bench_sharpe = (bench_cagr - RISK_FREE_RATE) / bench_vol if bench_vol > 0 else 0
    
    covariance = np.cov(metrics_df['port_ret'], metrics_df['bench_ret'])[0][1]
    variance = np.var(metrics_df['bench_ret'])
    beta = covariance / variance if variance > 0 else 0
    alpha = port_cagr - (RISK_FREE_RATE + beta * (bench_cagr - RISK_FREE_RATE))
    
    port_mdd = calculate_max_drawdown(portfolio['value'])
    bench_mdd = calculate_max_drawdown(benchmark)
    
    print("\n" + "="*60)
    print("PERFORMANCE REPORT (vs SPY)")
    print("="*60)
    print(f"Period: {portfolio.index[0].date()} to {portfolio.index[-1].date()} ({years:.1f} years)")
    print("-" * 60)
    print(f"{ 'Metric':<20} | { 'Strategy':<15} | { 'SPY':<15} | { 'Diff/Val':<15}")
    print("-" * 60)
    print(f"{ 'Total Return':<20} | {port_total_ret*100:8.2f}%       | {bench_total_ret*100:8.2f}%       | {port_total_ret*100-bench_total_ret*100:8.2f}%")
    print(f"{ 'CAGR (Ann. Growth)':<20} | {port_cagr*100:8.2f}%       | {bench_cagr*100:8.2f}%       | {port_cagr*100-bench_cagr*100:8.2f}%")
    print(f"{ 'Volatility (Ann.)':<20} | {port_vol*100:8.2f}%       | {bench_vol*100:8.2f}%       | {(port_vol-bench_vol)*100:8.2f}%")
    print(f"{ 'Sharpe Ratio':<20} | {port_sharpe:8.2f}        | {bench_sharpe:8.2f}        | {port_sharpe-bench_sharpe:8.2f}")
    print(f"{ 'Max Drawdown':<20} | {port_mdd*100:8.2f}%       | {bench_mdd*100:8.2f}%       | {(port_mdd-bench_mdd)*100:8.2f}%")
    print("-" * 60)
    print(f"{ 'Beta':<20} | {beta:8.2f}        | {'1.00':<15} |")
    print(f"{ 'Alpha (Annualized)':<20} | {alpha*100:8.2f}%       | {'0.00%':<15} |")
    print("-" * 60)
    
    portfolio['year'] = portfolio.index.year
    annual_returns = portfolio.groupby('year')['returns'].apply(lambda x: (1 + x).prod() - 1)
    
    bench_df = pd.DataFrame({'price': benchmark, 'year': benchmark.index.year})
    bench_df['returns'] = bench_df['price'].pct_change()
    bench_annual = bench_df.groupby('year')['returns'].apply(lambda x: (1 + x).prod() - 1)
    
    print("\nAnnual Returns:")
    print(f"{ 'Year':<6} | { 'Strategy':<10} | { 'SPY':<10} | { 'Diff':<10}")
    print("-" * 46)
    
    for year in annual_returns.index:
        strat = annual_returns[year]
        bench = bench_annual.get(year, 0.0)
        diff = strat - bench
        print(f"{year:<6} | {strat*100:6.2f}%    | {bench*100:6.2f}%    | {diff*100:6.2f}%")
    print("-" * 50)

def main():
    print("Starting Core-Satellite (SPY + Top 2) Backtest...")
    
    prices = fetch_data(ALL_SYMBOLS, START_DATE)
    if prices.empty: return

    momentum, sma200 = calculate_indicators(prices)
    portfolio = backtest(prices, momentum, sma200)
    
    if portfolio is not None:
        evaluate_performance(portfolio, prices[BENCHMARK])
        
        output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backtest_results.csv')
        portfolio.to_csv(output_file)
        
        # Current Signal
        print("\n" + "="*50)
        print("CURRENT SIGNAL (For Tomorrow)")
        print("="*50)
        last_date = prices.index[-1]
        
        target_weights, regime, ranking = get_rebalance_targets(last_date, prices, momentum, sma200)
        
        day_sma = sma200.loc[last_date]
        print(f"SPY Price: {prices.loc[last_date, BENCHMARK]:.2f}")
        print(f"SPY SMA200: {day_sma[BENCHMARK]:.2f}")
        print(f"Market Regime: {regime}")
        
        print("\nSector Rankings (3-Month Mom):")
        print(ranking.head(5))
        
        print("\nRecommendation:")
        if not target_weights:
            print("100% CASH")
        else:
            for sym, weight in target_weights.items():
                print(f"- {sym}: {weight*100:.1f}% Allocation")

if __name__ == "__main__":
    main()
