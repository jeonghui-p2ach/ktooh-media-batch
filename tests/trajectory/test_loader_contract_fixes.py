"""Tests for trajectory loader contract and calculation fixes."""

import pytest
from datetime import date, datetime, timedelta, timezone
from src.trajectory.loader import (
    CameraCodeMapping,
    TrajectoryLoadContext,
    build_dashboard_rows,
    _datetime
)
from src.trajectory.metrics import build_corrected_hourly_metrics
from src.trajectory.spatial import CameraGeoTransform, SpatialCellConfig

def test_hourly_metrics_camera_attribution_logic():
    """Verify that hourly metrics are correctly attributed to cameras and media-wide."""
    # Data: 2 cameras, 2 units (one on each)
    global_units = [
        {"global_unit_id": "U1", "camera_path": "CAM_A", "global_start_time": datetime(2026, 4, 23, 9)},
        {"global_unit_id": "U2", "camera_path": "CAM_B", "global_start_time": datetime(2026, 4, 23, 9)},
    ]
    global_presence = [
        {"global_unit_id": "U1", "camera_name": "CAM_A", "episode_start_time": datetime(2026, 4, 23, 9), "episode_end_time": datetime(2026, 4, 23, 9, 1)},
        {"global_unit_id": "U2", "camera_name": "CAM_B", "episode_start_time": datetime(2026, 4, 23, 9), "episode_end_time": datetime(2026, 4, 23, 9, 1)},
    ]
    
    results = build_corrected_hourly_metrics(global_units, global_presence)
    
    # Check that we have 3 rows: CAM_A, CAM_B, and Media-wide ("")
    assert len(results) == 3
    
    # Media-wide
    media_wide = [r for r in results if r["camera_name"] == ""]
    assert len(media_wide) == 1
    assert media_wide[0]["visible_unique_units"] == 2
    
    # Cameras
    cam_a = [r for r in results if r["camera_name"] == "CAM_A"]
    assert len(cam_a) == 1
    assert cam_a[0]["visible_unique_units"] == 1
    
    cam_b = [r for r in results if r["camera_name"] == "CAM_B"]
    assert len(cam_b) == 1
    assert cam_b[0]["visible_unique_units"] == 1

def test_spatial_heatmap_dwell_accumulation_bug():
    """Reproduce the bug where dwell_s is overwritten instead of accumulated in heatmap."""
    context = TrajectoryLoadContext(
        target_date=date(2026, 4, 23),
        media_id=101,
        camera_codes=(CameraCodeMapping(camera_name="CAM_A", camera_code="CAM_A"),),
        geo_transforms=(
            CameraGeoTransform(
                camera_code="CAM_A",
                origin_lat=37.0, origin_lng=127.0,
                lat_per_world_y=0.001, lng_per_world_x=0.001,
            ),
        ),
    )
    
    # Two different units in the same cell
    artifact_rows = {
        "transition_units_df": (
            {
                "local_unit_id": "U1", "camera_name": "CAM_A",
                "start_time": datetime(2026, 4, 23, 9),
                "route_points": [(0, 0)], "dwell_s": 10.5,
            },
            {
                "local_unit_id": "U2", "camera_name": "CAM_A",
                "start_time": datetime(2026, 4, 23, 9),
                "route_points": [(0, 0)], "dwell_s": 20.0,
            },
        )
    }
    
    rows = build_dashboard_rows(artifact_rows, context)
    
    # Expected: 10.5 + 20.0 = 30.5
    assert rows.spatial_heatmap_cells[0]["total_visible_dwell_s"] == 30.5

def test_datetime_normalization_tz_aware():
    """Verify that tz-aware datetimes are correctly normalized to UTC naive."""
    # KST (UTC+9) 09:00:00 -> UTC 00:00:00
    kst = timezone(timedelta(hours=9))
    aware_dt = datetime(2026, 4, 23, 9, 0, 0, tzinfo=kst)
    
    normalized = _datetime(aware_dt, datetime.min)
    
    # Should be 00:00:00 UTC
    assert normalized == datetime(2026, 4, 23, 0, 0, 0)
