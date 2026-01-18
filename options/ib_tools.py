from ib_insync import *
from datetime import datetime, date, timedelta
import math
import logging
import pandas as pd

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
            today = date.today()
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
                    futures.append(details[0].contract)
            
            if len(futures) < 2:
                return 'error'
                
            tickers = [self.ib.reqMktData(f, '', False, False) for f in futures[:2]]
            self.ib.sleep(2) 
            
            prices = []
            for t in tickers:
                price = t.last if not math.isnan(t.last) else (t.bid + t.ask)/2
                if math.isnan(price): price = t.close 
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

    def get_current_price(self, symbol="SPX"):
        """
        Gets the current market price for a symbol.
        """
        try:
            self.connect()
            if symbol == 'SPX' or symbol == 'VIX':
                contract = Index(symbol, 'CBOE')
            else:
                contract = Stock(symbol, 'SMART', 'USD')
            
            self.ib.qualifyContracts(contract)
            ticker = self.ib.reqMktData(contract, '', False, False)
            self.ib.sleep(2)
            
            price = ticker.last
            if math.isnan(price) or price <= 0:
                 price = ticker.marketPrice()
            if math.isnan(price) or price <= 0:
                 price = ticker.close
                 
            return price
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return 0.0

    def get_historical_iv_rank(self, symbol="SPX"):
        """
        Fetches 1 year of historical implied volatility from IBKR and calculates Rank.
        """
        try:
            self.connect()
            if symbol == 'SPX':
                contract = Index('SPX', 'CBOE')
            else:
                # Fallback for stocks
                contract = Stock(symbol, 'SMART', 'USD')
            
            self.ib.qualifyContracts(contract)
            
            bars = self.ib.reqHistoricalData(
                contract, 
                endDateTime='', 
                durationStr='1 Y', 
                barSizeSetting='1 day', 
                whatToShow='OPTION_IMPLIED_VOLATILITY', 
                useRTH=True
            )
            
            if not bars:
                logger.warning(f"No historical IV data for {symbol}")
                return 0.0
                
            df = util.df(bars)
            low = df['close'].min()
            high = df['close'].max()
            current = df['close'].iloc[-1]
            
            if high == low:
                return 0.0
                
            rank = (current - low) / (high - low) * 100
            logger.info(f"{symbol} IV Rank (Real-time IB): {rank:.2f} (Low: {low:.2f}, High: {high:.2f}, Current: {current:.2f})")
            return rank

        except Exception as e:
            logger.error(f"Error getting historical IV rank: {e}")
            return 0.0

    def find_iron_condor_strikes(self, symbol="SPX", target_dte=45, short_delta=0.16, long_delta=0.06):
        """
        Finds strikes for an Iron Condor.
        Short legs at `short_delta` (default 0.16).
        Long legs at `long_delta` (default 0.06).
        """
        try:
            self.connect()
            
            underlying_contract = None
            is_future = False
            
            if symbol == 'MES':
                is_future = True
                # Find active MES Future
                pattern = Future('MES', '', 'CME')
                details = self.ib.reqContractDetails(pattern)
                futures = [d.contract for d in details]
                futures.sort(key=lambda c: c.lastTradeDateOrContractMonth)
                
                today_str = datetime.now().strftime("%Y%m%d")
                active_future = None
                for f in futures:
                     if f.lastTradeDateOrContractMonth > today_str:
                         active_future = f
                         break
                
                if not active_future:
                    logger.error("No active MES future found.")
                    return None
                    
                logger.info(f"Active MES Future: {active_future.localSymbol}")
                underlying_contract = active_future
                
            else:
                underlying_contract = Index(symbol, 'CBOE') if symbol in ['SPX', 'NDX', 'VIX'] else Stock(symbol, 'SMART', 'USD')
            
            self.ib.qualifyContracts(underlying_contract)
            
            # 1. Get Chains
            if is_future:
                chains = self.ib.reqSecDefOptParams(underlying_contract.symbol, 'CME', underlying_contract.secType, underlying_contract.conId)
            else:
                chains = self.ib.reqSecDefOptParams(underlying_contract.symbol, '', underlying_contract.secType, underlying_contract.conId)
                
            if not chains:
                logger.warning("No option chains found.")
                return None

            if is_future:
                 chain = chains[0]
            else:
                 chain = next((c for c in chains if c.exchange == 'SMART'), chains[0])
            
            # 2. Find Expiration closest to 45 DTE
            today = date.today()
            target_date = today + timedelta(days=target_dte)
            
            valid_expirations = sorted([exp for exp in chain.expirations])
            best_exp = min(valid_expirations, key=lambda x: abs((datetime.strptime(x, "%Y%m%d").date() - target_date).days))
            logger.info(f"Selected Expiration: {best_exp}")

            # 3. Get Option Chain for that expiration
            strikes = [s for s in chain.strikes]
            
            und_ticker = self.ib.reqMktData(underlying_contract, '', False, False)
            self.ib.sleep(2)
            
            und_price = und_ticker.marketPrice()
            if math.isnan(und_price) or und_price <= 0:
                 und_price = und_ticker.close
                 if math.isnan(und_price) or und_price <= 0:
                      und_price = und_ticker.last
            
            if math.isnan(und_price) or und_price <= 0:
                 logger.warning(f"Could not get underlying price for {symbol}.")
                 return None
                 
            logger.info(f"Underlying Price ({symbol}): {und_price}")

            # Narrow strikes to +/- 30% to catch far OTM long legs
            relevant_strikes = [s for s in strikes if 0.7 * und_price < s < 1.3 * und_price]
            
            # Estimate targets
            T = target_dte / 365.0
            sigma = 0.20 # Base assumption, will refine with Greeks
            
            # Helper to estimate strike from delta (approximation)
            # Delta approx N(d1). Inverse CDF needed or just scan.
            # Scanning is safer.
            
            # Heuristic centers
            # Short Put ~ 16 delta ~ -1 SD
            # Long Put ~ 6 delta ~ -1.5 SD
            # Short Call ~ 16 delta ~ +1 SD
            # Long Call ~ 6 delta ~ +1.5 SD
            
            short_put_target = und_price * math.exp(-1.0 * sigma * math.sqrt(T))
            long_put_target = und_price * math.exp(-1.6 * sigma * math.sqrt(T))
            
            short_call_target = und_price * math.exp(1.0 * sigma * math.sqrt(T))
            long_call_target = und_price * math.exp(1.6 * sigma * math.sqrt(T))
            
            # Get candidates
            def get_candidates(target, count=5):
                return sorted(relevant_strikes, key=lambda x: abs(x - target))[:count]

            candidates = set()
            candidates.update(get_candidates(short_put_target))
            candidates.update(get_candidates(long_put_target))
            candidates.update(get_candidates(short_call_target))
            candidates.update(get_candidates(long_call_target))
            
            all_opts = []
            contract_map = {} # Key: (strike, right) -> contract
            
            for k in candidates:
                # Add Put
                if is_future:
                    p = FuturesOption(symbol, best_exp, k, 'P', 'CME')
                    c = FuturesOption(symbol, best_exp, k, 'C', 'CME')
                else:
                    p = Option(symbol, best_exp, k, 'P', 'SMART')
                    c = Option(symbol, best_exp, k, 'C', 'SMART')
                
                all_opts.extend([p, c])
                contract_map[(k, 'P')] = p
                contract_map[(k, 'C')] = c

            self.ib.qualifyContracts(*all_opts)
            
            tickers = []
            for c in all_opts:
                t = self.ib.reqMktData(c, '', False, False)
                tickers.append(t)
                
            self.ib.sleep(3)
            
            # Select Best Strikes
            def find_best(right, target_d):
                best = None
                min_diff = 1.0
                for t in tickers:
                    if t.contract.right != right: continue
                    
                    if t.modelGreeks and t.modelGreeks.delta is not None:
                        delta = abs(t.modelGreeks.delta)
                        diff = abs(delta - target_d)
                        if diff < min_diff:
                            min_diff = diff
                            best = (t.contract.strike, delta, t.bid, t.ask)
                return best

            short_put = find_best('P', short_delta)
            long_put = find_best('P', long_delta)
            short_call = find_best('C', short_delta)
            long_call = find_best('C', long_delta)
            
            # Fallback (Heuristic) if Greeks fail
            if not short_put:
                k = get_candidates(short_put_target, 1)[0]
                short_put = (k, 0.0, 0.0, 0.0)
            if not long_put:
                k = get_candidates(long_put_target, 1)[0]
                long_put = (k, 0.0, 0.0, 0.0)
            if not short_call:
                k = get_candidates(short_call_target, 1)[0]
                short_call = (k, 0.0, 0.0, 0.0)
            if not long_call:
                k = get_candidates(long_call_target, 1)[0]
                long_call = (k, 0.0, 0.0, 0.0)

            return {
                "expiration": best_exp,
                "underlying_price": und_price,
                "short_put": short_put,
                "long_put": long_put,
                "short_call": short_call,
                "long_call": long_call
            }

        except Exception as e:
            logger.error(f"Error finding strikes: {e}")
            return None

        except Exception as e:
            logger.error(f"Error finding strikes: {e}")
            return None
