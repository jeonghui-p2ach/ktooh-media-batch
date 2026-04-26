from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from src.trajectory.datetime_utils import to_utc_naive


def materialize_revised_global_units(
    transition_units: Sequence[Mapping[str, Any]],
    selected_edges: Sequence[Mapping[str, Any]],
) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    units_by_local_id = {
        _string(row.get("local_unit_id")): _normalized_transition_unit(row)
        for row in transition_units
        if _string(row.get("local_unit_id"))
    }
    if not units_by_local_id:
        return (), ()

    succ: dict[str, str] = {}
    pred: dict[str, str] = {}

    for row in selected_edges:
        s = _string(row.get("src_local_unit_id"))
        d = _string(row.get("dst_local_unit_id"))
        if not s or not d or s == d:
            continue
        succ[s] = d
        pred[d] = s

    visited: set[str] = set()
    chains: list[list[str]] = []
    local_unit_ids = sorted(units_by_local_id.keys())

    # Build directed chains
    for uid in local_unit_ids:
        if uid in visited or uid in pred:
            continue

        chain = [uid]
        visited.add(uid)
        cur = uid

        while cur in succ and succ[cur] not in visited:
            cur = succ[cur]
            chain.append(cur)
            visited.add(cur)

        chains.append(chain)

    # Add isolated nodes
    for uid in local_unit_ids:
        if uid not in visited:
            chains.append([uid])
            visited.add(uid)

    # Split repeated cameras
    simple_chains: list[list[str]] = []
    for chain in chains:
        cur_chain: list[str] = []
        seen_cam: set[str] = set()

        for uid in chain:
            row = units_by_local_id[uid]
            cam = row["camera_name"]
            if cam in seen_cam and cur_chain:
                simple_chains.append(cur_chain)
                cur_chain = [uid]
                seen_cam = {cam}
            else:
                cur_chain.append(uid)
                seen_cam.add(cam)

        if cur_chain:
            simple_chains.append(cur_chain)

    base_units: list[dict[str, Any]] = []
    base_members: list[dict[str, Any]] = []
    for k, component in enumerate(simple_chains):
        member_rows = tuple(
            sorted(
                (units_by_local_id[uid] for uid in component),
                key=lambda r: (r["start_time"] is None, r["start_time"], r["end_time"]),
            )
        )
        global_unit_id = f"GU_{k:06d}"

        start_times = tuple(
            row["start_time"] for row in member_rows if row["start_time"] is not None
        )
        end_times = tuple(row["end_time"] for row in member_rows if row["end_time"] is not None)
        confidences = tuple(
            row["local_confidence"] for row in member_rows if row["local_confidence"] is not None
        )

        global_start_time = min(start_times) if start_times else None
        global_end_time = max(end_times) if end_times else None

        cams = tuple(row["camera_name"] for row in member_rows if row["camera_name"])

        base_units.append(
            {
                "global_unit_id": global_unit_id,
                "global_start_time": global_start_time,
                "global_end_time": global_end_time,
                "elapsed_dwell_s": _elapsed_seconds(global_start_time, global_end_time),
                "n_cameras": len(set(cams)),
                "camera_path": ">".join(cams),
                "global_confidence": _mean(confidences),
                "seed_kind": "transition" if len(member_rows) > 1 else "episode",
            }
        )
        for member_order, row in enumerate(member_rows, start=1):
            base_members.append(
                {
                    "global_unit_id": global_unit_id,
                    "local_unit_id": row["local_unit_id"],
                    "camera_name": row["camera_name"],
                    "member_order": member_order,
                    "unit_kind": row["unit_kind"],
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                }
            )
    return tuple(base_units), tuple(base_members)


def _normalized_transition_unit(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "local_unit_id": _string(row.get("local_unit_id")),
        "unit_kind": _string(row.get("unit_kind")) or "transition",
        "camera_name": _string(row.get("camera_name")),
        "start_time": _datetime(row.get("start_time")),
        "end_time": _datetime(row.get("end_time")),
        "local_confidence": _optional_float(row.get("local_confidence")),
    }


def _elapsed_seconds(start_time: datetime | None, end_time: datetime | None) -> float:
    if start_time is None or end_time is None or end_time <= start_time:
        return 0.0
    return float((end_time - start_time).total_seconds())


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def _datetime(value: Any) -> datetime | None:
    return to_utc_naive(value)


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _string(value: Any) -> str:
    return "" if value is None else str(value)
