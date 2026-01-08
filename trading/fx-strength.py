import pandas as pd


def compute_currency_strength(data_feed, currencies, timeframes):
    """
    Computes a strength value for each currency over multiple timeframes.

    Parameters:
      data_feed: A dictionary where each key is a timeframe (e.g., 'M5', 'H1', etc.)
                 and each value is a dictionary of currency pair data.
                 Each currency pair (e.g., 'EURUSD') maps to a dict with 'open' and 'close' prices.

      currencies: A list of currency codes (e.g., ['EUR', 'JPY', ...]).

      timeframes: A list of timeframes to process.

    Returns:
      A pandas DataFrame with timeframes as rows and currencies as columns containing
      the aggregated strength scores.
    """
    # Initialize a nested dictionary to hold strength scores per timeframe & currency.
    strength_matrix = {tf: {currency: 0.0 for currency in currencies} for tf in timeframes}

    for tf in timeframes:
        # Get all pair data for this timeframe
        pairs_data = data_feed.get(tf, {})
        for pair, prices in pairs_data.items():
            # Expect pair names in the format "EURUSD" (first 3 letters: base, next 3: quote)
            if len(pair) < 6:
                continue  # Skip if the pair name is not valid.
            base = pair[:3]
            quote = pair[3:]

            # Process only if both currencies are in our list.
            if base in currencies and quote in currencies:
                open_price = prices['open']
                close_price = prices['close']

                # Compute percentage return for the pair.
                ret = (close_price - open_price) / open_price

                # For a forex pair, a positive return indicates that the base currency is gaining
                # relative to the quote currency. We add the return to the base's strength
                # and subtract it from the quote's strength.
                strength_matrix[tf][base] += ret
                strength_matrix[tf][quote] -= ret

    # Convert the nested dictionary into a pandas DataFrame for an easy-to-read matrix.
    # Rows will be timeframes and columns will be currencies.
    df = pd.DataFrame(strength_matrix).T
    return df


# -------------------------------
# Example usage with dummy data:
# -------------------------------

# Define the eight currencies
currencies = ["EUR", "JPY", "GBP", "NZD", "AUD", "CHF", "CAD", "USD"]

# Define the timeframes
timeframes = ["M5", "M15", "H1", "H4", "D1"]

# Sample data_feed structure.
# For each timeframe, we provide a dictionary of currency pairs.
# Each pair has an 'open' and 'close' price.
data_feed = {
    'M5': {
        'EURUSD': {'open': 1.1000, 'close': 1.1005},
        'GBPUSD': {'open': 1.2500, 'close': 1.2490},
        'USDJPY': {'open': 110.00, 'close': 110.10},
        'AUDUSD': {'open': 0.7000, 'close': 0.7005},
        'NZDUSD': {'open': 0.6500, 'close': 0.6490},
        'USDCAD': {'open': 1.3000, 'close': 1.2990},
        'CHFUSD': {'open': 0.9900, 'close': 0.9910},
        'EURGBP': {'open': 0.8800, 'close': 0.8810}
    },
    'M15': {
        'EURUSD': {'open': 1.1000, 'close': 1.1010},
        'GBPUSD': {'open': 1.2500, 'close': 1.2480},
        'USDJPY': {'open': 110.00, 'close': 110.05},
        'AUDUSD': {'open': 0.7000, 'close': 0.6995},
        'NZDUSD': {'open': 0.6500, 'close': 0.6510},
        'USDCAD': {'open': 1.3000, 'close': 1.3010},
        'CHFUSD': {'open': 0.9900, 'close': 0.9890},
        'EURGBP': {'open': 0.8800, 'close': 0.8790}
    },
    'H1': {
        'EURUSD': {'open': 1.1000, 'close': 1.1020},
        'GBPUSD': {'open': 1.2500, 'close': 1.2510},
        'USDJPY': {'open': 110.00, 'close': 110.20},
        'AUDUSD': {'open': 0.7000, 'close': 0.7010},
        'NZDUSD': {'open': 0.6500, 'close': 0.6490},
        'USDCAD': {'open': 1.3000, 'close': 1.2980},
        'CHFUSD': {'open': 0.9900, 'close': 0.9920},
        'EURGBP': {'open': 0.8800, 'close': 0.8820}
    },
    'H4': {
        'EURUSD': {'open': 1.1000, 'close': 1.1030},
        'GBPUSD': {'open': 1.2500, 'close': 1.2520},
        'USDJPY': {'open': 110.00, 'close': 110.15},
        'AUDUSD': {'open': 0.7000, 'close': 0.7000},
        'NZDUSD': {'open': 0.6500, 'close': 0.6500},
        'USDCAD': {'open': 1.3000, 'close': 1.3005},
        'CHFUSD': {'open': 0.9900, 'close': 0.9900},
        'EURGBP': {'open': 0.8800, 'close': 0.8805}
    },
    'D1': {
        'EURUSD': {'open': 1.1000, 'close': 1.1050},
        'GBPUSD': {'open': 1.2500, 'close': 1.2480},
        'USDJPY': {'open': 110.00, 'close': 110.30},
        'AUDUSD': {'open': 0.7000, 'close': 0.7020},
        'NZDUSD': {'open': 0.6500, 'close': 0.6470},
        'USDCAD': {'open': 1.3000, 'close': 1.2980},
        'CHFUSD': {'open': 0.9900, 'close': 0.9870},
        'EURGBP': {'open': 0.8800, 'close': 0.8820}
    }
}

# Compute the currency strength matrix
strength_df = compute_currency_strength(data_feed, currencies, timeframes)
print("Currency Strength Matrix:")
print(strength_df)