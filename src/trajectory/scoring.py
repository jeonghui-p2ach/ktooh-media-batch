from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any


def build_revised_candidate_edges(
    transition_nodes: Sequence[Mapping[str, Any]],
    links_df: Sequence[Mapping[str, Any]],
    offset_df: Sequence[Mapping[str, Any]],
    hour_speed_df: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], ...]:
    links = _distance_lookup(links_df)
    offsets = _distance_lookup(offset_df)
    speeds = _speed_lookup(hour_speed_df)

    exit_nodes = tuple(
        _normalized_node(row)
        for row in transition_nodes
        if _string(row.get("transition_role")).lower() == "exit"
    )
    enter_nodes = tuple(
        _normalized_node(row)
        for row in transition_nodes
        if _string(row.get("transition_role")).lower() == "enter"
    )

    edges: list[dict[str, Any]] = []
    for src in exit_nodes:
        for dst in enter_nodes:
            edge = _build_edge(
                src,
                dst,
                links=links,
                offsets=offsets,
                speeds=speeds,
                cfg=cfg,
            )
            if edge is not None:
                edges.append(edge)
    return tuple(
        sorted(
            edges,
            key=lambda row: (
                float(row["total_edge_cost"]),
                _string(row["src_transition_node_id"]),
                _string(row["dst_transition_node_id"]),
            ),
        )
    )


def _build_edge(
    src: Mapping[str, Any],
    dst: Mapping[str, Any],
    *,
    links: Mapping[tuple[str, str], float],
    offsets: Mapping[tuple[str, str], float],
    speeds: Mapping[int, float],
    cfg: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if src["camera_name"] == dst["camera_name"]:
        return None
    if src["parent_local_unit_id"] == dst["parent_local_unit_id"]:
        return None
    if src["node_time"] is None or dst["node_time"] is None or dst["node_time"] <= src["node_time"]:
        return None

    dt = float((dst["node_time"] - src["node_time"]).total_seconds())
    pair_key = (src["camera_name"], dst["camera_name"])
    if pair_key not in links and pair_key not in offsets:
        return None
    path_dist = links.get(pair_key, offsets.get(pair_key, 0.0))
    
    pair_speed = speeds.get(src["node_time"].hour, 1.0)
    exp_gap = path_dist / max(pair_speed, 0.25)
    
    implied_speed = path_dist / max(dt, 1e-6)
    max_inter_camera_speed_mps = _float_from_cfg(cfg, "max_inter_camera_speed_mps", 4.0)
    if implied_speed > max_inter_camera_speed_mps:
        return None

    gap_resid = abs(dt - exp_gap)
    gap_sigma_factor = _float_from_cfg(cfg, "gap_sigma_factor", 1.0)
    gap_sigma = max(gap_sigma_factor * max(exp_gap, 10.0), 10.0)

    speed_sigma_factor = _float_from_cfg(cfg, "speed_sigma_factor", 0.5)
    speed_sigma = max(speed_sigma_factor * max(pair_speed, 0.5), 0.20)
    speed_resid = abs(implied_speed - pair_speed)

    zone_penalty = 0.0
    s_zone = _string(src.get("boundary_zone_id"))
    d_zone = _string(dst.get("boundary_zone_id"))
    if s_zone and d_zone and s_zone != d_zone:
        zone_penalty = _float_from_cfg(cfg, "zone_mismatch_penalty", 50.0)

    s_score = _optional_float(src.get("transition_score")) or 1.0
    d_score = _optional_float(dst.get("transition_score")) or 1.0
    weak_threshold = _float_from_cfg(cfg, "weak_transition_penalty", 20.0)
    weak_pen = weak_threshold * max(1.0 - min(s_score, d_score), 0.0)

    s_conf = _optional_float(src.get("local_confidence")) or 1.0
    d_conf = _optional_float(dst.get("local_confidence")) or 1.0
    conf_pen = 0.20 * max(1.0 - min(s_conf, d_conf), 0.0)

    total_cost = (
        (gap_resid / gap_sigma) ** 2
        + (speed_resid / speed_sigma) ** 2
        + zone_penalty
        + weak_pen
        + conf_pen
    )

    return {
        "src_transition_node_id": src["transition_node_id"],
        "dst_transition_node_id": dst["transition_node_id"],
        "src_local_unit_id": src["parent_local_unit_id"],
        "dst_local_unit_id": dst["parent_local_unit_id"],
        "src_camera": src["camera_name"],
        "dst_camera": dst["camera_name"],
        "gap_s": dt,
        "shortest_path_dist_m": path_dist,
        "implied_speed_mps": implied_speed,
        "expected_gap_s": exp_gap,
        "total_edge_cost": float(total_cost),
    }


def _normalized_node(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "transition_node_id": _string(row.get("transition_node_id")),
        "parent_local_unit_id": _string(row.get("parent_local_unit_id")),
        "camera_name": _string(row.get("camera_name")),
        "node_time": _datetime(row.get("node_time")),
        "transition_score": _optional_float(row.get("transition_score")),
        "local_confidence": _optional_float(row.get("local_confidence")),
        "boundary_zone_id": _string(row.get("boundary_zone_id")),
    }


def _float_from_cfg(cfg: Mapping[str, Any] | None, key: str, default: float) -> float:
    if not cfg:
        return default
    value = cfg.get(key)
    return default if value is None else float(value)


def _distance_lookup(rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], float]:
    lookup: dict[tuple[str, str], float] = {}
    for row in rows:
        src_camera = _string(row.get("src_camera") or row.get("from_camera"))
        dst_camera = _string(row.get("dst_camera") or row.get("to_camera"))
        if not src_camera or not dst_camera:
            continue
        lookup[(src_camera, dst_camera)] = float(
            row.get("shortest_path_dist_m") or row.get("offset_m") or row.get("distance_m") or 0.0
        )
    return lookup


def _speed_lookup(rows: Sequence[Mapping[str, Any]]) -> dict[int, float]:
    lookup: dict[int, float] = {}
    for row in rows:
        hour = int(row.get("hour") or 0)
        speed = float(row.get("speed_mps") or row.get("expected_speed_mps") or 0.0)
        if speed > 0:
            lookup[hour] = speed
    return lookup


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
