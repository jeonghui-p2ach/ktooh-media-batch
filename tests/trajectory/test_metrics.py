from datetime import datetime

from src.trajectory.metrics import build_corrected_hourly_metrics


def test_build_corrected_hourly_metrics_splits_episode_overlap_by_hour() -> None:
    rows = build_corrected_hourly_metrics(
        global_units=(
            {
                "global_unit_id": "GU-1",
                "global_start_time": datetime(2026, 4, 23, 9, 50),
                "global_end_time": datetime(2026, 4, 23, 10, 10),
                "n_cameras": 1,
            },
        ),
        global_presence=(
            {
                "global_unit_id": "GU-1",
                "camera_name": "CAM_A",
                "episode_start_time": datetime(2026, 4, 23, 9, 50),
                "episode_end_time": datetime(2026, 4, 23, 10, 10),
                "episode_kpi_eligible": True,
            },
        ),
        metrics_version="metrics-v2",
    )

    assert rows == (
        {
            "date": datetime(2026, 4, 23, 9).date(),
            "hour": 9,
            "hour_start": datetime(2026, 4, 23, 9),
            "hour_end": datetime(2026, 4, 23, 10),
            "unique_global_units": 1,
            "single_camera_units": 1,
            "multi_camera_units": 0,
            "mean_n_cameras": 1.0,
            "visible_unique_units": 1,
            "visible_episode_count": 1,
            "visible_camera_count": 1,
            "kpi_visible_unique_units": 1,
            "kpi_visible_episode_count": 1,
            "total_visible_dwell_s": 600.0,
            "avg_visible_dwell_per_unit_s": 600.0,
            "median_visible_episode_dwell_s": 600.0,
            "p75_visible_episode_dwell_s": 600.0,
            "p90_visible_episode_dwell_s": 600.0,
            "kpi_total_visible_dwell_s": 600.0,
            "kpi_avg_visible_dwell_per_unit_s": 600.0,
            "metrics_version": "metrics-v2",
            "camera_name": "CAM_A",
        },
        {
            "date": datetime(2026, 4, 23, 10).date(),
            "hour": 10,
            "hour_start": datetime(2026, 4, 23, 10),
            "hour_end": datetime(2026, 4, 23, 11),
            "unique_global_units": 1,
            "single_camera_units": 1,
            "multi_camera_units": 0,
            "mean_n_cameras": 1.0,
            "visible_unique_units": 1,
            "visible_episode_count": 1,
            "visible_camera_count": 1,
            "kpi_visible_unique_units": 1,
            "kpi_visible_episode_count": 1,
            "total_visible_dwell_s": 600.0,
            "avg_visible_dwell_per_unit_s": 600.0,
            "median_visible_episode_dwell_s": 600.0,
            "p75_visible_episode_dwell_s": 600.0,
            "p90_visible_episode_dwell_s": 600.0,
            "kpi_total_visible_dwell_s": 600.0,
            "kpi_avg_visible_dwell_per_unit_s": 600.0,
            "metrics_version": "metrics-v2",
            "camera_name": "CAM_A",
        },
    )


def test_build_corrected_hourly_metrics_aggregates_unit_and_percentiles() -> None:
    rows = build_corrected_hourly_metrics(
        global_units=(
            {
                "global_unit_id": "GU-1",
                "global_start_time": datetime(2026, 4, 23, 9, 0),
                "global_end_time": datetime(2026, 4, 23, 9, 40),
                "n_cameras": 1,
            },
            {
                "global_unit_id": "GU-2",
                "global_start_time": datetime(2026, 4, 23, 9, 10),
                "global_end_time": datetime(2026, 4, 23, 9, 50),
                "n_cameras": 2,
            },
        ),
        global_presence=(
            {
                "global_unit_id": "GU-1",
                "camera_name": "CAM_A",
                "episode_start_time": datetime(2026, 4, 23, 9, 0),
                "episode_end_time": datetime(2026, 4, 23, 9, 10),
                "episode_kpi_eligible": True,
            },
            {
                "global_unit_id": "GU-2",
                "camera_name": "CAM_B",
                "episode_start_time": datetime(2026, 4, 23, 9, 15),
                "episode_end_time": datetime(2026, 4, 23, 9, 35),
                "episode_kpi_eligible": False,
            },
        ),
    )

    assert rows == (
        {
            "date": datetime(2026, 4, 23, 9).date(),
            "hour": 9,
            "hour_start": datetime(2026, 4, 23, 9),
            "hour_end": datetime(2026, 4, 23, 10),
            "unique_global_units": 2,
            "single_camera_units": 1,
            "multi_camera_units": 1,
            "mean_n_cameras": 1.5,
            "visible_unique_units": 1,
            "visible_episode_count": 1,
            "visible_camera_count": 1,
            "kpi_visible_unique_units": 1,
            "kpi_visible_episode_count": 1,
            "total_visible_dwell_s": 600.0,
            "avg_visible_dwell_per_unit_s": 600.0,
            "median_visible_episode_dwell_s": 600.0,
            "p75_visible_episode_dwell_s": 600.0,
            "p90_visible_episode_dwell_s": 600.0,
            "kpi_total_visible_dwell_s": 600.0,
            "kpi_avg_visible_dwell_per_unit_s": 600.0,
            "metrics_version": "metrics-v1",
            "camera_name": "CAM_A",
        },
        {
            "date": datetime(2026, 4, 23, 9).date(),
            "hour": 9,
            "hour_start": datetime(2026, 4, 23, 9),
            "hour_end": datetime(2026, 4, 23, 10),
            "unique_global_units": 2,
            "single_camera_units": 1,
            "multi_camera_units": 1,
            "mean_n_cameras": 1.5,
            "visible_unique_units": 1,
            "visible_episode_count": 1,
            "visible_camera_count": 1,
            "kpi_visible_unique_units": 0,
            "kpi_visible_episode_count": 0,
            "total_visible_dwell_s": 1200.0,
            "avg_visible_dwell_per_unit_s": 1200.0,
            "median_visible_episode_dwell_s": 1200.0,
            "p75_visible_episode_dwell_s": 1200.0,
            "p90_visible_episode_dwell_s": 1200.0,
            "kpi_total_visible_dwell_s": 0.0,
            "kpi_avg_visible_dwell_per_unit_s": 0.0,
            "metrics_version": "metrics-v1",
            "camera_name": "CAM_B",
        },
    )


def test_build_corrected_hourly_metrics_handles_empty_inputs() -> None:
    assert build_corrected_hourly_metrics(global_units=(), global_presence=()) == ()
