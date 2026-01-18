import sys
import os
import argparse
import logging
from datetime import date

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from strategy.iv_strangler.iv_strangler import IVStrangler
from options.ib_tools import IBTools

# Configure Logging
log_file = os.path.join(os.path.dirname(__file__), 'iv_strangler.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("IVStranglerManager")

def main():
    parser = argparse.ArgumentParser(description="IV Strangler Strategy Manager")
    parser.add_argument("--auto-scan", action="store_true", help="Automatically scan for entries")
    parser.add_argument("--monitor", action="store_true", help="Monitor active positions")
    args = parser.parse_args()

    logger.info("=== IV Strangler Strategy Manager Started ===")
    
    strategy = IVStrangler()
    ib = IBTools()
    
    # 1. Market Analysis
    logger.info("[1] Analyzing Market Regime...")
    try:
        regime = ib.get_vix_term_structure()
        logger.info(f"    VIX Term Structure: {regime.upper()}")
        
        if regime == 'error':
            logger.warning("    ! Could not fetch VIX futures. Proceeding with caution (assuming Contango for manual override).")
            regime = 'contango'
            
    except Exception as e:
        logger.error(f"    ! Error connecting to IB: {e}")
        regime = 'unknown'

    # 2. Entry Scan
    if args.auto_scan or input("\nScan for new entries? (y/n): ").lower() == 'y':
        logger.info("[2] Scanning for Entries (SPX)...")
        
        # IV Rank Check
        iv_rank_data = strategy.get_symbol_iv_rank("SPX")
        iv_rank = iv_rank_data
        
        logger.info(f"    SPX IV Rank: {iv_rank:.2f}")
        
        if regime == 'backwardation':
            logger.info("    [STOP] Market in Backwardation. No new entries.")
        elif iv_rank < 30:
            logger.info(f"    [WAIT] IV Rank {iv_rank:.2f} < 30. No new entries.")
        else:
            logger.info("    [GO] Conditions met! Searching for strikes...")
            # Find strikes
            strikes = ib.find_strangle_strikes("SPX", target_dte=45, target_delta=0.16)
            
            if strikes:
                logger.info("    >>> RECOMMENDATION <<<")
                logger.info(f"    Expiration: {strikes['expiration']}")
                logger.info(f"    Underlying: {strikes['underlying_price']}")
                
                if strikes['put']:
                    p_k, p_d, p_b, p_a = strikes['put']
                    logger.info(f"    SELL PUT:  Strike {p_k} (Delta {p_d:.2f}) | Bid/Ask: {p_b}/{p_a}")
                else:
                    logger.info("    SELL PUT:  Not found")
                    
                if strikes['call']:
                    c_k, c_d, c_b, c_a = strikes['call']
                    logger.info(f"    SELL CALL: Strike {c_k} (Delta {c_d:.2f}) | Bid/Ask: {c_b}/{c_a}")
                else:
                    logger.info("    SELL CALL: Not found")
                
                # Interactive part remains input() as it requires user action, but we log the decision
                if input("\n    Record this trade? (y/n): ").lower() == 'y':
                    try:
                        credit = float(input("    Enter total credit received: "))
                        trade = {
                            "symbol": "SPX",
                            "expiration": strikes['expiration'],
                            "put_strike": strikes['put'][0] if strikes['put'] else 0,
                            "call_strike": strikes['call'][0] if strikes['call'] else 0,
                            "entry_price": strikes['underlying_price'],
                            "entry_iv_rank": iv_rank,
                            "credit_received": credit
                        }
                        strategy.add_trade(trade)
                        logger.info(f"Trade recorded: {trade}")
                    except ValueError:
                        logger.error("Invalid input for credit.")
            else:
                logger.warning("    ! Could not find suitable strikes.")

    # 3. Monitor Active
    if args.monitor or input("\nMonitor active positions? (y/n): ").lower() == 'y':
        logger.info("[3] Monitoring Active Positions...")
        updates = strategy.check_active_positions()
        
        if not updates:
            logger.info("    No active positions.")
        else:
            for u in updates:
                logger.info(f"    Trade #{u['trade_id']} ({u['symbol']}): Held {u['days_held']} days. {u['msg']}")
                
    ib.disconnect()
    logger.info("Done.")

if __name__ == "__main__":
    main()
