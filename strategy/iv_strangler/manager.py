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
    
    # 1. Entry Scan
    if args.auto_scan or input("\nScan for new entries? (y/n): ").lower() == 'y':
        logger.info("[1] Scanning for Entries (MES)...")
        
        # IV Rank Check (Using SPX as proxy for broad market volatility)
        logger.info("    Fetching SPX IV Rank from IBKR (Real-time)...")
        iv_rank = ib.get_historical_iv_rank("SPX")
        logger.info(f"    SPX IV Rank: {iv_rank:.2f}")

        # Check Core Strategy
        if iv_rank < 30:
            logger.info(f"    [WAIT] IV Rank {iv_rank:.2f} < 30. No new entries.")
        else:
            logger.info("    [GO] Conditions met! Searching for Iron Condor strikes on MES...")
            # Find strikes for MES Iron Condor
            strikes = ib.find_iron_condor_strikes("MES", target_dte=45, short_delta=0.16, long_delta=0.06)
            
            if strikes:
                logger.info("    >>> RECOMMENDATION (IRON CONDOR) <<<")
                logger.info(f"    Expiration: {strikes['expiration']}")
                logger.info(f"    Underlying: {strikes['underlying_price']}")
                
                # Puts
                if strikes['short_put']:
                    k, d, b, a = strikes['short_put']
                    logger.info(f"    SELL PUT:  Strike {k} (Delta {d:.2f}) | Bid/Ask: {b}/{a}")
                else:
                    logger.info("    SELL PUT:  Not found")

                if strikes['long_put']:
                    k, d, b, a = strikes['long_put']
                    logger.info(f"    BUY PUT:   Strike {k} (Delta {d:.2f}) | Bid/Ask: {b}/{a}")
                else:
                    logger.info("    BUY PUT:   Not found")
                    
                # Calls
                if strikes['short_call']:
                    k, d, b, a = strikes['short_call']
                    logger.info(f"    SELL CALL: Strike {k} (Delta {d:.2f}) | Bid/Ask: {b}/{a}")
                else:
                    logger.info("    SELL CALL: Not found")

                if strikes['long_call']:
                    k, d, b, a = strikes['long_call']
                    logger.info(f"    BUY CALL:  Strike {k} (Delta {d:.2f}) | Bid/Ask: {b}/{a}")
                else:
                    logger.info("    BUY CALL:  Not found")
                
                if input("\n    Record this trade? (y/n): ").lower() == 'y':
                    try:
                        credit = float(input("    Enter total credit received: "))
                        trade = {
                            "symbol": "MES",
                            "type": "IRON_CONDOR",
                            "expiration": strikes['expiration'],
                            "short_put_strike": strikes['short_put'][0] if strikes['short_put'] else 0,
                            "long_put_strike": strikes['long_put'][0] if strikes['long_put'] else 0,
                            "short_call_strike": strikes['short_call'][0] if strikes['short_call'] else 0,
                            "long_call_strike": strikes['long_call'][0] if strikes['long_call'] else 0,
                            "entry_price": strikes['underlying_price'],
                            "entry_iv_rank": iv_rank,
                            "credit_received": credit,
                            "units": 1 
                        }
                        strategy.add_trade(trade)
                        logger.info(f"Trade recorded: {trade}")
                    except ValueError:
                        logger.error("Invalid input for credit.")
            else:
                logger.warning("    ! Could not find suitable strikes.")

    # 2. Monitor Active
    if args.monitor or input("\nMonitor active positions? (y/n): ").lower() == 'y':
        logger.info("[2] Monitoring Active Positions...")
        updates = strategy.check_active_positions()
        
        if not updates:
            logger.info("    No active positions.")
        else:
            for u in updates:
                if 'action' in u:
                    logger.info(f"    [Trade #{u['trade_id']}] ACTION: {u['action']}")
                    logger.info(f"      Reason: {u['reason']}")
                    logger.info(f"      Instruction: {u['instruction']}")
                else:
                    logger.info(f"    Trade #{u['trade_id']}: {u}")
                
    ib.disconnect()
    logger.info("Done.")

if __name__ == "__main__":
    main()
