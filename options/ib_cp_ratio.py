import sys
from ib_insync import IB, Stock

# Add parent dir for potential imports
sys.path.append('..')

def get_call_put_ratio(symbol: str, host: str = '127.0.0.1', port: int = 7496, client_id: int = 2):
    """
    Connects to IBKR and retrieves aggregated Call/Put Volume and Open Interest for a stock.
    Returns a dictionary with the data.
    """
    ib = IB()
    try:
        ib.connect(host, port, clientId=client_id)
        
        contract = Stock(symbol, 'SMART', 'USD')
        ib.qualifyContracts(contract)
        
        # Generic Ticks:
        # 100: Option Volume 
        # 101: Option OI 
        generic_ticks = '100,101'
        
        ticker = ib.reqMktData(contract, generic_ticks, False, False)
        
        # Wait for data to populate
        # We loop briefly to allow tick updates to arrive
        for _ in range(20):
            ib.sleep(0.2)
            if ticker.callVolume and ticker.putVolume:
                break
        
        # Extract values
        call_vol = ticker.callVolume
        put_vol = ticker.putVolume
        call_oi = ticker.callOpenInterest
        put_oi = ticker.putOpenInterest
        
        result = {
            "symbol": symbol,
            "call_volume": call_vol,
            "put_volume": put_vol,
            "call_oi": call_oi,
            "put_oi": put_oi,
            "volume_cp_ratio": None,
            "oi_cp_ratio": None
        }

        if call_vol and put_vol and call_vol > 0:
            result["volume_cp_ratio"] = put_vol / call_vol
            
        if call_oi and put_oi and call_oi > 0:
            result["oi_cp_ratio"] = put_oi / call_oi
            
        return result

    except Exception as e:
        print(f"Error in get_call_put_ratio: {e}")
        return None
    finally:
        ib.disconnect()

if __name__ == "__main__":
    sym = sys.argv[1] if len(sys.argv) > 1 else "SPY"
    data = get_call_put_ratio(sym)
    
    if data:
        print(f"--- {data['symbol']} Options Data ---")
        print(f"Call Volume: {data['call_volume']}")
        print(f"Put Volume:  {data['put_volume']}")
        if data['volume_cp_ratio'] is not None:
            print(f"Volume C/P Ratio: {data['volume_cp_ratio']:.4f}")
        else:
             print("Volume C/P Ratio: N/A")
             
        print("-" * 20)
        print(f"Call OI: {data['call_oi']}")
        print(f"Put OI:  {data['put_oi']}")
        if data['oi_cp_ratio'] is not None:
            print(f"OI C/P Ratio:     {data['oi_cp_ratio']:.4f}")
        else:
             print("OI C/P Ratio:     N/A")
    else:
        print("Failed to retrieve data.")