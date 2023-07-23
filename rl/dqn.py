import random
from collections import namedtuple, deque

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from pandas import Series


class DQN(nn.Module):
    def __init__(self, input_size, output_size):
        super(DQN, self).__init__()
        self.fc1 = nn.Linear(input_size, 404)
        self.fc2 = nn.Linear(404, 1600)
        self.fc21 = nn.Linear(1600, 64)
        self.fc3 = nn.Linear(64, output_size)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc21(x))
        x = self.fc3(x)
        return x


class ReplayMemory:
    def __init__(self, capacity):
        self.memory = deque(maxlen=capacity)
        self.Transition = namedtuple('Transition', ('state', 'action', 'next_state', 'reward'))

    def push(self, *args):
        self.memory.append(self.Transition(*args))

    def sample(self, batch_size):
        return random.sample(self.memory, batch_size)

    def __len__(self):
        return len(self.memory)


def train(model, memory, optimizer, batch_size, device):
    if len(memory) < batch_size:
        return
    transitions = memory.sample(batch_size)
    batch = memory.Transition(*zip(*transitions))

    state_batch = torch.cat(batch.state).to(device)
    action_batch = torch.cat(batch.action).to(device)

    # Convert reward_batch to tensor before concatenating
    reward_batch = [torch.tensor([reward], device=device, dtype=torch.float32) for reward in batch.reward]
    reward_batch = torch.cat(reward_batch)

    # Convert next_state_batch to tensor before concatenating
    next_state_batch = [next_state.clone().detach() for next_state in batch.next_state]
    next_state_batch = torch.cat(next_state_batch)

    q_values = model(state_batch).gather(1, action_batch)
    next_q_values = model(next_state_batch).max(1)[0].detach()
    expected_q_values = reward_batch + 0.99 * next_q_values

    loss = F.smooth_l1_loss(q_values, expected_q_values.unsqueeze(1))
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()


def select_action(state, model, device, n_actions, epsilon):
    if np.random.rand() < epsilon:
        random_action = np.random.choice(np.arange(n_actions), p=[0.2, 0.6, 0.2])
        return torch.tensor([[random_action]], device=device, dtype=torch.long)
    with torch.no_grad():
        prediction = model(state)
        # if prediction[0][0] > 0 or prediction[0][2] > 0:
        #     print(f"valid prediction: {prediction}")
        if np.random.rand() < 0.001:
            print(f"sample prediction: {prediction}")

        if prediction[0][0] * 1.0 > prediction[0][2]:
            return torch.tensor([[0]], device=device, dtype=torch.long)
        elif prediction[0][2] * 1.0 > prediction[0][0]:
            return torch.tensor([[2]], device=device, dtype=torch.long)
        else:
            return torch.tensor([[1]], device=device, dtype=torch.long)


def get_time_and_day(stick_name):
    # Extract hour and minute, and convert to the desired 4-digit integer format
    time_int = int(stick_name.strftime('%H%M'))

    # Extract the day of the week (where Monday = 0, Sunday = 6)
    # We will convert this to your specified format (Sunday = 0, Saturday = 6)
    day_of_week = (stick_name.weekday() + 1) % 7

    return time_int, day_of_week

