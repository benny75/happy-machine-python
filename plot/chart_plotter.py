import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional
import io
from data.TimescaleDBSticksDao import get_sticks


def calculate_ema(data: pd.Series, window: int) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return data.ewm(span=window, adjust=False).mean()


def calculate_rsi(data: pd.Series, window: int = 14) -> pd.Series:
    """Calculate Relative Strength Index"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def plot_chart(symbol: str, from_time: datetime, to_time: datetime, 
               timeframe: int, show_ema: bool = True, show_rsi: bool = True) -> bytes:
    """
    Plot a financial chart with optional EMA and RSI indicators
    
    Args:
        symbol: Stock/forex symbol
        from_time: Start datetime
        to_time: End datetime  
        timeframe: Time interval in minutes (e.g., 1, 5, 15, 60, 1440)
        show_ema: Whether to show EMA lines (20, 50, 150, 200)
        show_rsi: Whether to show RSI indicator
    
    Returns:
        bytes: PNG image data that can be used by MCP tools
    """
    
    # Fetch data using TimescaleDBSticksDao
    df = get_sticks(symbol, timeframe, from_time, to_time)
    
    if df.empty:
        raise ValueError(f"No data found for {symbol} in the specified time range")
    
    # Prepare OHLCV data for mplfinance
    # Use ask prices for the main chart
    ohlcv_data = pd.DataFrame({
        'Open': df['ask_open'],
        'High': df['ask_high'], 
        'Low': df['ask_low'],
        'Close': df['ask_close'],
        'Volume': df['volume']
    }, index=df.index)
    
    # Calculate indicators
    additional_plots = []
    
    if show_ema:
        # Calculate EMAs
        ema_20 = calculate_ema(ohlcv_data['Close'], 20)
        ema_50 = calculate_ema(ohlcv_data['Close'], 50)
        ema_150 = calculate_ema(ohlcv_data['Close'], 150)
        ema_200 = calculate_ema(ohlcv_data['Close'], 200)
        
        # Add EMA lines to additional plots
        additional_plots.extend([
            mpf.make_addplot(ema_20, color='blue', width=1, label='EMA 20'),
            mpf.make_addplot(ema_50, color='orange', width=1, label='EMA 50'), 
            mpf.make_addplot(ema_150, color='green', width=1, label='EMA 150'),
            mpf.make_addplot(ema_200, color='red', width=1, label='EMA 200')
        ])
    
    if show_rsi:
        # Calculate RSI
        rsi = calculate_rsi(ohlcv_data['Close'])
        
        # Add RSI as subplot
        additional_plots.append(
            mpf.make_addplot(rsi, panel=1, color='purple', secondary_y=False, ylabel='RSI')
        )
        
        # Add RSI reference lines (30 and 70)
        rsi_30 = pd.Series([30] * len(rsi), index=rsi.index)
        rsi_70 = pd.Series([70] * len(rsi), index=rsi.index)
        additional_plots.extend([
            mpf.make_addplot(rsi_30, panel=1, color='red', linestyle='--', width=0.5),
            mpf.make_addplot(rsi_70, panel=1, color='red', linestyle='--', width=0.5)
        ])
    
    # Create the plot style
    style = mpf.make_marketcolors(
        up='green', down='red',
        edge='inherit',
        wick={'up': 'green', 'down': 'red'},
        volume='in'
    )
    
    s = mpf.make_mpf_style(
        marketcolors=style,
        gridstyle='-',
        y_on_right=True
    )
    
    # Create figure with subplots if RSI is shown
    panel_ratios = (3, 1) if show_rsi else None
    
    # Save plot to bytes buffer
    buf = io.BytesIO()
    
    mpf.plot(
        ohlcv_data,
        type='candle',
        style=s,
        title=f'{symbol} - {timeframe}',
        ylabel='Price',
        volume=True,
        addplot=additional_plots if additional_plots else None,
        savefig=dict(fname=buf, format='png', bbox_inches='tight'),
        panel_ratios=panel_ratios,
        returnfig=False
    )
    
    buf.seek(0)
    image_bytes = buf.getvalue()
    buf.close()
    
    return image_bytes


def save_chart_to_file(symbol: str, from_time: datetime, to_time: datetime, 
                      timeframe: int, show_ema: bool = True, show_rsi: bool = True,
                      filename: Optional[str] = None) -> str:
    """
    Plot and save chart to file
    
    Returns:
        str: Path to saved file
    """
    image_bytes = plot_chart(symbol, from_time, to_time, timeframe, show_ema, show_rsi)
    
    if filename is None:
        filename = f"{symbol}_{timeframe}_{from_time.strftime('%Y%m%d')}_{to_time.strftime('%Y%m%d')}.png"
    
    with open(filename, 'wb') as f:
        f.write(image_bytes)
    
    return filename