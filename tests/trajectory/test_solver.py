from src.trajectory.solver import solve_revised_global_edges


def test_solve_global_edges_uses_hungarian_min_cost() -> None:
    # Greedy 알고리즘의 실패 케이스 (반례):
    # S1->D1: 10 (탐색 시 가장 먼저 픽됨)
    # S1->D2: 100
    # S2->D1: 20
    # S2->D2: 1000
    #
    # 만약 Greedy라면 10(S1->D1)을 고르고 남은 S2는 어쩔 수 없이 D2와 연결되어 1010(10+1000) 비용이 됨.
    # 하지만 최적의 매칭은 S1->D2, S2->D1 조합으로 비용이 120(100+20)이 되는 것임.
    rows = solve_revised_global_edges(
        candidate_edges=(
            {
                "src_transition_node_id": "S1",
                "dst_transition_node_id": "D1",
                "total_edge_cost": 10.0,
            },
            {
                "src_transition_node_id": "S1",
                "dst_transition_node_id": "D2",
                "total_edge_cost": 100.0,
            },
            {
                "src_transition_node_id": "S2",
                "dst_transition_node_id": "D1",
                "total_edge_cost": 20.0,
            },
            {
                "src_transition_node_id": "S2",
                "dst_transition_node_id": "D2",
                "total_edge_cost": 1000.0,
            },
        ),
        cfg={"max_edge_cost": 2000.0, "unmatched_cost": 2000.0},
    )

    # Hungarian 매칭 결과에 따라 S1-D2, S2-D1으로 정답이 도출될 것을 기대함
    matched_pairs = {(r["src_transition_node_id"], r["dst_transition_node_id"]) for r in rows}
    assert matched_pairs == {("S1", "D2"), ("S2", "D1")}



def test_solve_global_edges_preserves_input_order() -> None:
    rows = solve_revised_global_edges(
        candidate_edges=(
            {
                "src_transition_node_id": "S2",
                "dst_transition_node_id": "D2",
                "src_camera": "CAM_A",
                "dst_camera": "CAM_B",
                "total_edge_cost": 1.0,
            },
            {
                "src_transition_node_id": "S1",
                "dst_transition_node_id": "D1",
                "src_camera": "CAM_A",
                "dst_camera": "CAM_C",
                "total_edge_cost": 1.0,
            },
        ),
    )

    # 입력 순서(candidate_edges)를 보존하여 S2, 그 다음 S1을 반환해야 함
    assert rows[0]["src_transition_node_id"] == "S2"
    assert rows[1]["src_transition_node_id"] == "S1"
