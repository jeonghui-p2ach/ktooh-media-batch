from datetime import datetime

from src.trajectory.scoring import build_revised_candidate_edges


def test_build_revised_candidate_edges_builds_cross_camera_edges() -> None:
    # 수식 계산 (테스트 mock 값 기준):
    # - path_dist = 60.0
    # - gap_s = 60.0 (9:01:00 - 9:00:00)
    # - pair_speed = 1.0 (hour_speed_df)
    # - exp_gap = 60.0 / max(1.0, 0.25) = 60.0
    # - implied_speed = 60.0 / 60.0 = 1.0
    # - gap_resid = abs(60.0 - 60.0) = 0.0
    # - speed_resid = abs(1.0 - 1.0) = 0.0
    # - zone_penalty = 0.0
    # - weak_pen = weak_transition_penalty(1.5) * max(1.0 - min(0.9, 0.8), 0.0) = 1.5 * 0.2 = 0.3
    # - conf_pen = 0.20 * max(1.0 - min(0.8, 0.8), 0.0) = 0.20 * 0.2 = 0.04
    # - total_cost = 0.0 + 0.0 + 0.0 + 0.3 + 0.04 = 0.34

    rows = build_revised_candidate_edges(
        transition_nodes=(
            {
                "transition_node_id": "N1",
                "parent_local_unit_id": "LU-1",
                "camera_name": "CAM_A",
                "transition_role": "exit",
                "node_time": datetime(2026, 4, 23, 9, 0),
                "transition_score": 0.9,
                "local_confidence": 0.8,
            },
            {
                "transition_node_id": "N2",
                "parent_local_unit_id": "LU-2",
                "camera_name": "CAM_B",
                "transition_role": "enter",
                "node_time": datetime(2026, 4, 23, 9, 1),
                "transition_score": 0.8,
                "local_confidence": 0.8,
            },
        ),
        links_df=({"src_camera": "CAM_A", "dst_camera": "CAM_B", "shortest_path_dist_m": 60.0},),
        offset_df=(),
        hour_speed_df=({"hour": 9, "speed_mps": 1.0},),
        cfg={"weak_transition_penalty": 1.5, "max_inter_camera_speed_mps": 10.0},
    )

    assert len(rows) == 1
    edge = rows[0]
    assert edge["gap_s"] == 60.0
    assert edge["implied_speed_mps"] == 1.0
    assert abs(edge["total_edge_cost"] - 0.34) < 1e-5


def test_build_revised_candidate_edges_filters_impossible_speed() -> None:
    rows = build_revised_candidate_edges(
        transition_nodes=(
            {
                "transition_node_id": "N1",
                "parent_local_unit_id": "LU-1",
                "camera_name": "CAM_A",
                "transition_role": "exit",
                "node_time": datetime(2026, 4, 23, 9, 0),
            },
            {
                "transition_node_id": "N2",
                "parent_local_unit_id": "LU-2",
                "camera_name": "CAM_B",
                "transition_role": "enter",
                "node_time": datetime(2026, 4, 23, 9, 1),
            },
        ),
        links_df=({"src_camera": "CAM_A", "dst_camera": "CAM_B", "shortest_path_dist_m": 600.0},),
        offset_df=(),
        hour_speed_df=({"hour": 9, "speed_mps": 1.0},),
        cfg={"max_inter_camera_speed_mps": 5.0},
    )

    assert rows == ()
