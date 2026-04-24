from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any


def finalize_global_units(
    base_global_units: Sequence[Mapping[str, Any]],
    assigned_episodes: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    if not base_global_units:
        return ()

    episode_summary = _episode_summary_by_unit(assigned_episodes)
    return tuple(
        _merge_global_unit(row, episode_summary.get(_string(row.get("global_unit_id"))))
        for row in base_global_units
    )


def _merge_global_unit(
    row: Mapping[str, Any],
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "global_unit_id": _string(row.get("global_unit_id")),
        "global_start_time": _datetime(row.get("global_start_time")),
        "global_end_time": _datetime(row.get("global_end_time")),
        "elapsed_dwell_s": float(row.get("elapsed_dwell_s") or 0.0),
        "n_cameras": int(row.get("n_cameras") or 0),
        "camera_path": _string(row.get("camera_path")),
        "global_confidence": _optional_float(row.get("global_confidence")),
        "seed_kind": _string(row.get("seed_kind")),
        "visible_start_time": None if summary is None else summary["visible_start_time"],
        "visible_end_time": None if summary is None else summary["visible_end_time"],
        "visible_episode_count": 0 if summary is None else int(summary["visible_episode_count"]),
        "visible_camera_count": 0 if summary is None else int(summary["visible_camera_count"]),
    }


def _episode_summary_by_unit(
    assigned_episodes: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in assigned_episodes:
        unit_id = _string(row.get("global_unit_id"))
        if not unit_id:
            continue
        start_time = _datetime(row.get("episode_start_time"))
        end_time = _datetime(row.get("episode_end_time"))
        camera_name = _string(row.get("camera_name"))
        current = grouped.get(unit_id)
        if current is None:
            grouped[unit_id] = {
                "visible_start_time": start_time,
                "visible_end_time": end_time,
                "visible_episode_count": 1,
                "visible_camera_count": 1 if camera_name else 0,
                "_camera_names": {camera_name} if camera_name else set(),
            }
            continue
        current["visible_start_time"] = _min_datetime(current["visible_start_time"], start_time)
        current["visible_end_time"] = _max_datetime(current["visible_end_time"], end_time)
        current["visible_episode_count"] = int(current["visible_episode_count"]) + 1
        if camera_name:
            current["_camera_names"].add(camera_name)
            current["visible_camera_count"] = len(current["_camera_names"])
    return {
        unit_id: {
            "visible_start_time": values["visible_start_time"],
            "visible_end_time": values["visible_end_time"],
            "visible_episode_count": values["visible_episode_count"],
            "visible_camera_count": values["visible_camera_count"],
        }
        for unit_id, values in grouped.items()
    }


def _min_datetime(left: datetime | None, right: datetime | None) -> datetime | None:
    if left is None:
        return right
    if right is None:
        return left
    return left if left <= right else right


def _max_datetime(left: datetime | None, right: datetime | None) -> datetime | None:
    if left is None:
        return right
    if right is None:
        return left
    return left if left >= right else right


def _datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value).replace(tzinfo=None)
    return None


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _string(value: Any) -> str:
    return "" if value is None else str(value)
