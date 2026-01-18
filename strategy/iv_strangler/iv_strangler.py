import json
import os
import sys
import logging
from datetime import datetime, date
import pandas as pd

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from options.iv_rank import get_iv_rank

STATE_FILE = os.path.join(os.path.dirname(__file__), 'trades.json')
logger = logging.getLogger("IVStranglerManager")

class IVStrangler:
    def __init__(self):
        self.trades = self.load_trades()
        self.capital = 100000 # Default, should be configurable or fetched
        self.allocation_per_trade = 0.05 # 5% per trade (Quarter-Kelly approx)

    def load_trades(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return []
        return []

    def save_trades(self):
        with open(STATE_FILE, 'w') as f:
            json.dump(self.trades, f, indent=2, default=str)

    def check_market_regime(self):
        """
        Checks VIX Term structure.
        Returns 'contango', 'backwardation', or 'unknown'.
        """
        # TODO: Implement VIX Futures check using IB or other data source.
        # For now, we will assume Contango (Normal) or ask user?
        # A simple proxy might be VIX vs VIX3M if available via yfinance, 
        # but IBKR is better for /VX futures.
        
        logger.warning("VIX Term Structure check not fully implemented. Assuming Contango.")
        return 'contango'

    def get_symbol_iv_rank(self, symbol):
        data = get_iv_rank(symbol)
        logger.debug(f"get_iv_rank({symbol}) returned: {data}")
        if "iv_rank" in data:
            return data["iv_rank"]
        return 0

    def scan_for_entry(self, symbol="SPX"):
        """
        Scans for potential entry for the given symbol.
        Criteria:
        - Market in Contango
        - IV Rank > 30
        - 45 DTE
        """
        regime = self.check_market_regime()
        if regime == 'backwardation':
            return {"action": "WAIT", "reason": "Market in Backwardation (Panic)"}

        rank = self.get_symbol_iv_rank(symbol)
        if rank < 30:
            return {"action": "WAIT", "reason": f"IV Rank {rank} < 30"}

        # If we passed filters, we look for strikes
        # This requires an active connection to get the option chain
        return {
            "action": "ENTER",
            "symbol": symbol,
            "iv_rank": rank,
            "target_dte": 45,
            "target_delta": 16,
            "reason": "Conditions met"
        }

    def check_active_positions(self):
        """
        Iterate through active trades and check for exit/adjust signals.
        - Profit > 50%
        - DTE <= 21
        - Tested sides
        """
        updates = []
        for trade in self.trades:
            if trade.get('status') != 'OPEN':
                continue

            # Mocking current data for logic demonstration
            # In reality, we need to fetch current option prices for the specific strikes
            
            entry_date = datetime.strptime(trade['entry_date'], "%Y-%m-%d").date()
            days_held = (date.today() - entry_date).days
            
            # TODO: Calculate current profit/loss and DTE
            
            updates.append({
                "trade_id": trade['id'],
                "symbol": trade['symbol'],
                "days_held": days_held,
                "msg": "Monitoring..."
            })
            
        return updates

    def add_trade(self, trade_data):
        trade_data['id'] = len(self.trades) + 1
        trade_data['entry_date'] = str(date.today())
        trade_data['status'] = 'OPEN'
        self.trades.append(trade_data)
        self.save_trades()
        logger.info(f"Trade {trade_data['id']} added.")

if __name__ == "__main__":
    strategy = IVStrangler()
    
    # 1. Check for new entries
    print("--- Scanning for Entries ---")
    entry_signal = strategy.scan_for_entry("SPX")
    print(f"SPX Signal: {entry_signal}")

    # 2. Monitor existing
    print("\n--- Monitoring Positions ---")
    updates = strategy.check_active_positions()
    for u in updates:
        print(u)
