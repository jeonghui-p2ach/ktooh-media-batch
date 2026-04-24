from datetime import datetime

from src.trajectory.materialization import materialize_revised_global_units


def test_materialize_revised_global_units_builds_components_and_members() -> None:
    base_units, base_members = materialize_revised_global_units(
        transition_units=(
            {
                "local_unit_id": "LU-1",
                "unit_kind": "transition",
                "camera_name": "CAM_A",
                "start_time": datetime(2026, 4, 23, 9, 0),
                "end_time": datetime(2026, 4, 23, 9, 10),
                "local_confidence": 0.8,
            },
            {
                "local_unit_id": "LU-2",
                "unit_kind": "transition",
                "camera_name": "CAM_B",
                "start_time": datetime(2026, 4, 23, 9, 12),
                "end_time": datetime(2026, 4, 23, 9, 20),
                "local_confidence": 0.6,
            },
            {
                "local_unit_id": "LU-3",
                "unit_kind": "transition",
                "camera_name": "CAM_C",
                "start_time": datetime(2026, 4, 23, 10, 0),
                "end_time": datetime(2026, 4, 23, 10, 5),
                "local_confidence": 0.9,
            },
        ),
        selected_edges=(
            {
                "src_local_unit_id": "LU-1",
                "dst_local_unit_id": "LU-2",
            },
        ),
    )

    assert base_units == (
        {
            "global_unit_id": "GU_000000",
            "global_start_time": datetime(2026, 4, 23, 9, 0),
            "global_end_time": datetime(2026, 4, 23, 9, 20),
            "elapsed_dwell_s": 1200.0,
            "n_cameras": 2,
            "camera_path": "CAM_A>CAM_B",
            "global_confidence": 0.7,
            "seed_kind": "transition",
        },
        {
            "global_unit_id": "GU_000001",
            "global_start_time": datetime(2026, 4, 23, 10, 0),
            "global_end_time": datetime(2026, 4, 23, 10, 5),
            "elapsed_dwell_s": 300.0,
            "n_cameras": 1,
            "camera_path": "CAM_C",
            "global_confidence": 0.9,
            "seed_kind": "episode",
        },
    )
    assert base_members == (
        {
            "global_unit_id": "GU_000000",
            "local_unit_id": "LU-1",
            "camera_name": "CAM_A",
            "member_order": 1,
            "unit_kind": "transition",
            "start_time": datetime(2026, 4, 23, 9, 0),
            "end_time": datetime(2026, 4, 23, 9, 10),
        },
        {
            "global_unit_id": "GU_000000",
            "local_unit_id": "LU-2",
            "camera_name": "CAM_B",
            "member_order": 2,
            "unit_kind": "transition",
            "start_time": datetime(2026, 4, 23, 9, 12),
            "end_time": datetime(2026, 4, 23, 9, 20),
        },
        {
            "global_unit_id": "GU_000001",
            "local_unit_id": "LU-3",
            "camera_name": "CAM_C",
            "member_order": 1,
            "unit_kind": "transition",
            "start_time": datetime(2026, 4, 23, 10, 0),
            "end_time": datetime(2026, 4, 23, 10, 5),
        },
    )


def test_materialize_revised_global_units_handles_empty_inputs() -> None:
    assert materialize_revised_global_units(transition_units=(), selected_edges=()) == ((), ())


def test_materialize_repeated_camera_split() -> None:
    # 체인: LU-1(CAM_A) -> LU-2(CAM_B) -> LU-3(CAM_A)
    # 기대결과: CAM_A 재방문으로 인해 두 번째 CAM_A에서 단위가 분리되어야 함
    base_units, _ = materialize_revised_global_units(
        transition_units=(
            {
                "local_unit_id": "LU-1",
                "unit_kind": "transition",
                "camera_name": "CAM_A",
                "start_time": datetime(2026, 4, 23, 9, 0),
                "end_time": datetime(2026, 4, 23, 9, 10),
            },
            {
                "local_unit_id": "LU-2",
                "unit_kind": "transition",
                "camera_name": "CAM_B",
                "start_time": datetime(2026, 4, 23, 9, 12),
                "end_time": datetime(2026, 4, 23, 9, 20),
            },
            {
                "local_unit_id": "LU-3",
                "unit_kind": "transition",
                "camera_name": "CAM_A",
                "start_time": datetime(2026, 4, 23, 9, 25),
                "end_time": datetime(2026, 4, 23, 9, 30),
            },
        ),
        selected_edges=(
            {"src_local_unit_id": "LU-1", "dst_local_unit_id": "LU-2"},
            {"src_local_unit_id": "LU-2", "dst_local_unit_id": "LU-3"},
        ),
    )

    assert len(base_units) == 2
    assert base_units[0]["camera_path"] == "CAM_A>CAM_B"
    assert base_units[1]["camera_path"] == "CAM_A"


def test_materialize_directed_chain_respects_direction() -> None:
    # 엣지 방항: 1 -> 2 <- 3 (2번이 수신자만 2개, Undirected Component라면 1-2-3이 하나로 묶임)
    # 기대결과: 방향성 체인이므로 [1 -> 2]와 [3]으로 분리되어야 함.
    base_units, _ = materialize_revised_global_units(
        transition_units=(
            {
                "local_unit_id": "LU-1",
                "unit_kind": "transition",
                "camera_name": "CAM_A",
                "start_time": datetime(2026, 4, 23, 9, 0),
                "end_time": datetime(2026, 4, 23, 9, 5),
            },
            {
                "local_unit_id": "LU-2",
                "unit_kind": "transition",
                "camera_name": "CAM_B",
                "start_time": datetime(2026, 4, 23, 9, 10),
                "end_time": datetime(2026, 4, 23, 9, 15),
            },
            {
                "local_unit_id": "LU-3",
                "unit_kind": "transition",
                "camera_name": "CAM_C",
                "start_time": datetime(2026, 4, 23, 9, 2),
                "end_time": datetime(2026, 4, 23, 9, 7),
            },
        ),
        selected_edges=(
            {"src_local_unit_id": "LU-1", "dst_local_unit_id": "LU-2"},
            {"src_local_unit_id": "LU-3", "dst_local_unit_id": "LU-2"},
        ),
    )

    expected_paths = {row["camera_path"] for row in base_units}
    assert "CAM_A>CAM_B" in expected_paths
    assert "CAM_C" in expected_paths
    assert "CAM_C>CAM_B" not in expected_paths  # 2 is already consumed by 1
