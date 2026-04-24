from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any


def assign_episodes_to_global_units(
    episode_units: Sequence[Mapping[str, Any]],
    transition_units: Sequence[Mapping[str, Any]],
    global_members: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    del transition_units
    member_rows = tuple(_normalized_member(row) for row in global_members)
    return tuple(
        assigned
        for row in episode_units
        if (assigned := _assign_episode(row, member_rows)) is not None
    )


def _assign_episode(
    row: Mapping[str, Any],
    member_rows: Sequence[dict[str, Any]],
) -> dict[str, Any] | None:
    local_unit_id = _string(row.get("local_unit_id"))
    camera_name = _string(row.get("camera_name"))
    start_time = _datetime(row.get("start_time"))
    end_time = _datetime(row.get("end_time"))
    if start_time is None or end_time is None or end_time <= start_time:
        return None

    exact_matches = tuple(
        member
        for member in member_rows
        if member["local_unit_id"] == local_unit_id and member["camera_name"] == camera_name
    )
    if exact_matches:
        chosen = _best_member_by_overlap(exact_matches, start_time, end_time)
        if chosen is not None:
            return _assigned_episode_row(row, chosen, assignment_mode="exact_local_unit")

    overlap_matches = tuple(
        member
        for member in member_rows
        if member["camera_name"] == camera_name
        and _overlap_seconds(start_time, end_time, member["start_time"], member["end_time"]) > 0
    )
    if not overlap_matches:
        return None
    chosen = _best_member_by_overlap(overlap_matches, start_time, end_time)
    if chosen is None:
        return None
    return _assigned_episode_row(row, chosen, assignment_mode="overlap_camera")


def _best_member_by_overlap(
    members: Sequence[dict[str, Any]],
    start_time: datetime,
    end_time: datetime,
) -> dict[str, Any] | None:
    ranked = sorted(
        members,
        key=lambda member: (
            -_overlap_seconds(start_time, end_time, member["start_time"], member["end_time"]),
            member["member_order"],
            member["global_unit_id"],
        ),
    )
    return ranked[0] if ranked else None


def _assigned_episode_row(
    row: Mapping[str, Any],
    member: Mapping[str, Any],
    *,
    assignment_mode: str,
) -> dict[str, Any]:
    start_time = _datetime(row.get("start_time"))
    end_time = _datetime(row.get("end_time"))
    return {
        "local_unit_id": _string(row.get("local_unit_id")),
        "camera_name": _string(row.get("camera_name")),
        "episode_start_time": start_time,
        "episode_end_time": end_time,
        "episode_dwell_s": float(row.get("episode_dwell_s") or 0.0),
        "episode_kpi_eligible": bool(row.get("kpi_eligible", False)),
        "global_unit_id": _string(member.get("global_unit_id")),
        "assignment_mode": assignment_mode,
    }


def _normalized_member(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "global_unit_id": _string(row.get("global_unit_id")),
        "local_unit_id": _string(row.get("local_unit_id")),
        "camera_name": _string(row.get("camera_name")),
        "member_order": int(row.get("member_order") or 0),
        "start_time": _datetime(row.get("start_time")),
        "end_time": _datetime(row.get("end_time")),
    }


def _overlap_seconds(
    left_start: datetime | None,
    left_end: datetime | None,
    right_start: datetime | None,
    right_end: datetime | None,
) -> float:
    if None in (left_start, left_end, right_start, right_end):
        return 0.0
    if left_end <= left_start or right_end <= right_start:
        return 0.0
    overlap_start = max(left_start, right_start)
    overlap_end = min(left_end, right_end)
    if overlap_end <= overlap_start:
        return 0.0
    return float((overlap_end - overlap_start).total_seconds())


def _datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value).replace(tzinfo=None)
    return None


def _string(value: Any) -> str:
    return "" if value is None else str(value)
