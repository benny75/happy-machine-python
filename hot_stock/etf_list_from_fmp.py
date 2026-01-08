import requests, pandas as pd

API_KEY      = "FLRh0qFakyquQQaD469NUgpKH1RdDubE"          # grab a free one at FMP
VOL_MIN      = 1_000_000                     # ≥100 k average daily shares

url = (
    "https://financialmodelingprep.com/api/v3/stock-screener"
    "?isEtf=true"                          # <-- only ETFs
    "&country=US"                          # only U-S listings
    f"&volumeMoreThan={VOL_MIN}"           # same volume rule
    "&limit=10000"                         # plenty of room
    f"&apikey={API_KEY}"
)

raw = requests.get(url, timeout=30).json()

# -- a pure-symbol list (no duplicates) --
etf_symbols = sorted({row["symbol"] for row in raw})
print(len(etf_symbols), "ETFs hit the filter")
print(etf_symbols)                         # list[str] ready for Python use

# if you’d also like the fund name and a CSV:
df = pd.DataFrame(
    { "symbol": row["symbol"],
      "name"  : row.get("companyName", "") } for row in raw
).drop_duplicates("symbol").sort_values("symbol")

df.to_csv("us_etf_volume100k.csv", index=False)
print("CSV written → us_etf_volume100k.csv")