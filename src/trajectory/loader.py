from __future__ import annotations

import pickle
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from src.trajectory.artifacts import object_to_rows
from src.trajectory.contracts import ArtifactRef
from src.trajectory.datetime_utils import to_utc_naive
from src.trajectory.spatial import (
    CameraGeoTransform,
    SpatialCellConfig,
    cell_centroid_from_id,
    cell_id_for_geo,
    extract_xy_points,
    world_xy_to_geo,
)

ArtifactRows = Mapping[str, Sequence[Mapping[str, Any]]]


@dataclass(frozen=True, slots=True)
class CameraCodeMapping:
    camera_name: str
    camera_code: str


@dataclass(frozen=True, slots=True)
class TrajectoryLoadContext:
    target_date: date
    media_id: int
    camera_codes: tuple[CameraCodeMapping, ...] = ()
    campaign_id: int | None = None
    creative_id: int | None = None
    source_batch_id: str | None = None
    pipeline_version: str | None = None
    config_version: str | None = None
    spatial_cell: SpatialCellConfig = field(
        default_factory=lambda: SpatialCellConfig(zoom=18, cell_size_degrees=0.0001)
    )
    geo_transforms: tuple[CameraGeoTransform, ...] = ()


@dataclass(frozen=True, slots=True)
class TrajectoryDashboardRows:
    presence_episodes: tuple[dict[str, Any], ...]
    global_units: tuple[dict[str, Any], ...]
    global_presence_episodes: tuple[dict[str, Any], ...]
    hourly_metrics: tuple[dict[str, Any], ...]
    route_families: tuple[dict[str, Any], ...]
    spatial_heatmap_cells: tuple[dict[str, Any], ...]

    @property
    def total_count(self) -> int:
        return sum(
            len(rows)
            for rows in (
                self.presence_episodes,
                self.global_units,
                self.global_presence_episodes,
                self.hourly_metrics,
                self.route_families,
                self.spatial_heatmap_cells,
            )
        )


TABLE_ROW_ATTRS: Mapping[str, str] = {
    "trajectory_presence_episodes": "presence_episodes",
    "trajectory_global_units": "global_units",
    "trajectory_global_presence_episodes": "global_presence_episodes",
    "trajectory_hourly_metrics": "hourly_metrics",
    "trajectory_route_families": "route_families",
    "trajectory_spatial_heatmap_cells": "spatial_heatmap_cells",
}


def load_artifact_rows(
    artifact_refs: tuple[ArtifactRef, ...],
) -> dict[str, tuple[dict[str, Any], ...]]:
    return {
        artifact_ref.spec.name: read_artifact_rows(artifact_ref.path)
        for artifact_ref in artifact_refs
        if artifact_ref.spec.artifact_format == "pkl"
    }


def read_artifact_rows(path: Path) -> tuple[dict[str, Any], ...]:
    with path.open("rb") as file:
        value = pickle.load(file)
    return object_to_rows(value)


def build_dashboard_rows(
    artifact_rows: ArtifactRows,
    context: TrajectoryLoadContext,
) -> TrajectoryDashboardRows:
    return TrajectoryDashboardRows(
        presence_episodes=tuple(
            _presence_episode_row(row, context)
            for row in artifact_rows.get("presence_episode_df", ())
        ),
        global_units=tuple(
            _global_unit_row(row, context)
            for row in artifact_rows.get("global_units_df", ())
        ),
        global_presence_episodes=tuple(
            _global_presence_episode_row(row, context)
            for row in artifact_rows.get("global_presence_episode_df", ())
        ),
        hourly_metrics=tuple(
            _hourly_metric_row(row, context)
            for row in artifact_rows.get("hourly_metric_summary_df", ())
        ),
        route_families=tuple(
            _route_family_row(row, context)
            for row in artifact_rows.get("route_family_df", ())
        ),
        spatial_heatmap_cells=build_spatial_heatmap_cells(
            artifact_rows.get("transition_units_df", ()),
            context,
        ),
    )


def persist_dashboard_rows(
    rows: TrajectoryDashboardRows,
    *,
    database_url: str | None,
    media_id: int,
    target_date: date,
    dry_run: bool,
) -> int:
    if dry_run or not database_url or rows.total_count == 0:
        return rows.total_count
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            for table_name, attr_name in TABLE_ROW_ATTRS.items():
                table_rows = tuple(getattr(rows, attr_name))
                connection.execute(
                    text(
                        f"""
                        DELETE FROM {table_name}
                        WHERE media_id = :media_id
                          AND target_date = :target_date
                        """
                    ),
                    {"media_id": media_id, "target_date": target_date},
                )
                if table_rows:
                    columns = tuple(table_rows[0].keys())
                    connection.execute(
                        text(
                            f"""
                            INSERT INTO {table_name} ({", ".join(columns)})
                            VALUES ({", ".join(f":{column}" for column in columns)})
                            """
                        ),
                        list(table_rows),
                    )
    finally:
        engine.dispose()
    return rows.total_count


def build_spatial_heatmap_cells(
    transition_rows: Sequence[Mapping[str, Any]],
    context: TrajectoryLoadContext,
) -> tuple[dict[str, Any], ...]:
    transform_by_camera = {item.camera_code: item for item in context.geo_transforms}
    grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
    # Track units per cell+hour to avoid double counting dwell
    unit_cell_hour_dwell: set[tuple[str, str, int]] = set()

    for row in transition_rows:
        camera_name = _string(row.get("camera_name"), "unknown")
        camera_code = _camera_code(camera_name, context)
        transform = transform_by_camera.get(camera_code)
        if transform is None:
            continue
        
        unit_id = _string(row.get("local_unit_id"), "")
        dwell_s = _float(row.get("dwell_s"))
        start_time = _datetime(row.get("start_time"), _midnight(context.target_date))
        hour = start_time.hour

        for point in extract_xy_points(row.get("route_points")):
            geo_point = world_xy_to_geo(point, transform)
            cell_id = cell_id_for_geo(camera_code, geo_point, context.spatial_cell)
            key = (
                context.target_date,
                context.media_id,
                camera_code,
                context.campaign_id,
                context.creative_id,
                hour,
                cell_id,
            )
            
            centroid = cell_centroid_from_id(cell_id, context.spatial_cell)
            current = grouped.get(key)
            
            # Unit+Cell+Hour dwell tracking
            uch_key = (unit_id, cell_id, hour)
            add_dwell = 0.0
            if uch_key not in unit_cell_hour_dwell:
                add_dwell = dwell_s
                unit_cell_hour_dwell.add(uch_key)

            if current is None:
                grouped[key] = {
                    "target_date": context.target_date,
                    "media_id": context.media_id,
                    "camera_code": camera_code,
                    "camera_name": camera_name,
                    "campaign_id": context.campaign_id,
                    "creative_id": context.creative_id,
                    "hour": hour,
                    "cell_id": cell_id,
                    "cell_centroid_lat": centroid.lat,
                    "cell_centroid_lng": centroid.lng,
                    "cell_geojson": None,
                    "cell_polygon_wkt": None,
                    "point_count": 1,
                    "visible_unique_units": 1,
                    "total_visible_dwell_s": add_dwell,
                    "heatmap_value": 1,
                    "spatial_ref": context.spatial_ref if hasattr(context, 'spatial_ref') else context.spatial_cell.spatial_ref,
                    "source_batch_id": context.source_batch_id,
                    "_unit_ids": {unit_id},
                }
            else:
                current["point_count"] += 1
                current["heatmap_value"] = current["point_count"]
                current["total_visible_dwell_s"] += add_dwell
                if unit_id not in current["_unit_ids"]:
                    current["visible_unique_units"] += 1
                    current["_unit_ids"].add(unit_id)

    return tuple(_without_internal_keys(row) for row in grouped.values())


def _presence_episode_row(row: Mapping[str, Any], context: TrajectoryLoadContext) -> dict[str, Any]:
    camera_name = _string(row.get("camera_name"), "unknown")
    return {
        "target_date": context.target_date,
        "media_id": context.media_id,
        "camera_code": _camera_code(camera_name, context),
        "local_unit_id": _string(row.get("local_unit_id") or row.get("episode_id"), ""),
        "camera_name": camera_name,
        "campaign_id": context.campaign_id,
        "creative_id": context.creative_id,
        "episode_id": _string(row.get("episode_id"), ""),
        "episode_start_time": _datetime(
            row.get("episode_start_time"),
            _midnight(context.target_date),
        ),
        "episode_end_time": _datetime(row.get("episode_end_time"), _midnight(context.target_date)),
        "episode_dwell_s": _float(row.get("episode_dwell_s")),
        "kpi_eligible": bool(row.get("episode_kpi_eligible", False)),
        "local_confidence": _optional_float(row.get("episode_confidence")),
        "support_tracklet_ids": _string(row.get("support_tracklet_ids"), ""),
        "support_tracklet_count": len(_sequence(row.get("support_tracklet_ids"))),
        "source_batch_id": context.source_batch_id,
        "pipeline_version": context.pipeline_version,
        "created_at_utc": _now_utc_naive(),
    }


def _global_unit_row(row: Mapping[str, Any], context: TrajectoryLoadContext) -> dict[str, Any]:
    camera_path = _string(row.get("camera_path"), "")
    camera_name = camera_path.split(">")[0] if camera_path else _string(row.get("camera_name"), "")
    return {
        "target_date": context.target_date,
        "media_id": context.media_id,
        "camera_code": _camera_code(camera_name, context),
        "global_unit_id": _string(row.get("global_unit_id"), ""),
        "campaign_id": context.campaign_id,
        "creative_id": context.creative_id,
        "seed_kind": _string(row.get("seed_kind"), "unknown"),
        "global_start_time": _datetime(
            row.get("global_start_time"),
            _midnight(context.target_date),
        ),
        "global_end_time": _datetime(row.get("global_end_time"), _midnight(context.target_date)),
        "elapsed_dwell_s": _float(row.get("elapsed_dwell_s")),
        "n_cameras": _int(row.get("n_cameras")),
        "camera_path": camera_path,
        "global_confidence": _optional_float(row.get("global_confidence")),
        "visible_start_time": _optional_datetime(row.get("visible_start_time")),
        "visible_end_time": _optional_datetime(row.get("visible_end_time")),
        "visible_episode_count": _int(row.get("visible_episode_count")),
        "visible_camera_count": _int(row.get("visible_camera_count")),
        "config_version": context.config_version,
        "repeated_camera_validation": "not_evaluated",
        "source_batch_id": context.source_batch_id,
        "pipeline_version": context.pipeline_version,
        "created_at_utc": _now_utc_naive(),
    }


def _global_presence_episode_row(
    row: Mapping[str, Any],
    context: TrajectoryLoadContext,
) -> dict[str, Any]:
    camera_name = _string(row.get("camera_name"), "unknown")
    return {
        "target_date": context.target_date,
        "media_id": context.media_id,
        "camera_code": _camera_code(camera_name, context),
        "global_unit_id": _string(row.get("global_unit_id"), ""),
        "local_unit_id": _string(row.get("local_unit_id"), ""),
        "camera_name": camera_name,
        "campaign_id": context.campaign_id,
        "creative_id": context.creative_id,
        "episode_start_time": _datetime(
            row.get("episode_start_time"),
            _midnight(context.target_date),
        ),
        "episode_end_time": _datetime(row.get("episode_end_time"), _midnight(context.target_date)),
        "episode_dwell_s": _float(row.get("episode_dwell_s")),
        "episode_kpi_eligible": bool(row.get("episode_kpi_eligible", False)),
        "assignment_mode": _string(row.get("assignment_mode"), "unknown"),
        "source_batch_id": context.source_batch_id,
        "pipeline_version": context.pipeline_version,
        "created_at_utc": _now_utc_naive(),
    }


def _hourly_metric_row(row: Mapping[str, Any], context: TrajectoryLoadContext) -> dict[str, Any]:
    hour_start = _datetime(row.get("hour_start"), _midnight(context.target_date))
    # camera_name should be provided by metrics logic. 
    # Fallback only to the first camera if it's explicitly intended for media-wide rows (not recommended).
    camera_name = _string(row.get("camera_name"), "")
    if not camera_name and context.camera_codes:
        # Warning: ambiguous attribution
        camera_name = context.camera_codes[0].camera_name
    return {
        "target_date": context.target_date,
        "media_id": context.media_id,
        "camera_code": _camera_code(camera_name, context),
        "campaign_id": context.campaign_id,
        "creative_id": context.creative_id,
        "date": _date(row.get("date"), context.target_date),
        "hour": _int(row.get("hour", hour_start.hour)),
        "hour_start": hour_start,
        "hour_end": _datetime(row.get("hour_end"), hour_start),
        "unique_global_units": _int(row.get("unique_global_units")),
        "single_camera_units": _int(row.get("single_camera_units")),
        "multi_camera_units": _int(row.get("multi_camera_units")),
        "mean_n_cameras": _float(row.get("mean_n_cameras")),
        "visible_unique_units": _int(row.get("visible_unique_units")),
        "visible_episode_count": _int(row.get("visible_episode_count")),
        "visible_camera_count": _int(row.get("visible_camera_count")),
        "kpi_visible_unique_units": _int(row.get("kpi_visible_unique_units")),
        "kpi_visible_episode_count": _int(row.get("kpi_visible_episode_count")),
        "total_visible_dwell_s": _float(row.get("total_visible_dwell_s")),
        "avg_visible_dwell_per_unit_s": _float(row.get("avg_visible_dwell_per_unit_s")),
        "median_visible_episode_dwell_s": _float(row.get("median_visible_episode_dwell_s")),
        "p75_visible_episode_dwell_s": _float(row.get("p75_visible_episode_dwell_s")),
        "p90_visible_episode_dwell_s": _float(row.get("p90_visible_episode_dwell_s")),
        "kpi_total_visible_dwell_s": _float(row.get("kpi_total_visible_dwell_s")),
        "kpi_avg_visible_dwell_per_unit_s": _float(row.get("kpi_avg_visible_dwell_per_unit_s")),
        "metrics_version": _string(row.get("metrics_version"), context.pipeline_version or ""),
        "source_batch_id": context.source_batch_id,
    }


def _route_family_row(row: Mapping[str, Any], context: TrajectoryLoadContext) -> dict[str, Any]:
    camera_path = _string(row.get("camera_path"), "")
    camera_name = camera_path.split(">")[0] if camera_path else _string(row.get("camera_name"), "")
    return {
        "target_date": context.target_date,
        "media_id": context.media_id,
        "camera_code": _camera_code(camera_name, context),
        "campaign_id": context.campaign_id,
        "creative_id": context.creative_id,
        "route_family_id": _string(row.get("route_family_id"), ""),
        "camera_path": camera_path,
        "unit_count": _int(row.get("unit_count")),
        "visible_unit_count": _int(row.get("visible_unit_count")),
        "median_visible_dwell_s": _float(row.get("median_visible_dwell_s")),
        "mean_route_confidence": _optional_float(row.get("mean_route_confidence")),
        "median_elapsed_s": _float(row.get("median_elapsed_s")),
        "route_grid_version": _string(row.get("route_grid_version"), ""),
        "source_batch_id": context.source_batch_id,
    }


def _camera_code(camera_name: str, context: TrajectoryLoadContext) -> str:
    matches = tuple(
        item.camera_code
        for item in context.camera_codes
        if item.camera_name == camera_name
    )
    return matches[0] if matches else camera_name


def _sequence(value: Any) -> tuple[Any, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return ()


def _string(value: Any, default: str) -> str:
    if value is None:
        return default
    return str(value)


def _int(value: Any) -> int:
    return int(value or 0)


def _float(value: Any) -> float:
    return float(value or 0)


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _date(value: Any, default: date) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str) and value:
        return date.fromisoformat(value)
    return default


def _datetime(value: Any, default: datetime) -> datetime:
    return to_utc_naive(value, default=default)


def _optional_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    return _datetime(value, _now_utc_naive())


def _midnight(target_date: date) -> datetime:
    return datetime.combine(target_date, datetime.min.time())


def _now_utc_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _without_internal_keys(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if not key.startswith("_")}
