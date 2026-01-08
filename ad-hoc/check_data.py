from data.TimescaleDBSticksDao import get_sticks

sticks = get_sticks("XLP", 1440)
# print(sticks.iloc[-1].name)

