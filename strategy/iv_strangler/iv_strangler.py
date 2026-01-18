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
        - IV Rank > 30
        - 45 DTE
        """
        signals = []
        
        # 1. CORE STRATEGY (Iron Condor)
        rank = self.get_symbol_iv_rank(symbol)
        if rank < 30:
            signals.append({"type": "STRATEGY", "action": "WAIT", "reason": f"IV Rank {rank:.2f} < 30"})
        else:
            signals.append({
                "type": "STRATEGY",
                "action": "ENTER",
                "symbol": symbol,
                "iv_rank": rank,
                "target_dte": 45,
                "target_delta": 16,
                "reason": "Conditions met"
            })
        
        return signals

    def check_active_positions(self, current_market_data=None):
        """
        Iterate through active trades and check for exit/adjust signals.
        - Crash Protection (Backwardation)
        - Profit > 50%
        - DTE <= 21
        - Tested sides (Defense)
        
        Args:
            current_market_data (dict): Optional dict with current prices/regime. 
                                        Example: {'SPX_price': 4000, 'regime': 'contango'}
        """
        updates = []
        
        for trade in self.trades:
            if trade.get('status') != 'OPEN':
                continue

            entry_date = datetime.strptime(trade['entry_date'], "%Y-%m-%d").date()
            days_held = (date.today() - entry_date).days
            
            # Calculate DTE
            try:
                exp_date = datetime.strptime(str(trade['expiration']), "%Y%m%d").date()
                dte = (exp_date - date.today()).days
            except ValueError:
                dte = 0 # Expired or invalid
            
            # 1. TIME STOP (21 DTE)
            if dte <= 21:
                updates.append({
                    "trade_id": trade['id'],
                    "action": "ROLL_OUT",
                    "reason": f"DTE {dte} <= 21 (Gamma Risk).",
                    "instruction": "Roll entire position to next monthly cycle for a Net Credit."
                })
                continue

            # 3. PROFIT TAKING (50%)
            # We need current option prices to calculate this. 
            # If data provided:
            # current_profit = ...
            # if current_profit >= 0.5 * max_profit: ...
            # For now, we output a check instruction.
            updates.append({
                "trade_id": trade['id'],
                "action": "CHECK_PROFIT",
                "reason": "Routine Check",
                "instruction": f"Check if profit >= 50% of Credit Received ({trade.get('credit_received', 0)})."
            })

            # 4. TESTED STRIKES (DEFENSE)
            # Logic: If Underlying Price touches Short Put or Short Call
            # instruction: "Roll untested side closer to delta neutral."
            updates.append({
                "trade_id": trade['id'],
                "action": "MONITOR_STRIKES",
                "reason": "Delta Defense",
                "instruction": f"Verify if {trade.get('symbol')} price is challenging Short Put {trade.get('short_put_strike')} or Short Call {trade.get('short_call_strike')}."
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
