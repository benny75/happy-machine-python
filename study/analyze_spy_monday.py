import matplotlib.pyplot as plt

from data.TimescaleDBSticksDao import get_sticks

# ======= Monday Open-Close Analysis =======

def analyze_monday_open_close():
    # Use SPY daily data
    symbol = "AB.D.SPYAU.DAILY.IP"
    interval = 1440  # daily interval in minutes

    # Retrieve candlestick data
    df = get_sticks(symbol, interval)

    # Use ask_open and ask_close as the daily open and close prices.
    # Adjust if you'd like to use bid prices or an average.
    df['open'] = df['ask_open']
    df['close'] = df['ask_close']

    # Filter the DataFrame to only include Mondays (Monday == 0)
    df_mondays = df[df.index.weekday == 0]

    # Calculate percentage change from open to close: (close - open) / open
    df_mondays['pct_change'] = (df_mondays['close'] - df_mondays['open']) / df_mondays['open']

    # Compute summary statistics
    count = df_mondays.shape[0]
    avg_change = df_mondays['pct_change'].mean()
    median_change = df_mondays['pct_change'].median()
    std_change = df_mondays['pct_change'].std()

    print("Monday Open-Close Analysis for SPY (symbol: AB.D.SPYAU.DAILY.IP):")
    print("----------------------------------------------------------")
    print(f"Number of Mondays analyzed: {count}")
    print(f"Average Monday % change (close - open): {avg_change*100:.2f}%")
    print(f"Median Monday % change (close - open): {median_change*100:.2f}%")
    print(f"Standard Deviation: {std_change*100:.2f}%")

    # Plot histogram of the percentage changes on Mondays
    plt.hist(df_mondays['pct_change'], bins=20, edgecolor='black')
    plt.xlabel("Monday % Change (Close - Open)")
    plt.ylabel("Frequency")
    plt.title("Distribution of Monday Open-Close % Changes")
    plt.show()

if __name__ == '__main__':
    analyze_monday_open_close()