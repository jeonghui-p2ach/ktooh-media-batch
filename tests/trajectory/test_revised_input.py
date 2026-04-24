import pickle
from datetime import datetime
from pathlib import Path

from src.trajectory.revised_input import (
    build_revised_global_inputs,
    build_revised_global_inputs_from_rows,
)


def test_build_revised_global_inputs_from_rows_builds_required_outputs() -> None:
    result = build_revised_global_inputs_from_rows(
        prepared_all=(),
        stitched_df_all=(
            {
                "stitched_id": "ST-1",
                "camera_name": "CAM_A",
                "start_time": datetime(2026, 4, 23, 9, 0),
                "end_time": datetime(2026, 4, 23, 9, 10),
                "raw_tracklet_ids": ["T1", "T2"],
                "local_confidence": 0.8,
                "world_points_arr": [(0.0, 0.0), (3.0, 4.0)],
            },
        ),
        presence_episode_df=(
            {
                "episode_id": "EP-1",
                "camera_name": "CAM_A",
                "episode_start_time": datetime(2026, 4, 23, 9, 1),
                "episode_end_time": datetime(2026, 4, 23, 9, 5),
                "episode_dwell_s": 240.0,
                "support_tracklet_ids": ["T1"],
                "episode_confidence": 0.9,
                "episode_kpi_eligible": True,
                "start_xy": (1.0, 2.0),
            },
        ),
    )

    assert result["episode_units_df"] == (
        {
            "local_unit_id": "EP-1",
            "unit_kind": "episode",
            "camera_name": "CAM_A",
            "start_time": datetime(2026, 4, 23, 9, 1),
            "end_time": datetime(2026, 4, 23, 9, 5),
            "support_tracklet_ids": ("T1",),
            "local_confidence": 0.9,
            "kpi_eligible": True,
            "episode_dwell_s": 240.0,
            "anchor_xy": (1.0, 2.0),
        },
    )
    assert result["transition_units_df"][0]["local_unit_id"] == "ST-1"
    assert result["transition_units_df"][0]["route_length_m"] == 5.0
    assert result["transition_nodes_df"] == (
        {
            "transition_node_id": "ST-1:enter",
            "parent_local_unit_id": "ST-1",
            "camera_name": "CAM_A",
            "transition_role": "enter",
            "node_time": datetime(2026, 4, 23, 9, 0),
            "node_xy": (0.0, 0.0),
            "boundary_zone_id": "",
            "dist_to_zone_m": 0.0,
            "transition_score": 0.8,
        },
        {
            "transition_node_id": "ST-1:exit",
            "parent_local_unit_id": "ST-1",
            "camera_name": "CAM_A",
            "transition_role": "exit",
            "node_time": datetime(2026, 4, 23, 9, 10),
            "node_xy": (3.0, 4.0),
            "boundary_zone_id": "",
            "dist_to_zone_m": 0.0,
            "transition_score": 0.8,
        },
    )


def test_build_revised_global_inputs_reads_local_pickles(tmp_path: Path) -> None:
    _write_pickle(tmp_path / "prepared_all.pkl", [])
    _write_pickle(
        tmp_path / "stitched_df_all.pkl",
        [
            {
                "stitched_id": "ST-1",
                "camera_name": "CAM_A",
                "start_time": datetime(2026, 4, 23, 9, 0),
                "end_time": datetime(2026, 4, 23, 9, 1),
                "raw_tracklet_ids": [],
                "local_confidence": 0.5,
                "world_points_arr": [(0.0, 0.0)],
            }
        ],
    )
    _write_pickle(
        tmp_path / "presence_episode_df.pkl",
        [
            {
                "episode_id": "EP-1",
                "camera_name": "CAM_A",
                "episode_start_time": datetime(2026, 4, 23, 9, 0),
                "episode_end_time": datetime(2026, 4, 23, 9, 1),
                "episode_dwell_s": 60.0,
                "support_tracklet_ids": [],
                "episode_confidence": 0.5,
                "episode_kpi_eligible": False,
            }
        ],
    )

    result = build_revised_global_inputs(tmp_path, cfg=None)

    assert len(result["episode_units_df"]) == 1
    assert len(result["transition_units_df"]) == 1
    assert len(result["transition_nodes_df"]) == 2


def _write_pickle(path: Path, value: object) -> None:
    path.write_bytes(pickle.dumps(value))
