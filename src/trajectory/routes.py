from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from statistics import median
from typing import Any

from src.trajectory.intervals import union_interval_seconds


def build_route_family_table(
    global_units: Sequence[Mapping[str, Any]],
    global_presence: Sequence[Mapping[str, Any]],
    *,
    route_grid_version: str = "route-grid-v1",
) -> tuple[dict[str, Any], ...]:
    if not global_units:
        return ()

    visible_dwell_by_unit = _visible_dwell_by_unit(global_presence)
    grouped_units: dict[str, list[Mapping[str, Any]]] = {}
    for row in global_units:
        camera_path = _string(row.get("camera_path"))
        if not camera_path:
            continue
        grouped_units.setdefault(camera_path, []).append(row)

    return tuple(
        _route_family_row(
            camera_path,
            rows,
            visible_dwell_by_unit,
            route_grid_version=route_grid_version,
        )
        for camera_path, rows in sorted(grouped_units.items())
    )


def _route_family_row(
    camera_path: str,
    rows: Sequence[Mapping[str, Any]],
    visible_dwell_by_unit: Mapping[str, float],
    *,
    route_grid_version: str,
) -> dict[str, Any]:
    unit_ids = tuple(
        _string(row.get("global_unit_id"))
        for row in rows
        if _string(row.get("global_unit_id"))
    )
    visible_dwells = tuple(
        visible_dwell_by_unit[unit_id]
        for unit_id in unit_ids
        if visible_dwell_by_unit.get(unit_id, 0.0) > 0
    )
    confidences = tuple(
        float(row["global_confidence"])
        for row in rows
        if row.get("global_confidence") is not None
    )
    elapsed_dwells = tuple(float(row.get("elapsed_dwell_s") or 0.0) for row in rows)

    return {
        "route_family_id": f"RF_{camera_path.replace('>', '_')}",
        "camera_path": camera_path,
        "unit_count": len(unit_ids),
        "visible_unit_count": len(visible_dwells),
        "median_visible_dwell_s": _median(visible_dwells),
        "mean_route_confidence": _mean(confidences),
        "median_elapsed_s": _median(elapsed_dwells),
        "route_grid_version": route_grid_version,
    }


def _visible_dwell_by_unit(
    global_presence: Sequence[Mapping[str, Any]],
) -> dict[str, float]:
    intervals_by_unit: dict[str, list[tuple[datetime, datetime]]] = {}
    for row in global_presence:
        unit_id = _string(row.get("global_unit_id"))
        if not unit_id:
            continue
        start = row.get("episode_start_time")
        end = row.get("episode_end_time")
        if not isinstance(start, datetime) or not isinstance(end, datetime) or end <= start:
            continue
        intervals_by_unit.setdefault(unit_id, []).append((start, end))
    return {
        unit_id: union_interval_seconds(intervals)
        for unit_id, intervals in intervals_by_unit.items()
    }


def _median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return float(median(values))


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def _string(value: Any) -> str:
    return "" if value is None else str(value)
