# happy-machine-python

## Option Pricing

To calculate the theoretical price of an option using Black-Scholes and fetch market data from Interactive Brokers (IBKR), use the `options/ib_calculator.py` script.

**Prerequisites:**
- Ensure IBKR TWS or Gateway is running and accepting API connections (default port 7496 or 4001).
- Python environment set up in `.venv`.

**Usage:**
```bash
.venv/bin/python options/ib_calculator.py <SYMBOL> <STRIKE> <EXPIRATION> <RIGHT> [PORT]
```

- `SYMBOL`: Ticker symbol (e.g., SPY, AAPL)
- `STRIKE`: Strike price (e.g., 400)
- `EXPIRATION`: Expiration date in YYYYMMDD format (e.g., 20231215)
- `RIGHT`: 'C' for Call or 'P' for Put
- `PORT`: (Optional) IBKR API port, defaults to 7496

**Example:**
```bash
.venv/bin/python options/ib_calculator.py SPY 450 20251220 C
```