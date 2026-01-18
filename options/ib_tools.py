from ib_insync import *
from datetime import datetime, date, timedelta
import math
import logging

logger = logging.getLogger("IVStranglerManager")

class IBTools:
    def __init__(self, host='127.0.0.1', port=7496, client_id=100):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = IB()

    def connect(self):
        if not self.ib.isConnected():
            try:
                self.ib.connect(self.host, self.port, clientId=self.client_id)
            except Exception as e:
                logger.error(f"Could not connect to IB: {e}")

    def disconnect(self):
        if self.ib.isConnected():
            self.ib.disconnect()

    def get_vix_term_structure(self):
        """
        Compare Front Month vs Back Month VIX Futures.
        Returns: 'contango', 'backwardation', or 'error'
        """
        try:
            self.connect()
            # Request all VIX futures
            # Note: We need to be careful to get the correct active months.
            # A simple way is to search for 'VIX' futures on CFE.
            
            # Use a broad search or hardcode logic for "next 2 months"
            # Getting specific contracts is faster than searching all.
            
            today = date.today()
            # Logic to guess contract months: current month, next month
            # Format: YYYYMM
            
            # Simple heuristic: Construct contract months for the next 3 months
            months = []
            for i in range(3):
                d = today.replace(day=1) + timedelta(days=32*i)
                months.append(d.strftime("%Y%m"))
            
            futures = []
            for m in months:
                contract = Future('VIX', m, 'CFE')
                details = self.ib.reqContractDetails(contract)
                if details:
                    # Filter for standard monthly (not weekly) if needed?
                    # VIX Futures are usually standard monthly.
                    futures.append(details[0].contract)
            
            if len(futures) < 2:
                return 'error'
                
            # Request market data
            tickers = [self.ib.reqMktData(f, '', False, False) for f in futures[:2]]
            self.ib.sleep(2) # Wait for data
            
            prices = []
            for t in tickers:
                price = t.last if not math.isnan(t.last) else (t.bid + t.ask)/2
                if math.isnan(price): price = t.close # Fallback
                prices.append(price)
            
            logger.debug(f"VIX Futures Prices: {prices}")
            
            if math.isnan(prices[0]) or math.isnan(prices[1]):
                return 'error'

            if prices[0] < prices[1]:
                return 'contango'
            else:
                return 'backwardation'

        except Exception as e:
            logger.error(f"Error checking VIX term structure: {e}")
            return 'error'

    def find_strangle_strikes(self, symbol="SPX", target_dte=45, target_delta=0.16):
        """
        Finds strikes for a Short Strangle.
        Returns: {
            "expiration": str,
            "put_strike": float,
            "call_strike": float,
            "put_delta": float,
            "call_delta": float
        }
        """
        try:
            self.connect()
            underlying = Index(symbol, 'CBOE') if symbol in ['SPX', 'NDX', 'VIX'] else Stock(symbol, 'SMART', 'USD')
            self.ib.qualifyContracts(underlying)
            
            # 1. Get Chains
            chains = self.ib.reqSecDefOptParams(underlying.symbol, '', underlying.secType, underlying.conId)
            if not chains:
                logger.warning("No option chains found.")
                return None

            # Filter for SMART exchange to get aggregate view
            chain = next((c for c in chains if c.exchange == 'SMART'), chains[0])
            
            # 2. Find Expiration closest to 45 DTE
            today = date.today()
            target_date = today + timedelta(days=target_dte)
            
            # Parse expirations (they are strings YYYYMMDD)
            valid_expirations = sorted([exp for exp in chain.expirations])
            
            # Find closest
            best_exp = min(valid_expirations, key=lambda x: abs((datetime.strptime(x, "%Y%m%d").date() - target_date).days))
            logger.info(f"Selected Expiration: {best_exp}")

            # 3. Get Option Chain for that expiration
            strikes = [s for s in chain.strikes]
            # Need underlying price to narrow down strikes request (optimization)
            # Request underlying market data
            und_ticker = self.ib.reqMktData(underlying, '', False, False)
            self.ib.sleep(1)
            und_price = und_ticker.marketPrice()
            if math.isnan(und_price): und_price = und_ticker.close
            
            if math.isnan(und_price) or und_price <= 0:
                 logger.warning("Could not get underlying price.")
                 return None

            # Narrow strikes to +/- 20% to save bandwidth
            relevant_strikes = [s for s in strikes if 0.8 * und_price < s < 1.2 * und_price]
            
            # Create contracts
            contracts = []
            for strike in relevant_strikes:
                contracts.append(Option(symbol, best_exp, strike, 'P', 'SMART'))
                contracts.append(Option(symbol, best_exp, strike, 'C', 'SMART'))
            
            # We can't request market data for ALL of them. 
            # Strategy: Use Black-Scholes locally to estimate delta, or request data for a subset?
            # IB `reqMktData` provides Greeks. 
            # A better way with IB is often to just request the ones we think are close 
            # based on a rough estimate, or use `calculateImpliedVolatility`? 
            # No, `reqMktData` is standard. But limited to ~100 active tickers.
            
            # Heuristic: 16 Delta puts are usually ~10-15% OTM? 16 Delta calls ~5-10% OTM?
            # Let's verify with current VIX.
            # For robustness, let's just pick a spread of strikes every 10 points/50 points?
            
            # Alternatively, request a few around expected range.
            # Put Strike ~ Price * (1 - 0.5 * IV * sqrt(T)) ?
            
            # Let's request specific strikes spaced out, check their delta, and interpolate/refine.
            # But "16 Delta" is a strict rule.
            
            # Let's try to grab data for ~20 strikes on each side that seem "reasonable".
            # Assume 16 Delta is roughly 1 SD.
            # Strike ~ S * exp( +/- sigma * sqrt(T) )
            # We need sigma (IV). Assume 0.20 (20%) for SPX.
            T = target_dte / 365.0
            sigma = 0.20
            
            put_target_strike = und_price * math.exp(-1.0 * sigma * math.sqrt(T))
            call_target_strike = und_price * math.exp(1.0 * sigma * math.sqrt(T))
            
            # Find closest strikes in the chain
            # Get 5 strikes around the target
            put_candidates = sorted(relevant_strikes, key=lambda x: abs(x - put_target_strike))[:5]
            call_candidates = sorted(relevant_strikes, key=lambda x: abs(x - call_target_strike))[:5]
            
            # Request data
            tickers = []
            contracts_map = {}
            
            for k in put_candidates:
                c = Option(symbol, best_exp, k, 'P', 'SMART')
                contracts_map[c.conId] = c # Wait, we don't have conId yet until qualified.
                # Just store by object ID or use list
            
            # Batch qualify
            all_opts = [Option(symbol, best_exp, k, 'P', 'SMART') for k in put_candidates] + \
                       [Option(symbol, best_exp, k, 'C', 'SMART') for k in call_candidates]
            
            self.ib.qualifyContracts(*all_opts)
            
            for c in all_opts:
                t = self.ib.reqMktData(c, '', False, False)
                tickers.append(t)
                
            self.ib.sleep(3)
            
            best_put = None
            best_call = None
            min_put_diff = 1.0
            min_call_diff = 1.0
            
            for t in tickers:
                if t.modelGreeks and t.modelGreeks.delta is not None:
                    delta = abs(t.modelGreeks.delta)
                    strike = t.contract.strike
                    right = t.contract.right
                    
                    diff = abs(delta - target_delta)
                    
                    if right == 'P':
                        if diff < min_put_diff:
                            min_put_diff = diff
                            best_put = (strike, delta, t.bid, t.ask)
                    else:
                        if diff < min_call_diff:
                            min_call_diff = diff
                            best_call = (strike, delta, t.bid, t.ask)
                            
            return {
                "expiration": best_exp,
                "underlying_price": und_price,
                "put": best_put, # (strike, delta, bid, ask)
                "call": best_call
            }

        except Exception as e:
            logger.error(f"Error finding strikes: {e}")
            return None
