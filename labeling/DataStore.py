import pickle


class DataStore:
    def __init__(self, file_path='trendy-ema.p'):
        self.file_path = file_path
        try:
            with open(self.file_path, 'rb') as f:
                self.data = pickle.load(f)
        except (FileNotFoundError, EOFError):
            self.data = []

    def store_data(self, symbol, interval, is_pattern, is_up, ema_n, sticks):
        # Append new data
        self.data.append({
            'symbol': symbol,
            'interval': interval,
            'is_pattern': is_pattern,
            'is_up': is_up,
            'ema_n': ema_n,
            'sticks': sticks,
        })

        # Write data back to file
        with open(self.file_path, 'wb') as f:
            pickle.dump(self.data, f)

    def read_data(self):
        # Read data from file
        with open(self.file_path, 'rb') as f:
            return pickle.load(f)

# from labeling.DataStore import *
# datastore = DataStore('labeling/trendy-ema.p')
# data = datastore.read_data()
