from datetime import datetime

from src.trajectory.assignment import assign_episodes_to_global_units


def test_assign_episodes_to_global_units_prefers_exact_local_unit_match() -> None:
    rows = assign_episodes_to_global_units(
        episode_units=(
            {
                "local_unit_id": "EP-1",
                "camera_name": "CAM_A",
                "start_time": datetime(2026, 4, 23, 9, 5),
                "end_time": datetime(2026, 4, 23, 9, 10),
                "episode_dwell_s": 300.0,
                "kpi_eligible": True,
            },
        ),
        transition_units=(),
        global_members=(
            {
                "global_unit_id": "GU-2",
                "local_unit_id": "OTHER",
                "camera_name": "CAM_A",
                "member_order": 2,
                "start_time": datetime(2026, 4, 23, 9, 0),
                "end_time": datetime(2026, 4, 23, 9, 20),
            },
            {
                "global_unit_id": "GU-1",
                "local_unit_id": "EP-1",
                "camera_name": "CAM_A",
                "member_order": 1,
                "start_time": datetime(2026, 4, 23, 9, 0),
                "end_time": datetime(2026, 4, 23, 9, 20),
            },
        ),
    )

    assert rows == (
        {
            "local_unit_id": "EP-1",
            "camera_name": "CAM_A",
            "episode_start_time": datetime(2026, 4, 23, 9, 5),
            "episode_end_time": datetime(2026, 4, 23, 9, 10),
            "episode_dwell_s": 300.0,
            "episode_kpi_eligible": True,
            "global_unit_id": "GU-1",
            "assignment_mode": "exact_local_unit",
        },
    )


def test_assign_episodes_to_global_units_uses_overlap_fallback() -> None:
    rows = assign_episodes_to_global_units(
        episode_units=(
            {
                "local_unit_id": "EP-X",
                "camera_name": "CAM_A",
                "start_time": datetime(2026, 4, 23, 9, 5),
                "end_time": datetime(2026, 4, 23, 9, 25),
                "episode_dwell_s": 1200.0,
                "kpi_eligible": False,
            },
        ),
        transition_units=(),
        global_members=(
            {
                "global_unit_id": "GU-1",
                "local_unit_id": "M-1",
                "camera_name": "CAM_A",
                "member_order": 2,
                "start_time": datetime(2026, 4, 23, 9, 0),
                "end_time": datetime(2026, 4, 23, 9, 10),
            },
            {
                "global_unit_id": "GU-2",
                "local_unit_id": "M-2",
                "camera_name": "CAM_A",
                "member_order": 1,
                "start_time": datetime(2026, 4, 23, 9, 10),
                "end_time": datetime(2026, 4, 23, 9, 30),
            },
        ),
    )

    assert rows[0]["global_unit_id"] == "GU-2"
    assert rows[0]["assignment_mode"] == "overlap_camera"


def test_assign_episodes_to_global_units_skips_unmatched_episode() -> None:
    rows = assign_episodes_to_global_units(
        episode_units=(
            {
                "local_unit_id": "EP-1",
                "camera_name": "CAM_X",
                "start_time": datetime(2026, 4, 23, 9, 5),
                "end_time": datetime(2026, 4, 23, 9, 10),
            },
        ),
        transition_units=(),
        global_members=(),
    )

    assert rows == ()
