from datetime import datetime, timedelta

from src.trajectory.intervals import union_interval_seconds


def test_union_interval_seconds_empty() -> None:
    assert union_interval_seconds([]) == 0.0


def test_union_interval_seconds_no_overlap() -> None:
    t0 = datetime(2026, 1, 1, 12, 0, 0)
    intervals = [
        (t0, t0 + timedelta(seconds=10)),
        (t0 + timedelta(seconds=20), t0 + timedelta(seconds=35)),
    ]
    # 10s + 15s = 25s
    assert union_interval_seconds(intervals) == 25.0


def test_union_interval_seconds_full_overlap() -> None:
    t0 = datetime(2026, 1, 1, 12, 0, 0)
    intervals = [
        (t0, t0 + timedelta(seconds=30)),
        (t0 + timedelta(seconds=10), t0 + timedelta(seconds=20)),
    ]
    # second interval is fully inside the first -> 30s
    assert union_interval_seconds(intervals) == 30.0


def test_union_interval_seconds_partial_overlap() -> None:
    t0 = datetime(2026, 1, 1, 12, 0, 0)
    intervals = [
        (t0, t0 + timedelta(seconds=20)),
        (t0 + timedelta(seconds=10), t0 + timedelta(seconds=30)),
    ]
    # overlaps from 10 to 20 -> union is 0 to 30 -> 30s
    assert union_interval_seconds(intervals) == 30.0


def test_union_interval_seconds_multiple_overlaps() -> None:
    t0 = datetime(2026, 1, 1, 12, 0, 0)
    intervals = [
        (t0, t0 + timedelta(seconds=10)),
        (t0 + timedelta(seconds=5), t0 + timedelta(seconds=15)),
        (t0 + timedelta(seconds=12), t0 + timedelta(seconds=20)),
        (t0 + timedelta(seconds=30), t0 + timedelta(seconds=40)),
    ]
    # First group: 0 to 20 -> 20s
    # Second group: 30 to 40 -> 10s
    # Total: 30s
    assert union_interval_seconds(intervals) == 30.0
