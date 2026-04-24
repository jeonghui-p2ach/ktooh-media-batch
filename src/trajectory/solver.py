from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from scipy.optimize import linear_sum_assignment


def solve_revised_global_edges(
    candidate_edges: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], ...]:
    if not candidate_edges:
        return ()

    max_edge_cost = _float_from_cfg(cfg, "max_edge_cost", 2000.0)
    unmatched_cost = _float_from_cfg(cfg, "unmatched_cost", 2000.0)
    big_cost = unmatched_cost + max_edge_cost + 10.0

    src_ids: list[str] = []
    dst_ids: list[str] = []
    for row in candidate_edges:
        s = _string(row.get("src_transition_node_id"))
        d = _string(row.get("dst_transition_node_id"))
        if s and s not in src_ids:
            src_ids.append(s)
        if d and d not in dst_ids:
            dst_ids.append(d)

    n_src = len(src_ids)
    n_dst = len(dst_ids)
    if n_src == 0 or n_dst == 0:
        return ()

    size = n_src + n_dst
    src_to_i = {k: i for i, k in enumerate(src_ids)}
    dst_to_j = {k: j for j, k in enumerate(dst_ids)}

    c_mat = np.full((size, size), big_cost, dtype=float)

    # Dedup and sort to keep the best cost for duplicate transitions
    best_edges_dict: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in sorted(candidate_edges, key=lambda x: float(x.get("total_edge_cost") or 0.0)):
        s = _string(row.get("src_transition_node_id"))
        d = _string(row.get("dst_transition_node_id"))
        if s and d and (s, d) not in best_edges_dict:
            best_edges_dict[(s, d)] = row

    for (s, d), row in best_edges_dict.items():
        i = src_to_i[s]
        j = dst_to_j[d]
        c_mat[i, j] = float(row.get("total_edge_cost") or 0.0)

    for i in range(n_src):
        c_mat[i, n_dst + i] = unmatched_cost

    for j in range(n_dst):
        c_mat[n_src + j, j] = unmatched_cost

    for i in range(n_src, size):
        for j in range(n_dst, size):
            c_mat[i, j] = 0.0

    row_ind, col_ind = linear_sum_assignment(c_mat)

    selected_pairs: set[tuple[str, str]] = set()
    for i, j in zip(row_ind, col_ind, strict=False):
        if i < n_src and j < n_dst and c_mat[i, j] <= max_edge_cost:
            selected_pairs.add((src_ids[i], dst_ids[j]))

    if not selected_pairs:
        return ()

    selected: list[dict[str, Any]] = []
    # Preserve order
    for row in candidate_edges:
        s = _string(row.get("src_transition_node_id"))
        d = _string(row.get("dst_transition_node_id"))
        if (s, d) in selected_pairs:
            selected.append(dict(row))
            selected_pairs.remove((s, d))

    return tuple(selected)


def _float_from_cfg(cfg: Mapping[str, Any] | None, key: str, default: float) -> float:
    if not cfg:
        return default
    value = cfg.get(key)
    return default if value is None else float(value)


def _string(value: Any) -> str:
    return "" if value is None else str(value)
