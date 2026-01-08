import random

import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS
from pandas import Timestamp

from data.SticksEnrichment import add_ema
from data.Symbols import healthy_shares
from data.TimescaleDBSticksDao import get_sticks
from labeling.DataStore import DataStore

app = Flask(__name__)
CORS(app)
data_store = DataStore()

default_sticks = None
min_sticks = 150


def df_to_dict(df: pd.DataFrame):
    return [{
        "time": idx.strftime('%Y-%m-%d %H:%M:%S'),  # Assumes index is a datetime
        "open": row['ask_open'],
        "high": row['ask_high'],
        "low": row['ask_low'],
        "close": row['ask_close'],
        "volume": row['volume'],
        "ema18": row['ema18'],
        "ema50": row['ema50'],
        "ema200": row['ema200'],
    } for idx, row in df.iterrows()]


@app.route('/api/candlestick', methods=['GET'])
def get_candlestick_data():
    global default_sticks
    symbol = "CS.D.EURUSD.TODAY.IP"
    if not default_sticks:
        default_sticks = get_sticks(symbol, 15)
        default_sticks = add_ema(default_sticks)
    sticks = default_sticks
    n = random.randint(0, len(sticks) - min_sticks)
    sticks_to_plot = sticks[n:n + min_sticks]

    return jsonify({
        "symbol": symbol,
        "candlesticks": df_to_dict(sticks_to_plot)
    })


@app.route('/api/random/candlestick', methods=['GET'])
def get_random_candlestick_data():
    symbols = healthy_shares()
    symbol = random.choice(symbols)
    interval = random.choice([15, 30, 60, 1440])
    sticks = get_sticks(symbol, interval)
    sticks = add_ema(sticks)

    n = random.randint(0, len(sticks) - min_sticks)
    sticks_to_plot = sticks[n:n + min_sticks]

    return jsonify({
        "symbol": symbol,
        "interval": interval,
        "candlesticks": df_to_dict(sticks_to_plot)
    })


@app.route('/api/ml/label', methods=['POST'])
def add_label():
    data = request.get_json(force=True)

    datetime_str = data.get('datetime')
    symbol = data.get('symbol')
    is_pattern = data.get('is_pattern')
    interval = float(data.get('interval'))
    timestamp = Timestamp(datetime_str, tz='UTC')
    sticks = get_sticks(symbol, interval, to_time=timestamp)  # get up to todate
    sticks = add_ema(sticks)
    label_sticks = sticks.iloc[-100:]

    ema_period = data.get('ema')
    is_up = sticks.ema200[-1] > sticks.ema200[-100]

    print(f"adding label {label_sticks.index[0]} {ema_period}")
    data_store.store_data(symbol, interval, is_pattern, is_up, ema_period, label_sticks)

    return jsonify({
            'symbol': symbol,
            'interval': interval,
            'is_pattern': is_pattern,
            'is_up': str(is_up),
            'ema_n': ema_period,
        }), 201


# @app.route('/api/ml/random_trendy', methods=['GET'])
# def get_random_trendy_sticks():
#     try:
#         symbol, interval, sub_sticks = random_trendy()
#         return jsonify(
#         {
#             "symbol": symbol,
#             'interval': interval,
#             "candlesticks": df_to_dict(sub_sticks)
#         })
#     except:
#         return jsonify({"error": "something went wrong."}), 500


# @app.route('/api/ml/predict', methods=['POST'])
# def predict():
#     data = request.get_json(force=True)
#     sticks_json = data['sticks']
#     df = __sticks_to_dataframe(sticks_json)
#
#     if df is None or len(df) < 150:
#         return jsonify({"error": "Invalid data. 'sticks' length must be at least 150."}), 400
#
#     df = add_ema(df)
#     print(f"predicting sticks starting from {df.index[0]}")
#
#     from trendy_ai.ffnn.predict import predict
#     response = predict(df)
#     print(f"result: {response}")
#
#     return response


def __sticks_to_dataframe(sticks_json):
    # Convert JSON to pandas DataFrame
    sticks_df = pd.DataFrame(sticks_json)

    # Convert stickDatetime to datetime and set it as index
    sticks_df['stickDatetime'] = sticks_df['stickDatetime'].str.split("[", expand=True)[0]
    sticks_df['stickDatetime'] = pd.to_datetime(sticks_df['stickDatetime']).dt.tz_convert(None)
    sticks_df.set_index('stickDatetime', inplace=True)

    # Select only necessary columns (ask prices) and rename them
    selected_df = sticks_df[['askOpen', 'askHigh', 'askLow', 'askClose', 'volume']].copy()
    selected_df.columns = ['ask_open', 'ask_high', 'ask_low', 'ask_close', 'volume']

    return selected_df


if __name__ == '__main__':
    app.run(debug=False, port=5001, threaded=True)
