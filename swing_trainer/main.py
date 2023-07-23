import random
import time

import mplfinance as mpf
from pandas import DataFrame

from data.Symbols import healthy_shares
from data.TimescaleDBSticksDao import get_sticks
from data.constants import BUY, SELL


def plot_chart(title: str, sticks: DataFrame, use_bid: bool = False):
    df = sticks.copy()

    if use_bid:
        df = df.rename(columns={'bid_open': 'open', 'bid_high': 'high', 'bid_low': 'low', 'bid_close': 'close'})
    else:
        df = df.rename(columns={'ask_open': 'open', 'ask_high': 'high', 'ask_low': 'low', 'ask_close': 'close'})

    # Plot the chart
    mpf.plot(df, style='charles', type='candle', volume=True, mav=(18, 50, 200), title=title)
    mpf.show(block=False)


def run_loop():
    balance = 10000.0
    symbols = healthy_shares()
    interval = 15
    min_sticks = 120

    while True:
        try:
            # symbol = random.choice(symbols)
            symbol = "CS.D.EURUSD.TODAY.IP"

            sticks = get_sticks(symbol, interval)
            if len(sticks) == 0:
                print(f"not sticks for {symbol}, next one...")
                continue
            if len(sticks) >= min_sticks:
                # take random n. [n:n+100] where 0 >= n >= len - 20
                n = random.randint(0, len(sticks) - min_sticks)
                sticks_to_plot = sticks[n:n+100]
            else:
                n = 0
                sticks_to_plot = sticks[n:len(sticks)-20]
            plot_chart(symbol, sticks_to_plot)

            i = 0
            direction = 0
            stop_loss = 0
            take_profit = 0
            amount = 0
            open_price = 0
            profit = 0
            trade_opened = False
            while True:
                i += 1
                current_index = n + 100 + i
                if current_index >= len(sticks):
                    print("not enough data")
                    break

                spread = 100 * (sticks.iloc[current_index].ask_open - sticks.iloc[current_index].bid_open) / sticks.iloc[current_index].ask_open
                print(f"on {symbol}, spread:{int(spread*100)/100}%")

                # TODO open price
                if direction == 0:
                    choice = input("Enter your choice (1/2/3), or Enter for next stick: ")
                    if choice == "3":
                        print("No go, exit...")
                        break
                    elif choice == "1":
                        direction = BUY
                        open_price = float(input("Enter open price: "))
                        stop_loss = float(input("Enter stop loss price: "))
                        take_profit = float(input("Enter take profit price: "))
                        # open_price = sticks.iloc[current_index].bid_open
                        amount = 100 / (open_price - stop_loss)
                        print(f"open price is {open_price}")
                    elif choice == "2":
                        direction = SELL
                        open_price = float(input("Enter open price: "))
                        stop_loss = float(input("Enter stop loss price: "))
                        take_profit = float(input("Enter take profit price: "))
                        # open_price = sticks.iloc[current_index].ask_open
                        amount = 100 / (stop_loss - open_price)
                        print(f"open price is {open_price}")
                else:
                    print(f"current stick is {sticks.iloc[current_index].to_list()}")
                    time.sleep(1)

                if not trade_opened and sticks.iloc[current_index].bid_low <= open_price <= sticks.iloc[current_index].ask_high:
                    print(f"trade opened. range: {sticks.iloc[current_index].bid_low}, {sticks.iloc[current_index].ask_high}")
                    trade_opened = True

                if trade_opened and direction == BUY:
                    # TODO hi res
                    if sticks.iloc[current_index].bid_low <= stop_loss:
                        print(f"SL is reached, low is {sticks.iloc[current_index].bid_low}")
                        profit = amount * (stop_loss - open_price)
                    elif sticks.iloc[current_index].bid_high >= take_profit:
                        print(f"TP is reached, high is {sticks.iloc[current_index].bid_high}")
                        profit = amount * (take_profit - open_price)
                elif direction == SELL:
                    if sticks.iloc[current_index].ask_high >= stop_loss:
                        print(f"SL is reached, high is {sticks.iloc[current_index].ask_high}")
                        profit = amount * (open_price - stop_loss)
                    elif sticks.iloc[current_index].ask_low <= take_profit:
                        print(f"TP is reached, low is {sticks.iloc[current_index].ask_low}")
                        profit = amount * (open_price - take_profit)

                sticks_to_plot = sticks[n+i:current_index]
                plot_chart(f"{symbol}: {sticks.iloc[current_index].epoch_utc_ms}", sticks_to_plot, direction == BUY)
                if profit != 0 or (open_price != 0 and not trade_opened and i > 10):
                    balance += profit
                    print(f"trade ended. profit: {profit}, balance: {balance}")
                    ignore = input('press to continue')
                    print(ignore)
                    break

        except ValueError as ex:
            print(f"something ValueError happened... {ex}")


if __name__ == "__main__":
    run_loop()
