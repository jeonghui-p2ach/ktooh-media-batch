from datetime import datetime

from src.trajectory.routes import build_route_family_table


def test_build_route_family_table_groups_by_camera_path() -> None:
    rows = build_route_family_table(
        global_units=(
            {
                "global_unit_id": "GU-1",
                "camera_path": "CAM_A>CAM_B",
                "elapsed_dwell_s": 100.0,
                "global_confidence": 0.8,
            },
            {
                "global_unit_id": "GU-2",
                "camera_path": "CAM_A>CAM_B",
                "elapsed_dwell_s": 200.0,
                "global_confidence": 0.6,
            },
            {
                "global_unit_id": "GU-3",
                "camera_path": "CAM_C",
                "elapsed_dwell_s": 50.0,
                "global_confidence": None,
            },
        ),
        global_presence=(
            # GU-1: 두 에피소드 (0~40s, 40~50s) → union = 50s
            {
                "global_unit_id": "GU-1",
                "episode_start_time": datetime(2026, 4, 23, 9, 0, 0),
                "episode_end_time": datetime(2026, 4, 23, 9, 0, 40),
            },
            {
                "global_unit_id": "GU-1",
                "episode_start_time": datetime(2026, 4, 23, 9, 0, 40),
                "episode_end_time": datetime(2026, 4, 23, 9, 0, 50),
            },
            # GU-2: 단일 에피소드 20s
            {
                "global_unit_id": "GU-2",
                "episode_start_time": datetime(2026, 4, 23, 9, 0, 0),
                "episode_end_time": datetime(2026, 4, 23, 9, 0, 20),
            },
        ),
        route_grid_version="grid-v2",

    )

    assert rows == (
        {
            "route_family_id": "RF_CAM_A_CAM_B",
            "camera_path": "CAM_A>CAM_B",
            "unit_count": 2,
            "visible_unit_count": 2,
            "median_visible_dwell_s": 35.0,
            "mean_route_confidence": 0.7,
            "median_elapsed_s": 150.0,
            "route_grid_version": "grid-v2",
        },
        {
            "route_family_id": "RF_CAM_C",
            "camera_path": "CAM_C",
            "unit_count": 1,
            "visible_unit_count": 0,
            "median_visible_dwell_s": 0.0,
            "mean_route_confidence": None,
            "median_elapsed_s": 50.0,
            "route_grid_version": "grid-v2",
        },
    )


def test_build_route_family_table_handles_empty_inputs() -> None:
    assert build_route_family_table(global_units=(), global_presence=()) == ()
