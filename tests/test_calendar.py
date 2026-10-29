from datetime import datetime

from nem_grid_pulse.calendar import bucket_end_30min, hour_of_day, trading_date


def test_half_hour_bucket_edges():
    assert bucket_end_30min(datetime(2025, 9, 1, 0, 5)) == datetime(2025, 9, 1, 0, 30)
    assert bucket_end_30min(datetime(2025, 9, 1, 0, 30)) == datetime(2025, 9, 1, 0, 30)
    assert bucket_end_30min(datetime(2025, 9, 1, 0, 35)) == datetime(2025, 9, 1, 1, 0)
    assert bucket_end_30min(datetime(2025, 9, 1, 1, 0)) == datetime(2025, 9, 1, 1, 0)
    assert bucket_end_30min(datetime(2025, 9, 1, 23, 55)) == datetime(2025, 9, 2, 0, 0)


def test_trading_date_assigns_midnight_to_the_previous_day():
    assert trading_date(datetime(2025, 9, 2, 0, 0)) == datetime(2025, 9, 1).date()
    assert trading_date(datetime(2025, 9, 1, 0, 5)) == datetime(2025, 9, 1).date()


def test_hour_of_day_uses_the_clock_hour_containing_the_interval():
    assert hour_of_day(datetime(2025, 9, 1, 0, 30)) == 0
    assert hour_of_day(datetime(2025, 9, 1, 1, 0)) == 0
    assert hour_of_day(datetime(2025, 9, 2, 0, 0)) == 23
    assert hour_of_day(datetime(2025, 9, 1, 13, 30)) == 13
