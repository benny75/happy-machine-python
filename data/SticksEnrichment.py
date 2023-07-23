from pandas import DataFrame


def add_ema(sticks_: DataFrame) -> DataFrame:
    sticks = sticks_.copy()
    sticks['ema18'] = sticks['ask_close'].ewm(span=18, adjust=False).mean()
    sticks['ema50'] = sticks['ask_close'].ewm(span=50, adjust=False).mean()
    sticks['ema200'] = sticks['ask_close'].ewm(span=200, adjust=False).mean()
    return sticks
