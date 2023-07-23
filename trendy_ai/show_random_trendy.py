import random

from data.SticksEnrichment import add_ema
from data.Symbols import healthy_shares, INDEXES, CURRENCIES
from data.TimescaleDBSticksDao import get_sticks
from trendy_ai.constants import DATA_SIZE
from trendy_ai.predict import predict

min_sticks = 150

# symbols = healthy_shares()
symbols = CURRENCIES + INDEXES


def random_trendy():
    symbol = random.choice(symbols)
    interval = random.choice([15, 30, 60])

    sticks = get_sticks(symbol, interval)
    sticks = add_ema(sticks)

    for _ in range(100):
        n = random.randint(0, len(sticks) - min_sticks)
        ema_key = 'ema' + str(interval)
        sub_sticks = sticks.iloc[n - 100:n]
        print(f"preticting on {symbol} {interval}")
        trendy = predict(sticks.iloc[n - DATA_SIZE:n])
        if trendy:
            print(f"return {symbol} {interval} on {trendy}")
            return symbol, interval, sub_sticks

    print(f"no good prediction...")
    return None, []
