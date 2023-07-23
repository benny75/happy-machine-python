from pandas import DataFrame

from trendy_ai.constants import DATA_SIZE


def validate_data(data: DataFrame):
    if 'ema18' not in data:
        raise Exception("ema18 is missing from sticks data")
    if len(data) != DATA_SIZE:
        raise Exception(f"rows sticks does not match DATA_SIZE. {len(data)} vs {DATA_SIZE}")


def flatten_data(sticks: DataFrame, ema_key: str):
    is_up = sticks.iloc[-1].ema200 > sticks.iloc[-1 - int(DATA_SIZE / 2)].ema200
    return flatten_and_normalise(ema_key, is_up, sticks)


def flatten_and_normalise(ema_key, is_up, sticks):
    nom_sticks = __enrich_sticks_with_normalised(ema_key, is_up, sticks)
    return [item for sublist in
            [[row['nom_open'], row['nom_high'], row['nom_low'], row['nom_close'], row['nom_ema'], row['volume']] for idx, row
             in nom_sticks.iterrows()] for item in sublist]


def __enrich_sticks_with_normalised(ema_key, is_up_, sticks_: DataFrame):
    sticks = sticks_.copy()[-DATA_SIZE:]
    is_up = 1 if is_up_ else -1
    nom_value = sticks[ema_key][-1]
    sticks['nom_open'] = (sticks['ask_open'] - nom_value) * is_up
    sticks['nom_high'] = (sticks['ask_high'] - nom_value) * is_up
    sticks['nom_low'] = (sticks['ask_low'] - nom_value) * is_up
    sticks['nom_close'] = (sticks['ask_close'] - nom_value) * is_up
    sticks['nom_ema'] = (sticks[ema_key] - nom_value) * is_up
    return sticks
