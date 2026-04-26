from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta
from typing import Any

from src.trajectory.datetime_utils import to_utc_naive
from src.trajectory.intervals import union_interval_seconds


def build_corrected_hourly_metrics(
    global_units: Sequence[Mapping[str, Any]],
    global_presence: Sequence[Mapping[str, Any]],
    *,
    metrics_version: str = "metrics-v1",
) -> tuple[dict[str, Any], ...]:
    # Group presence by camera
    presence_by_camera = defaultdict(list)
    for row in global_presence:
        presence_by_camera[_string(row.get("camera_name"))].append(row)
    
    all_rows = []
    
    # 1. Media-wide metrics (ALL cameras)
    media_hours = _collect_hour_starts(global_units, global_presence)
    for hour_start in media_hours:
        row = _hourly_row(
            hour_start=hour_start,
            global_units=global_units,
            global_presence=global_presence,
            metrics_version=metrics_version,
        )
        row["camera_name"] = "" # Empty means media-wide
        all_rows.append(row)

    # 2. Camera-level metrics
    for camera_name, camera_presence in presence_by_camera.items():
        if not camera_name:
            continue
        hours = _collect_hour_starts(global_units, camera_presence)
        for hour_start in hours:
            row = _hourly_row(
                hour_start=hour_start,
                global_units=global_units,
                global_presence=camera_presence,
                metrics_version=metrics_version,
            )
            row["camera_name"] = camera_name
            all_rows.append(row)
            
    return tuple(all_rows)


def _hourly_row(
    *,
    hour_start: datetime,
    global_units: Sequence[Mapping[str, Any]],
    global_presence: Sequence[Mapping[str, Any]],
    metrics_version: str,
) -> dict[str, Any]:
    hour_end = hour_start + timedelta(hours=1)
    active_units = tuple(
        row
        for row in global_units
        if _overlap_seconds(
            _datetime(row.get("global_start_time")),
            _datetime(row.get("global_end_time")),
            hour_start,
            hour_end,
        )
        > 0
    )
    episode_overlaps = tuple(_episode_overlap(row, hour_start, hour_end) for row in global_presence)
    visible_episodes = tuple(item for item in episode_overlaps if item is not None)
    kpi_episodes = tuple(
        item for item in visible_episodes if bool(item["row"].get("episode_kpi_eligible", False))
    )
    visible_unique_units = {
        _string(item["row"].get("global_unit_id"))
        for item in visible_episodes
        if _string(item["row"].get("global_unit_id"))
    }
    kpi_unique_units = {
        _string(item["row"].get("global_unit_id"))
        for item in kpi_episodes
        if _string(item["row"].get("global_unit_id"))
    }
    visible_cameras = {
        _string(item["row"].get("camera_name"))
        for item in visible_episodes
        if _string(item["row"].get("camera_name"))
    }
    overlap_values = tuple(float(item["overlap_s"]) for item in visible_episodes)
    n_cameras_values = tuple(float(row.get("n_cameras") or 0.0) for row in active_units)
    total_visible_dwell_s = _sum_unioned_dwell(visible_episodes)
    kpi_total_visible_dwell_s = _sum_unioned_dwell(kpi_episodes)

    return {
        "date": hour_start.date(),
        "hour": hour_start.hour,
        "hour_start": hour_start,
        "hour_end": hour_end,
        "unique_global_units": len(
            {
                _string(row.get("global_unit_id"))
                for row in active_units
                if _string(row.get("global_unit_id"))
            }
        ),
        "single_camera_units": sum(
            1 for row in active_units if int(row.get("n_cameras") or 0) == 1
        ),
        "multi_camera_units": sum(1 for row in active_units if int(row.get("n_cameras") or 0) > 1),
        "mean_n_cameras": _mean(n_cameras_values),
        "visible_unique_units": len(visible_unique_units),
        "visible_episode_count": len(visible_episodes),
        "visible_camera_count": len(visible_cameras),
        "kpi_visible_unique_units": len(kpi_unique_units),
        "kpi_visible_episode_count": len(kpi_episodes),
        "total_visible_dwell_s": total_visible_dwell_s,
        "avg_visible_dwell_per_unit_s": _safe_divide(
            total_visible_dwell_s,
            len(visible_unique_units),
        ),
        "median_visible_episode_dwell_s": _percentile(overlap_values, 50),
        "p75_visible_episode_dwell_s": _percentile(overlap_values, 75),
        "p90_visible_episode_dwell_s": _percentile(overlap_values, 90),
        "kpi_total_visible_dwell_s": kpi_total_visible_dwell_s,
        "kpi_avg_visible_dwell_per_unit_s": _safe_divide(
            kpi_total_visible_dwell_s,
            len(kpi_unique_units),
        ),
        "metrics_version": metrics_version,
    }


def _sum_unioned_dwell(episodes: Sequence[Mapping[str, Any]]) -> float:
    intervals_by_gu: defaultdict[str, list[tuple[datetime, datetime]]] = defaultdict(list)
    for item in episodes:
        gu_id = _string(item["row"].get("global_unit_id"))
        if gu_id:
            intervals_by_gu[gu_id].append(item["interval"])

    return sum(union_interval_seconds(intervals) for intervals in intervals_by_gu.values())


def _collect_hour_starts(
    global_units: Sequence[Mapping[str, Any]],
    global_presence: Sequence[Mapping[str, Any]],
) -> tuple[datetime, ...]:
    starts: set[datetime] = set()
    for row in global_units:
        starts.update(
            _hour_range(
                _datetime(row.get("global_start_time")),
                _datetime(row.get("global_end_time")),
            )
        )
    for row in global_presence:
        starts.update(
            _hour_range(
                _datetime(row.get("episode_start_time")),
                _datetime(row.get("episode_end_time")),
            )
        )
    return tuple(sorted(starts))


def _hour_range(start: datetime | None, end: datetime | None) -> tuple[datetime, ...]:
    if start is None or end is None or end <= start:
        return ()
    current = start.replace(minute=0, second=0, microsecond=0)
    final_hour = (end - timedelta(microseconds=1)).replace(minute=0, second=0, microsecond=0)
    hours: list[datetime] = []
    while current <= final_hour:
        hours.append(current)
        current += timedelta(hours=1)
    return tuple(hours)


def _episode_overlap(
    row: Mapping[str, Any],
    hour_start: datetime,
    hour_end: datetime,
) -> dict[str, Any] | None:
    start = _datetime(row.get("episode_start_time"))
    end = _datetime(row.get("episode_end_time"))
    if start is None or end is None or end <= start:
        return None
    overlap_start = max(start, hour_start)
    overlap_end = min(end, hour_end)
    if overlap_end <= overlap_start:
        return None
    return {
        "row": row,
        "overlap_s": float((overlap_end - overlap_start).total_seconds()),
        "interval": (overlap_start, overlap_end),
    }


def _overlap_seconds(
    start: datetime | None,
    end: datetime | None,
    window_start: datetime,
    window_end: datetime,
) -> float:
    if start is None or end is None or end <= start:
        return 0.0
    overlap_start = max(start, window_start)
    overlap_end = min(end, window_end)
    if overlap_end <= overlap_start:
        return 0.0
    return float((overlap_end - overlap_start).total_seconds())


def _percentile(values: Sequence[float], percentile: int) -> float:
    if not values:
        return 0.0
    sorted_values = tuple(sorted(float(value) for value in values))
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * (percentile / 100)
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    fraction = rank - lower_index
    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]
    return float(lower_value + (upper_value - lower_value) * fraction)


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _safe_divide(numerator: float, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator / denominator)


def _datetime(value: Any) -> datetime | None:
    return to_utc_naive(value)


def _string(value: Any) -> str:
    return "" if value is None else str(value)
