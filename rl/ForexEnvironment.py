from pandas import DataFrame, Series

from rl.TradingState import TradingState


class ForexEnvironment:
    def __init__(self, input_size, all_sticks: DataFrame):
        self.all_sticks = all_sticks
        self.input_size = input_size
        self.current_step = 0
        self.state = TradingState(self.input_size, self.all_sticks.iloc[:self.input_size])
        self.past_positions = []

    def reset(self):
        self.current_step = 0
        self.state = TradingState(self.input_size, self.all_sticks.iloc[:self.input_size])
        self.past_positions = []

    def calculate_reward(self, action: int) -> float:
        if action == 0 or self.state.current_position['direction'] == 0:
            return 0.0
        elif action == self.state.current_position['direction']:
            return float('-inf')
        else:
            return self.state.current_position['running_profit']

    def step(self, stick: Series, action: int):
        current_reward, closed_position = self.state.update_on_step(stick, action)
        if closed_position is not None:
            self.past_positions.append(closed_position)

        self.current_step += 1

        if self.current_step >= len(self.all_sticks) - 1:
            return 0.0, True
        else:
            done = False
        return current_reward, done

