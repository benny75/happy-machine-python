from datetime import datetime, timedelta
from plot.chart_plotter import save_chart_to_file
import pytz

# Test parameters  
symbol = "A"  # AMD data with full symbol name
to_time = datetime.now(pytz.UTC)
from_time = to_time - timedelta(days=7)
timeframe = 15  # 15 minutes as integer

print(f"Testing chart plotting for {symbol}")
print(f"From: {from_time}")
print(f"To: {to_time}")
print(f"Timeframe: {timeframe}")

try:
    filename = save_chart_to_file(
        symbol=symbol,
        from_time=from_time,
        to_time=to_time,
        timeframe=timeframe,
        show_ema=True,
        show_rsi=True
    )
    print(f"Chart saved successfully to: {filename}")
except Exception as e:
    print(f"Error: {e}")