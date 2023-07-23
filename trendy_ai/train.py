import random

import numpy as np
import torch
from sklearn.model_selection import train_test_split

from data.SticksEnrichment import add_ema
from data.TimescaleDBSticksDao import get_sticks
from labeling.DataStore import DataStore
from trendy_ai.TrendyNet import TrendyNet
from trendy_ai.constants import model_path, DATA_SIZE
from trendy_ai.data_processing import flatten_data


def load_data(data):
    def process_data(d):
        sticks = d['sticks']
        ema_key = 'ema' + str(d['ema_n'])
        return flatten_data(sticks, ema_key)

    return [process_data(d) for d in data if 'ema18' in d['sticks']]


def load_random_non_pattern(data):
    dirty_non_pattern_data = []

    def process_data(d):
        n = random.randint(DATA_SIZE, len(d) - DATA_SIZE)
        ema_key = 'ema' + random.choice(['18', '50', '200'])
        sub_sticks = d.iloc[n - DATA_SIZE:n]
        return flatten_data(sub_sticks, ema_key)

    symbol_interval_list = [(d['symbol'], d['interval']) for d in data]
    symbol_interval_set = set(symbol_interval_list)
    for symbol, interval in symbol_interval_set:
        non_pattern_n = symbol_interval_list.count((symbol, interval)) * 3
        sticks = get_sticks(symbol, interval)
        sticks = add_ema(sticks)
        dirty_non_pattern_data.append([process_data(sticks) for _ in range(non_pattern_n)])

    return [inner for outer in dirty_non_pattern_data for inner in outer]


training_data_path = '../labeling/trendy-ema.p'
datastore = DataStore(training_data_path)
raw_data = datastore.read_data()
raw_data = [x for x in raw_data if 'TODAY.IP' in x['symbol'] or x['symbol'] == "CC.D.DX.USS.IP"]
patten_data = load_data([x for x in raw_data if x['is_pattern']])
non_data = load_data([x for x in raw_data if not x['is_pattern']])
generated_non_data = load_random_non_pattern(raw_data)
print(f"have {len(patten_data)} pattern data and {len(generated_non_data)} non pattern data")

X = patten_data + generated_non_data + non_data
Y = [1]*len(patten_data) + [0]*len(generated_non_data + non_data)

X_train_np, X_val_np, Y_train_np, Y_val_np = train_test_split(np.array(X), np.array(Y), test_size=0.2, random_state=42)


# # Initialize the model, optimizer, and loss function
model = TrendyNet(len(X[0]))

# Transform the data into PyTorch tensors
X_train = torch.tensor(X_train_np, dtype=torch.float)
y_train = torch.tensor(Y_train_np, dtype=torch.long)

X_val = torch.tensor(X_val_np, dtype=torch.float)
Y_val = torch.tensor(Y_val_np, dtype=torch.long)


# Training process
for epoch in range(100):
    train_loss = model.train_model(X_train, y_train)
    val_loss = model.validate(X_val, Y_val)
    print(f'Epoch: {epoch + 1}, Training Loss: {train_loss}, Validation Loss: {val_loss}')

torch.save(model.state_dict(), model_path())
