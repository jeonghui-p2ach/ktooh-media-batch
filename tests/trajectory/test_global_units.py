from datetime import datetime

from src.trajectory.global_units import finalize_global_units


def test_finalize_global_units_merges_visible_summary() -> None:
    rows = finalize_global_units(
        base_global_units=(
            {
                "global_unit_id": "GU-1",
                "global_start_time": datetime(2026, 4, 23, 9, 0),
                "global_end_time": datetime(2026, 4, 23, 9, 40),
                "elapsed_dwell_s": 2400.0,
                "n_cameras": 2,
                "camera_path": "CAM_A>CAM_B",
                "global_confidence": 0.75,
                "seed_kind": "transition",
            },
            {
                "global_unit_id": "GU-2",
                "global_start_time": datetime(2026, 4, 23, 10, 0),
                "global_end_time": datetime(2026, 4, 23, 10, 30),
                "elapsed_dwell_s": 1800.0,
                "n_cameras": 1,
                "camera_path": "CAM_C",
                "global_confidence": None,
                "seed_kind": "episode",
            },
        ),
        assigned_episodes=(
            {
                "global_unit_id": "GU-1",
                "camera_name": "CAM_A",
                "episode_start_time": datetime(2026, 4, 23, 9, 5),
                "episode_end_time": datetime(2026, 4, 23, 9, 15),
            },
            {
                "global_unit_id": "GU-1",
                "camera_name": "CAM_B",
                "episode_start_time": datetime(2026, 4, 23, 9, 20),
                "episode_end_time": datetime(2026, 4, 23, 9, 30),
            },
        ),
    )

    assert rows == (
        {
            "global_unit_id": "GU-1",
            "global_start_time": datetime(2026, 4, 23, 9, 0),
            "global_end_time": datetime(2026, 4, 23, 9, 40),
            "elapsed_dwell_s": 2400.0,
            "n_cameras": 2,
            "camera_path": "CAM_A>CAM_B",
            "global_confidence": 0.75,
            "seed_kind": "transition",
            "visible_start_time": datetime(2026, 4, 23, 9, 5),
            "visible_end_time": datetime(2026, 4, 23, 9, 30),
            "visible_episode_count": 2,
            "visible_camera_count": 2,
        },
        {
            "global_unit_id": "GU-2",
            "global_start_time": datetime(2026, 4, 23, 10, 0),
            "global_end_time": datetime(2026, 4, 23, 10, 30),
            "elapsed_dwell_s": 1800.0,
            "n_cameras": 1,
            "camera_path": "CAM_C",
            "global_confidence": None,
            "seed_kind": "episode",
            "visible_start_time": None,
            "visible_end_time": None,
            "visible_episode_count": 0,
            "visible_camera_count": 0,
        },
    )


def test_finalize_global_units_handles_empty_inputs() -> None:
    assert finalize_global_units(base_global_units=(), assigned_episodes=()) == ()
