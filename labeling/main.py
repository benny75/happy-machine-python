import pickle
import random
import time

import mplfinance as mpf
import pandas as pd
from pandas import DataFrame

from data.SticksEnrichment import add_ema
from data.Symbols import healthy_shares
from data.TimescaleDBSticksDao import get_sticks
from data.constants import BUY, SELL
from labeling.DataStore import DataStore


def plot_chart(title: str, sticks: DataFrame, use_bid: bool = False):
    df = sticks.copy()

    if use_bid:
        df = df.rename(columns={'bid_open': 'open', 'bid_high': 'high', 'bid_low': 'low', 'bid_close': 'close'})
    else:
        df = df.rename(columns={'ask_open': 'open', 'ask_high': 'high', 'ask_low': 'low', 'ask_close': 'close'})

    # Create AddPlot objects for each EMA
    ap_ema18 = mpf.make_addplot(df['ema18'])
    ap_ema50 = mpf.make_addplot(df['ema50'])
    ap_ema200 = mpf.make_addplot(df['ema200'])

    # Create a list of AddPlot objects
    aps = [ap_ema18, ap_ema50, ap_ema200]

    # Plot the chart
    mpf.plot(df, style='charles', type='candle', volume=True, addplot=aps, title=title)
    mpf.show(block=False)


def run_loop():
    balance = 10000.0
    # symbols = healthy_shares()
    interval = 15
    min_sticks = 120

    data_store = DataStore()

    while True:
        try:
            # symbol = random.choice(symbols)
            symbol = "CS.D.EURUSD.TODAY.IP"

            sticks = get_sticks(symbol, interval)
            if len(sticks) == 0:
                print(f"not sticks for {symbol}, next one...")
                continue
            sticks = add_ema(sticks)

            if len(sticks) >= min_sticks:
                # take random n. [n:n+100] where 0 >= n >= len - 20
                n = random.randint(0, len(sticks) - min_sticks)
                sticks_to_plot = sticks[n:n+100]
            else:
                n = 0
                sticks_to_plot = sticks[n:len(sticks)-20]

            plot_chart(f"{symbol}: {sticks.index[-1]}", sticks_to_plot)

            i = 0
            direction = 0
            open_price = 0
            profit = 0
            trade_opened = False
            while True:
                i += 1
                current_index = n + 100 + i
                if current_index >= len(sticks):
                    print("not enough data")
                    break

                if not check_trend(sticks):
                    print("clearly not trendy EMA")
                    break

                spread = 100 * (sticks.iloc[current_index].ask_open - sticks.iloc[current_index].bid_open) / sticks.iloc[current_index].ask_open
                print(f"on {symbol}, spread:{int(spread*100)/100}%")

                if direction == 0:
                    choice = input("n for next, or (offset, EMAn), any other key for next random chart")
                    if choice == "n":
                        print("next stick")
                    elif ',' in choice:
                        try:
                            offset_str, ema_n_str = choice.split(',')
                            offset = int(offset_str)
                            ema_n = int(ema_n_str)
                            is_up = sticks.iloc[current_index].ask_open > sticks.iloc[current_index-100].ask_open
                            print(f"writing in {offset}, {is_up}, {ema_n}")
                            data_store.store_data(symbol, interval, True, is_up, ema_n, sticks[current_index-100+offset : current_index+offset])
                        except Exception as ex:
                            print(f"failed to parse {choice}")
                            raise ex
                        i -= 1
                    else:
                        break
                else:
                    print(f"current stick is {sticks.iloc[current_index].to_list()}")
                    time.sleep(1)

                sticks_to_plot = sticks[n+i:current_index]
                plot_chart(f"{symbol}: {sticks.index[current_index]}", sticks_to_plot, direction == BUY)
                if profit != 0 or (open_price != 0 and not trade_opened and i > 10):
                    balance += profit
                    print(f"trade ended. profit: {profit}, balance: {balance}")
                    ignore = input('press to continue')
                    print(ignore)
                    break

        except ValueError as ex:
            print(f"something ValueError happened... {ex}")


def check_trend(sticks: pd.DataFrame) -> bool:
    """Checks if at least half of the time, EMA 18, 50 and 200 are on the same trend."""
    # Check when the EMAs are on the same trend
    trend_condition = ((sticks['ema18'] < sticks['ema50']) & (sticks['ema50'] < sticks['ema200'])) | (
                (sticks['ema18'] > sticks['ema50']) & (sticks['ema50'] > sticks['ema200']))

    # Count number of instances where the trend condition is met
    trend_count = trend_condition.sum()

    # Compare trend_count with half of the total number of instances
    return trend_count >= len(sticks) * .7

if __name__ == "__main__":
    run_loop()
