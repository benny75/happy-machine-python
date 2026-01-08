import requests, pandas as pd

API_KEY = "FLRh0qFakyquQQaD469NUgpKH1RdDubE"          # get a free key at FinancialModelingPrep
MIN_VOL      = 100_000                     # ≥100 k average daily shares
US_EXCHANGES = ("NASDAQ", "NYSE", "AMEX")  # primary U.S. venues only

rows = []
for ex in US_EXCHANGES:
    url = (
        "https://financialmodelingprep.com/api/v3/stock-screener"
        f"?exchange={ex}"
        f"&volumeMoreThan={MIN_VOL}"
        "&isEtf=false"                     # skip ETFs
        "&limit=5000"                      # generous cap per call
        f"&apikey={API_KEY}"
    )
    rows.extend(requests.get(url, timeout=30).json())

# de-duplicate by symbol and keep the first hit
unique = {}
for r in rows:
    sym = r["symbol"]
    # fall back to 'company' if older field name appears
    name = r.get("companyName") or r.get("company", "")
    if sym not in unique and name:
        unique[sym] = {"symbol": sym, "name": name}

df = pd.DataFrame(unique.values()).sort_values("symbol")
df.to_csv("us_high_volume_stocks.csv", index=False)

print(f"Wrote {len(df)} rows to us_high_volume_stocks.csv")