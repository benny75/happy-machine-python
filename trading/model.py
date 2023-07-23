from enum import Enum

PositionStatus = Enum('PositionStatus', ['PENDING', ])


class Position:
    state = PositionStatus.PENDING

