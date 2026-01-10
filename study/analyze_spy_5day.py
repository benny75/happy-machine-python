import matplotlib.pyplot as plt
import pandas as pd

from data.TimescaleDBSticksDao import get_sticks


def _undiff_list(input_list):
    return [sum(input_list[:i + 1]) for i in range(len(input_list))]


def analyze_spy_5day():
    # Use the provided symbol and daily interval (1440 minutes)
    symbol = "AB.D.SPYAU.DAILY.IP"
    interval = 1440

    # Retrieve candlestick data
    df = get_sticks(symbol, interval)

    # For simplicity, use ask_close as the closing price.
    # You might choose to use bid_close or an average of both.
    df['close'] = df['ask_close']

    results = []  # to hold the subsequent 5-day % changes
    # Loop through the DataFrame using a sliding window.
    # We need at least 10 data points: 5 days for the drop and 5 days for the outcome.
    for i in range(len(df) - 10):
        price_start = df.iloc[i]['close']          # beginning of the 5-day drop period
        price_end_drop = df.iloc[i+4]['close']       # end of the drop period
        price_end_outcome = df.iloc[i+9]['close']      # end of the outcome period

        # Compute percentage change over the first 5 days
        pct_change = (price_end_drop - price_start) / price_start

        # Compute percentage change over the following 5 days
        pct_change_outcome = (price_end_outcome - price_end_drop) / price_end_drop

        # If the 5-day drop is at least 2% (i.e. -0.02 or lower), record the outcome
        if -0.01<= pct_change <= 0.01:
            results.append(pct_change_outcome)

    if results:
        avg_change = sum(results) / len(results)
        median_change = pd.Series(results).median()
        print("Analysis for SPY (symbol: AB.D.SPYAU.DAILY.IP):")
        print("--------------------------------------------------")
        print(f"Number of instances: {len(results)}")
        print(f"Average subsequent 5-day % change: {avg_change*100:.2f}%")
        print(f"Median subsequent 5-day % change: {median_change*100:.2f}%")
    else:
        print("No instances found")

    # Plot histogram of the subsequent 5-day changes
    plt.hist(results, bins=10, edgecolor='black')
    plt.xlabel("Subsequent 5-day % Change")
    plt.ylabel("Frequency")
    plt.title("Distribution of 5-day % Changes After a <1% 5-day up/down")
    plt.show()

if __name__ == '__main__':
    analyze_spy_5day()