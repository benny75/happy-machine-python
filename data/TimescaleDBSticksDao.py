import psycopg2
from datetime import datetime, timezone
from psycopg2.extras import RealDictCursor
import msgpack
import pandas as pd
import pytz

from data.db_config import get_db_connection, get_migration_db_connection

def get_sticks(symbol, interval, from_time: datetime = datetime.min, to_time: datetime = datetime.max, limit: int = None):
    connection = get_db_connection()

    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        if from_time != datetime.min and to_time != datetime.max:
            query = """
            SELECT compressed_sticks FROM stick WHERE symbol = %s AND interval = %s AND
            start_date <= %s AND end_date >= %s
            ORDER BY start_date DESC
            """
            if limit:
                query += f" LIMIT {limit}"
            cursor.execute(query, (symbol, interval, to_time, from_time))
        else:
            query = """
            SELECT compressed_sticks FROM stick WHERE symbol = %s AND interval = %s
            ORDER BY start_date DESC
            """
            if limit:
                query += f" LIMIT {limit}"
            cursor.execute(query, (symbol, interval))

        rows = cursor.fetchall()
    connection.close()

    decoded_sticks_list = [msgpack.unpackb(row['compressed_sticks'], raw=False) for row in rows]
    flat_sticks_list = [stick for dsl in decoded_sticks_list for stick in _explode_sticks_msg(symbol, interval, dsl)]

    stick_dicts = [
        {
            "stick_datetime": stick['stickDatetime'],
            "ask_open": stick['askOpen'],
            "ask_high": stick['askHigh'],
            "ask_low": stick['askLow'],
            "ask_close": stick['askClose'],
            "bid_open": stick['bidOpen'],
            "bid_high": stick['bidHigh'],
            "bid_low": stick['bidLow'],
            "bid_close": stick['bidClose'],
            "volume": stick['volume'],
            "epoch_utc_ms": stick['epochUtcMs'],
        }
        for stick in flat_sticks_list
    ]

    sticks_df = pd.DataFrame(stick_dicts).set_index("stick_datetime")

    if from_time is not None and to_time is not None:
        from_time_tzaware = from_time.replace(tzinfo=pytz.UTC)
        to_time_tzaware = to_time.replace(tzinfo=pytz.UTC)
        sticks_df = sticks_df.loc[(sticks_df['volume'] != 0) &
                                  (sticks_df.index >= from_time_tzaware) & (sticks_df.index <= to_time_tzaware)]
    else:
        sticks_df = sticks_df.loc[(sticks_df['volume'] != 0)]

    return sticks_df


def get_all_symbols():
    connection = get_migration_db_connection()

    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        query = """
        SELECT DISTINCT symbol FROM stick
        """
        cursor.execute(query)
        rows = cursor.fetchall()
    connection.close()

    symbols = [row['symbol'] for row in rows]
    return symbols


def _undiff_list(input_list):
    return [sum(input_list[:i + 1]) for i in range(len(input_list))]


def _explode_sticks_msg(symbol, interval, sticks_msg):
    epochs = _undiff_list(sticks_msg['epoch'])
    ask_opens = _undiff_list(sticks_msg['askOpen'])
    ask_highs = _undiff_list(sticks_msg['askHigh'])
    ask_lows = _undiff_list(sticks_msg['askLow'])
    ask_closes = _undiff_list(sticks_msg['askClose'])
    bid_opens = _undiff_list(sticks_msg['bidOpen'])
    bid_highs = _undiff_list(sticks_msg['bidHigh'])
    bid_lows = _undiff_list(sticks_msg['bidLow'])
    bid_closes = _undiff_list(sticks_msg['bidClose'])
    volumes = _undiff_list(sticks_msg['volume'])

    sticks = []
    for i in range(len(epochs)):
        stick_datetime = datetime.fromtimestamp(epochs[i], timezone.utc)
        stick = {
            'stickDatetime': stick_datetime,
            'askOpen': ask_opens[i],
            'askHigh': ask_highs[i],
            'askLow': ask_lows[i],
            'askClose': ask_closes[i],
            'bidOpen': bid_opens[i],
            'bidHigh': bid_highs[i],
            'bidLow': bid_lows[i],
            'bidClose': bid_closes[i],
            'volume': volumes[i],
            'interval': interval,
            'epochUtcMs': epochs[i] * 1000
        }
        sticks.append(stick)

    return sticks
