import sys
import math
from datetime import datetime, date
from statistics import NormalDist
from ib_insync import IB, Stock, Option, util

# Add the project root to the python path to allow importing if needed in the future
sys.path.append('..')

def black_scholes(S, K, T, r, sigma, option_type):
    """
    Calculate the Black-Scholes option price for a European option.
    
    Args:
        S (float): Current underlying price
        K (float): Strike price
        T (float): Time to expiration in years
        r (float): Risk-free interest rate (decimal, e.g., 0.05 for 5%)
        sigma (float): Volatility (decimal, e.g., 0.2 for 20%)
        option_type (str): 'C' for Call, 'P' for Put
    
    Returns:
        float: Theoretical option price
    """
    if T <= 0:
        return max(0, S - K) if option_type == 'C' else max(0, K - S)
        
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    nd = NormalDist(mu=0, sigma=1)
    
    if option_type == 'C':
        price = S * nd.cdf(d1) - K * math.exp(-r * T) * nd.cdf(d2)
    else:
        price = K * math.exp(-r * T) * nd.cdf(-d2) - S * nd.cdf(-d1)
        
    return price

def calculate_option_value(symbol: str, strike: float, expiration: str, right: str, host: str = '127.0.0.1', port: int = 7496, client_id: int = 1):
    """
    Connects to IBKR TWS/Gateway, requests market data for the specified option and its underlying,
    and returns the option's market price (midpoint of bid/ask) and theoretical Black-Scholes value.
    """
    
    # Normalize inputs
    expiration_str = expiration.replace('-', '')
    right = right.upper()
    if right == 'CALL':
        right = 'C'
    elif right == 'PUT':
        right = 'P'
        
    ib = IB()
    try:
        # Connect to IBKR
        ib.connect(host, port, clientId=client_id)
        
        # Define the underlying stock contract
        underlying = Stock(symbol, 'SMART', 'USD')
        ib.qualifyContracts(underlying)
        
        # Request market data for underlying
        underlying_ticker = ib.reqMktData(underlying, '', False, False)
        
        # Define the Option contract
        contract = Option(symbol, expiration_str, strike, right, 'SMART', currency='USD', multiplier='100')
        
        # Qualify the contract
        qualified_contracts = ib.qualifyContracts(contract)
        if not qualified_contracts:
            return {"error": f"Option contract not found: {symbol} {strike} {expiration} {right}"}
        
        contract = qualified_contracts[0]
        
        # Request market data for the option
        option_ticker = ib.reqMktData(contract, '', False, False)
        
        # Wait for data to arrive
        ib.sleep(2) 
        
        # Wait a bit more if data is delayed
        attempts = 0
        while attempts < 5 and (math.isnan(option_ticker.bid) or math.isnan(option_ticker.ask)):
            ib.sleep(1)
            attempts += 1
            
        # Retrieve values
        und_price = underlying_ticker.marketPrice()
        if math.isnan(und_price) or und_price == 0:
             und_price = underlying_ticker.close
             
        opt_bid = option_ticker.bid
        opt_ask = option_ticker.ask
        opt_last = option_ticker.last
        implied_vol = option_ticker.modelGreeks.impliedVol if option_ticker.modelGreeks else float('nan')
        
        # Calculate mid price
        if not math.isnan(opt_bid) and not math.isnan(opt_ask) and opt_bid > 0 and opt_ask > 0:
            market_price = (opt_bid + opt_ask) / 2
        elif not math.isnan(opt_last) and opt_last > 0:
            market_price = opt_last
        else:
            market_price = None
            
        # Calculate Theoretical Value using Black-Scholes
        theoretical_value = None
        
        # 1. Calculate Time to Expiration (T)
        try:
            exp_date = datetime.strptime(expiration_str, "%Y%m%d").date()
            today = date.today()
            days_to_expiry = (exp_date - today).days
            T = max(0, days_to_expiry / 365.0)
        except ValueError:
            T = 0
            
        # 2. Use retrieved Implied Volatility or fallback
        if math.isnan(implied_vol) or implied_vol <= 0:
             sigma = 0.5 # Fallback
        else:
            sigma = implied_vol
            
        # 3. Risk-free rate
        r = 0.0375
        
        if und_price and und_price > 0:
             theoretical_value = black_scholes(und_price, strike, T, r, sigma, right)
            
        result = {
            "symbol": symbol,
            "strike": strike,
            "expiration": expiration,
            "right": right,
            "underlying_price": und_price,
            "option_bid": opt_bid,
            "option_ask": opt_ask,
            "market_value": market_price,
            "theoretical_value": theoretical_value,
            "implied_volatility": implied_vol if not math.isnan(implied_vol) else None,
            "currency": contract.currency,
            "model_inputs": {
                "S": und_price,
                "K": strike,
                "T": T,
                "r": r,
                "sigma": sigma
            }
        }
        
        return result

    except Exception as e:
        return {"error": str(e)}
    finally:
        ib.disconnect()

if __name__ == "__main__":
    if len(sys.argv) >= 5:
        sym = sys.argv[1]
        strk = float(sys.argv[2])
        exp = sys.argv[3]
        rt = sys.argv[4]
        port = int(sys.argv[5]) if len(sys.argv) > 5 else 7496
        
        print(f"Fetching data for {sym} {strk} {exp} {rt} on port {port}...")
        val = calculate_option_value(sym, strk, exp, rt, port=port)
        import pprint
        pprint.pprint(val)
    else:
        print("Usage: python options/ib_calculator.py <SYMBOL> <STRIKE> <EXPIRATION> <RIGHT> [PORT]")
