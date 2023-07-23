from typing import Any

from pandas import DataFrame, Series


class TradingState:
    def __init__(self, window_size: int, init_sticks: DataFrame):
        self.window_size = window_size
        self.sticks = init_sticks
        self.current_position = Position()

    def update_on_step(self, stick: Series, direction: int):
        _direction = direction - 1
        # print(f"direction: {self.current_position.direction} -> {_direction}")

        # nothing happened, no running profit to update
        if _direction == 0 and self.current_position.direction == 0:
            # print(f"0->0 nothing happened")
            return 0.0, None

        # same direction as before, update running profit
        if _direction == 0 and self.current_position.direction != 0:
            current_price = stick['bid_close'] if _direction == 1 else stick['ask_close']
            running_profit = self.current_position.update_running_profit(current_price)
            return running_profit, None

        # same direction as before
        if _direction != 0 and _direction == self.current_position.direction:
            current_price = stick['bid_close'] if _direction == 1 else stick['ask_close']
            running_profit = self.current_position.update_running_profit(current_price)
            return running_profit, None

        # close position
        if self.current_position.direction != 0 and _direction != self.current_position.direction:
            # print(f"closing position")
            current_price = stick['bid_close'] if _direction == 1 else stick['ask_close']
            self.current_position.close_position(stick.name, current_price)
            closed_position = self.current_position
            duration_hours = (closed_position.close_datetime - closed_position.open_datetime).total_seconds() / 3600
            self.current_position = Position()
            profit_per_hour = 0 if duration_hours == 0 else closed_position.running_profit / duration_hours
            reward = closed_position.running_profit * 10 if closed_position.running_profit > 0 else closed_position.running_profit
            return reward, closed_position

        # open position
        if self.current_position.direction == 0 and _direction != self.current_position.direction:
            # print(f"open position")
            open_price = stick['ask_close'] if _direction == 1 else stick['bid_close']
            self.current_position = Position(_direction, open_price, stick.name)
            return 0.0, None

        raise Exception(f"unhandled condition: {_direction}, {self.current_position}")


class Position:
    def __init__(self, direction=0, open_price=0.0, open_datetime=None):
        self.direction = direction  # -1: sell, 0: nothing, 1: buy
        self.open_datetime = open_datetime
        self.open_price = open_price
        self.running_profit = 0.0
        self.close_datetime = None
        self.close_price = None

    def __str__(self):
        return f"Position(direction={self.direction}, datetime={self.open_datetime}/{self.close_datetime}, " \
               f"duration:{self.close_datetime - self.open_datetime} price={self.open_price}/{self.close_price}, " \
               f"running_profit={self.running_profit})"

    def close_position(self, close_datetime=None, close_price=None):
        self.update_running_profit(close_price)
        self.close_datetime = close_datetime
        self.close_price = close_price

    def update_running_profit(self, current_price) -> float:
        running_profit = (current_price - self.open_price) * self.direction
        self.running_profit = running_profit
        return running_profit
