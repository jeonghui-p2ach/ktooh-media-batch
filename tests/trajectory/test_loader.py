from datetime import date, datetime

from src.trajectory.loader import (
    CameraCodeMapping,
    TrajectoryLoadContext,
    build_dashboard_rows,
)
from src.trajectory.spatial import CameraGeoTransform, SpatialCellConfig


def test_build_dashboard_rows_maps_core_artifacts() -> None:
    context = TrajectoryLoadContext(
        target_date=date(2026, 4, 23),
        media_id=101,
        camera_codes=(CameraCodeMapping(camera_name="CAM_14", camera_code="CAM_14"),),
        campaign_id=201,
        creative_id=301,
        source_batch_id="batch-1",
        pipeline_version="v1",
        config_version="cfg-1",
    )
    rows = build_dashboard_rows(
        {
            "presence_episode_df": (
                {
                    "episode_id": "EP-1",
                    "camera_name": "CAM_14",
                    "episode_start_time": datetime(2026, 4, 23, 1),
                    "episode_end_time": datetime(2026, 4, 23, 1, 5),
                    "episode_dwell_s": 300,
                    "support_tracklet_ids": ["T1", "T2"],
                    "episode_confidence": 0.91,
                    "episode_kpi_eligible": True,
                },
            ),
            "global_units_df": (
                {
                    "global_unit_id": "GU-1",
                    "global_start_time": datetime(2026, 4, 23, 1),
                    "global_end_time": datetime(2026, 4, 23, 1, 5),
                    "elapsed_dwell_s": 300,
                    "n_cameras": 1,
                    "camera_path": "CAM_14",
                    "global_confidence": 0.95,
                    "seed_kind": "episode",
                    "visible_episode_count": 1,
                    "visible_camera_count": 1,
                },
            ),
            "hourly_metric_summary_df": (
                {
                    "date": date(2026, 4, 23),
                    "hour": 1,
                    "hour_start": datetime(2026, 4, 23, 1),
                    "hour_end": datetime(2026, 4, 23, 2),
                    "unique_global_units": 1,
                    "visible_unique_units": 1,
                    "total_visible_dwell_s": 300,
                },
            ),
        },
        context,
    )

    assert rows.presence_episodes[0]["camera_code"] == "CAM_14"
    assert rows.presence_episodes[0]["support_tracklet_count"] == 2
    assert rows.global_units[0]["config_version"] == "cfg-1"
    assert rows.hourly_metrics[0]["campaign_id"] == 201


def test_spatial_heatmap_cells_aggregate_route_points() -> None:
    context = TrajectoryLoadContext(
        target_date=date(2026, 4, 23),
        media_id=101,
        camera_codes=(CameraCodeMapping(camera_name="Camera A", camera_code="CAM_A"),),
        spatial_cell=SpatialCellConfig(zoom=18, cell_size_degrees=0.001),
        geo_transforms=(
            CameraGeoTransform(
                camera_code="CAM_A",
                origin_lat=37.0,
                origin_lng=127.0,
                lat_per_world_y=0.001,
                lng_per_world_x=0.001,
            ),
        ),
    )
    rows = build_dashboard_rows(
        {
            "transition_units_df": (
                {
                    "local_unit_id": "LU-1",
                    "camera_name": "Camera A",
                    "start_time": datetime(2026, 4, 23, 9),
                    "route_points": [(0, 0), (0.1, 0.1)],
                    "dwell_s": 10,
                },
            )
        },
        context,
    )

    assert len(rows.spatial_heatmap_cells) == 1
    assert rows.spatial_heatmap_cells[0]["point_count"] == 2
    assert rows.spatial_heatmap_cells[0]["visible_unique_units"] == 1
    assert rows.spatial_heatmap_cells[0]["spatial_ref"] == "EPSG:4326"
