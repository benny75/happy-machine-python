import datetime
from unittest import TestCase

from data.TimescaleDBSticksDao import get_sticks
from swing_trainer.main import plot_chart


class Test(TestCase):
    def test_plot_chart(self):
        symbol = "CS.D.GBPUSD.TODAY.IP"
        interval = 15
        open_datetime = datetime.datetime.strptime('23-03-03 09:30:00', '%y-%m-%d %H:%M:%S')
        sticks = get_sticks(symbol, interval, open_datetime, open_datetime + datetime.timedelta(days=3))

        plt = plot_chart("test", sticks)
        self.assertIsNotNone(plt)
