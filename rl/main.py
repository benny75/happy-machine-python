import os.path
import time
from collections import Counter
from typing import List

import numpy as np
import pandas as pd
import torch

from data.SticksEnrichment import add_ema
from data.TimescaleDBSticksDao import get_sticks
from dqn import DQN, ReplayMemory, train, select_action, get_time_and_day
from rl.TradingState import Position
from rl.ForexEnvironment import ForexEnvironment

# Load the sticks data
sticks = get_sticks("CS.D.EURUSD.TODAY.IP", 15)
sticks = add_ema(sticks)


# Set up the DQN model and training parameters
device = torch.device("cpu")
input_size = 402
output_size = 3  # Buy, Sell, Hold
model = DQN(input_size, output_size).to(device)
target_model = DQN(input_size, output_size).to(device)

if os.path.exists("trained_model.pt"):
    model.load_state_dict(torch.load("trained_model.pt"))
target_model.load_state_dict(model.state_dict())
target_model.eval()
optimizer = torch.optim.Adam(model.parameters())
memory = ReplayMemory(len(sticks))
batch_size = 64
n_actions = 3
start_epsilon = 0.0
end_epsilon = 0.0

epsilon_decay_rate = 0.99

env = ForexEnvironment(input_size, sticks)

actions = []


def analyse_end_positions(past_positions: List[Position]):
    if len(past_positions) == 0:
        print("No position to analyse!?")
        return

    df = pd.DataFrame([vars(p) for p in past_positions])
    total_profit = sum(df['running_profit'])
    print(f"Total positions: {len(past_positions)}. Total profit: {total_profit}. Profit per position: {total_profit / len(past_positions)}")

    # Calculate duration in hours
    df['duration'] = (df['close_datetime'] - df['open_datetime']).dt.total_seconds() / 3600

    # Sort DataFrame by running_profit
    df_sorted = df.sort_values('running_profit')

    # Display the top 5 and bottom 5 trades, selecting specific columns
    print("Top 5 trades:")
    print(df_sorted[['open_datetime', 'duration', 'running_profit']].tail(5))
    print("Bottom 5 trades:")
    print(df_sorted[['open_datetime', 'duration', 'running_profit']].head(5))


def create_state_from_stick(i, sticks, env):
    assert i >= 50, "Index out of range. Need at least 50 previous sticks."
    past_50_sticks = sticks.iloc[i - 50:i].copy()  # make a copy to avoid modifying the original dataframe

    # Normalize the OHLC and EMA columns with the last closing price, except for the volume
    last_close_price = past_50_sticks['ask_close'].iloc[-1]
    for col in ['ask_open', 'ask_high', 'ask_low', 'ask_close', 'ema18', 'ema50', 'ema200']:
        past_50_sticks[col] /= last_close_price

    stick_values = past_50_sticks[
        ['ask_open', 'ask_high', 'ask_low', 'ask_close', 'volume', 'ema18', 'ema50', 'ema200']].values.flatten()
    time_int, day_of_week = get_time_and_day(sticks.iloc[i].name)
    additional_info = np.array(
        [time_int, day_of_week])
    state = np.concatenate((stick_values, additional_info))
    state_tensor = torch.tensor(state, device=device, dtype=torch.float).unsqueeze(0)
    assert state_tensor.shape[1] == input_size, f"Expected state of size {input_size}, but got {state_tensor.shape[1]}"
    return state_tensor


for epoch in range(20):
    start_time = time.time()  # Returns the current time in seconds since the epoch
    try:
        # Train the model
        if epoch == 0:
            epsilon = start_epsilon
        elif epsilon < end_epsilon:
            epsilon = end_epsilon
        else:
            epsilon = epsilon * epsilon_decay_rate
        print("=========================================================================================")
        print(f"new episode. epsilon: {epsilon}")
        for i in range(50, len(sticks)-1):
            state = create_state_from_stick(i, sticks, env)
            action = select_action(state, model, device, n_actions, epsilon)
            actions.append(action.item())
            reward, done = env.step(sticks.iloc[i], action.item())
            if done:
                break

            next_state = create_state_from_stick(i+1, sticks, env)
            memory.push(state, action, next_state, reward)
            if i % 10 == 0 and epsilon > 0:
                train(model, memory, optimizer, batch_size, device)

        analyse_end_positions(env.past_positions)
        end_time = time.time()  # Returns the current time again
        elapsed_time = end_time - start_time  # Time in seconds

        for item, count in Counter(actions).items():
            print(f"Action {item} occurs {count} times")
        actions = []

        print(f"epoch {epoch} finished. {elapsed_time} seconds")
        env.reset()
    except KeyboardInterrupt:
        print("KeyboardInterrupt handled")
        break
    if epoch % 10 == 0 and epsilon > 0:
        torch.save(model.state_dict(), "trained_model.pt")

print("training done")
# Save the trained model
if epsilon > 0:
    torch.save(model.state_dict(), "trained_model.pt")
