from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import pairwise
from math import dist
from pathlib import Path
from typing import Any

from src.trajectory.artifacts import load_pickle_artifact, object_to_rows


def build_revised_global_inputs(local_dir: Path, cfg: Mapping[str, Any] | None) -> dict[str, Any]:
    del cfg
    prepared_all = object_to_rows(load_pickle_artifact(local_dir / "prepared_all.pkl"))
    stitched_df_all = object_to_rows(load_pickle_artifact(local_dir / "stitched_df_all.pkl"))
    presence_episode_df = object_to_rows(
        load_pickle_artifact(local_dir / "presence_episode_df.pkl")
    )
    return build_revised_global_inputs_from_rows(
        prepared_all=prepared_all,
        stitched_df_all=stitched_df_all,
        presence_episode_df=presence_episode_df,
    )


def build_revised_global_inputs_from_rows(
    *,
    prepared_all: Sequence[Mapping[str, Any]],
    stitched_df_all: Sequence[Mapping[str, Any]],
    presence_episode_df: Sequence[Mapping[str, Any]],
) -> dict[str, tuple[dict[str, Any], ...]]:
    del prepared_all
    episode_units = tuple(_episode_unit_row(row) for row in presence_episode_df)
    transition_units = tuple(_transition_unit_row(row) for row in stitched_df_all)
    transition_nodes = tuple(
        node
        for row in transition_units
        for node in _transition_nodes_for_unit(row)
    )
    return {
        "episode_units_df": episode_units,
        "transition_units_df": transition_units,
        "transition_nodes_df": transition_nodes,
    }


def _episode_unit_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "local_unit_id": _string(row.get("episode_id")),
        "unit_kind": "episode",
        "camera_name": _string(row.get("camera_name")),
        "start_time": _datetime(row.get("episode_start_time")),
        "end_time": _datetime(row.get("episode_end_time")),
        "support_tracklet_ids": tuple(_sequence(row.get("support_tracklet_ids"))),
        "local_confidence": _optional_float(row.get("episode_confidence")),
        "kpi_eligible": bool(row.get("episode_kpi_eligible", False)),
        "episode_dwell_s": float(row.get("episode_dwell_s") or 0.0),
        "anchor_xy": _anchor_xy(row.get("anchor_xy"), row.get("start_xy")),
    }


def _transition_unit_row(row: Mapping[str, Any]) -> dict[str, Any]:
    route_points = _route_points(row.get("world_points_arr"))
    return {
        "local_unit_id": _string(row.get("local_unit_id") or row.get("stitched_id")),
        "unit_kind": "transition",
        "camera_name": _string(row.get("camera_name")),
        "start_time": _datetime(row.get("start_time")),
        "end_time": _datetime(row.get("end_time")),
        "support_tracklet_ids": tuple(_sequence(row.get("raw_tracklet_ids"))),
        "local_confidence": _optional_float(row.get("local_confidence")),
        "kpi_eligible": bool(row.get("kpi_eligible", False)),
        "route_points": route_points,
        "dwell_s": _elapsed_seconds(
            _datetime(row.get("start_time")),
            _datetime(row.get("end_time")),
        ),
        "route_length_m": _route_length(route_points),
        "is_transition_support": len(route_points) > 1,
    }


def _transition_nodes_for_unit(row: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    local_unit_id = _string(row.get("local_unit_id"))
    camera_name = _string(row.get("camera_name"))
    route_points = tuple(_route_points(row.get("route_points")))
    start_time = _datetime(row.get("start_time"))
    end_time = _datetime(row.get("end_time"))
    transition_score = _optional_float(row.get("local_confidence")) or 0.0
    start_xy = route_points[0] if route_points else None
    end_xy = route_points[-1] if route_points else None
    return (
        {
            "transition_node_id": f"{local_unit_id}:enter",
            "parent_local_unit_id": local_unit_id,
            "camera_name": camera_name,
            "transition_role": "enter",
            "node_time": start_time,
            "node_xy": start_xy,
            "boundary_zone_id": "",
            "dist_to_zone_m": 0.0,
            "transition_score": transition_score,
        },
        {
            "transition_node_id": f"{local_unit_id}:exit",
            "parent_local_unit_id": local_unit_id,
            "camera_name": camera_name,
            "transition_role": "exit",
            "node_time": end_time,
            "node_xy": end_xy,
            "boundary_zone_id": "",
            "dist_to_zone_m": 0.0,
            "transition_score": transition_score,
        },
    )


def _route_points(value: Any) -> tuple[tuple[float, float], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    points: list[tuple[float, float]] = []
    for item in value:
        if not isinstance(item, Sequence) or len(item) < 2:
            continue
        points.append((float(item[0]), float(item[1])))
    return tuple(points)


def _route_length(points: Sequence[tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    return float(sum(dist(left, right) for left, right in pairwise(points)))


def _elapsed_seconds(start_time: Any, end_time: Any) -> float:
    if start_time is None or end_time is None or end_time <= start_time:
        return 0.0
    return float((end_time - start_time).total_seconds())


def _anchor_xy(anchor_xy: Any, start_xy: Any) -> tuple[float, float] | None:
    source = anchor_xy if anchor_xy is not None else start_xy
    if not isinstance(source, Sequence) or len(source) < 2:
        return None
    return (float(source[0]), float(source[1]))


def _datetime(value: Any) -> Any:
    from datetime import datetime

    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value).replace(tzinfo=None)
    return None


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _sequence(value: Any) -> tuple[Any, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(value)
    return ()


def _string(value: Any) -> str:
    return "" if value is None else str(value)
