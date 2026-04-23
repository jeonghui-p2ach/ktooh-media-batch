# APPENDIX: 06 Notebook Output Column Snapshot

## 0. 목적

이 문서는 `@ktooh/06.integrated_local_global_revised_pipeline.ipynb`가 생성하거나 직접 참조하는
주요 산출물의 컬럼 스냅샷을 고정한다.

이번 스냅샷은 두 기준을 함께 사용했다.

- raw 기준: `project-pooh-kt/docs/floating.jsonl`
- 코드 기준: `06.integrated_local_global_revised_pipeline.ipynb`, `kt_local_presence_episode.py`, `kt_route_grid_v2.py`

중요:

- `floating.jsonl`의 top-level 필드는 `id`, `type`, `start_time`, `end_time`, `dwell`, `move_dist`, `status`, `bboxes`, `location`뿐이다.
- 따라서 `camera_name`, `tracklet_id`, `support_tracklet_ids`, `transition_node_id`, `global_unit_id`, `camera_path`, `route_family_id`는 raw 직출 컬럼이 아니다.
- 아래 컬럼은 raw -> preprocess/local stitch -> revised global -> metrics/routes 단계에서 파생된다.

---

## 1. Raw 및 Upstream Local Artifact

### 1.1 `floating.jsonl`

raw object event 필드:

- `id`
- `type`
- `start_time`
- `end_time`
- `dwell`
- `move_dist`
- `status`
- `bboxes`
- `location`

measurement batch가 직접 소비하는 필드:

- `type`
- `start_time`
- `end_time`
- `dwell`
- `status`

trajectory batch가 downstream에서 간접 소비하는 출발 필드:

- `start_time`
- `end_time`
- `dwell`
- `bboxes`
- `location`

### 1.2 `prepared_all.pkl`

06 노트북에서 직접 참조하는 핵심 컬럼:

- `tracklet_id` 또는 `id`
- `camera_name` 또는 `source_camera`
- `start_time`
- `end_time`
- `start_xy`
- `end_xy`
- `world_points_arr` 또는 `world_points`
- `track_quality` 또는 `quality`

해석:

- `prepared_all`은 raw 객체를 camera-local tracklet으로 정리한 upstream 산출물이다.
- 06 노트북은 이 파일 전체 스키마를 그대로 계약으로 삼지 않고, 위 핵심 컬럼만 사용한다.

### 1.3 `stitched_df_all.pkl`

06 노트북에서 직접 참조하거나 승계하는 핵심 컬럼:

- `camera_name` 또는 `source_camera`
- `start_time` 또는 `stitched_start_time`
- `end_time` 또는 `stitched_end_time`
- `raw_tracklet_ids` 또는 `support_tracklet_ids`
- `local_confidence`
- `start_xy`
- `end_xy`
- `world_points_arr` 또는 `world_points`

해석:

- `stitched_df_all`은 single-camera stitched trajectory 묶음이다.
- revised global 단계에서는 이 중 boundary support trajectory만 추려 `transition_units_df` 후보로 쓴다.

### 1.4 `presence_episode_df.pkl`

`kt_local_presence_episode.py`의 `EPISODE_COLUMNS` 기준 컬럼:

- `episode_id`
- `camera_name`
- `aoi_id`
- `stay_zone_id`
- `episode_start_time`
- `episode_end_time`
- `episode_dwell_s`
- `observed_time_s`
- `unobserved_gap_s`
- `observed_support_ratio`
- `max_gap_s`
- `median_gap_s`
- `support_tracklet_ids`
- `support_tracklet_count`
- `anchor_drift_m`
- `stay_state_fraction`
- `occlusion_support`
- `mean_episode_node_score`
- `episode_confidence`
- `episode_status`
- `episode_kpi_eligible`
- `artifact_flag`
- `recovery_mode`
- `presence_episode_version`

---

## 2. 06 노트북 Revised Global Input

### 2.1 `episode_units_df.pkl`

`presence_episode_df`에 아래 컬럼을 추가해 만든다.

추가 컬럼:

- `local_unit_id`
- `unit_kind`
- `start_time`
- `end_time`
- `local_confidence`
- `kpi_eligible`
- `anchor_xy`

핵심 사용 컬럼 스냅샷:

- `local_unit_id`
- `unit_kind`
- `camera_name`
- `start_time`
- `end_time`
- `support_tracklet_ids`
- `local_confidence`
- `kpi_eligible`
- `episode_dwell_s`
- `anchor_xy`

### 2.2 `transition_units_df.pkl`

`stitched_df_all`에 아래 파생 컬럼을 추가하고 `is_transition_support == True`만 남긴다.

핵심 컬럼 스냅샷:

- `local_unit_id`
- `unit_kind`
- `camera_name`
- `start_time`
- `end_time`
- `support_tracklet_ids`
- `local_confidence`
- `kpi_eligible`
- `start_xy`
- `end_xy`
- `route_points`
- `dwell_s`
- `route_length_m`
- `start_boundary_zone_id`
- `end_boundary_zone_id`
- `start_boundary_dist_m`
- `end_boundary_dist_m`
- `is_transition_support`

### 2.3 `transition_nodes_df.pkl`

노트북 rows dict 기준 exact 컬럼:

- `transition_node_id`
- `parent_local_unit_id`
- `camera_name`
- `transition_role`
- `node_time`
- `node_xy`
- `boundary_zone_id`
- `dist_to_zone_m`
- `transition_score`

---

## 3. 06 노트북 Association Output

### 3.1 `global_candidate_edges_df.pkl`

노트북 `rec` dict 기준 exact 컬럼:

- `src_transition_node_id`
- `dst_transition_node_id`
- `src_local_unit_id`
- `dst_local_unit_id`
- `src_camera`
- `dst_camera`
- `src_portal_id`
- `dst_portal_id`
- `gap_s`
- `expected_gap_s`
- `shortest_path_dist_m`
- `implied_speed_mps`
- `src_transition_score`
- `dst_transition_score`
- `total_edge_cost`

### 3.2 `selected_global_edges_df.pkl`

컬럼은 `global_candidate_edges_df.pkl`와 동일하다.

### 3.3 `base_global_units_df.pkl`

노트북 `gu_rows` 기준 exact 컬럼:

- `global_unit_id`
- `global_start_time`
- `global_end_time`
- `elapsed_dwell_s`
- `n_cameras`
- `camera_path`
- `global_confidence`
- `seed_kind`

### 3.4 `base_global_unit_members_df.pkl`

노트북 `mem_rows` 기준 exact 컬럼:

- `global_unit_id`
- `local_unit_id`
- `camera_name`
- `member_order`
- `unit_kind`
- `start_time`
- `end_time`

---

## 4. 06 노트북 Metrics Output

### 4.1 `global_presence_episode_df.pkl`

노트북 `assignments` dict 기준 exact 컬럼:

- `local_unit_id`
- `camera_name`
- `episode_start_time`
- `episode_end_time`
- `episode_dwell_s`
- `episode_kpi_eligible`
- `global_unit_id`
- `assignment_mode`

### 4.2 `global_units_df.pkl`

`base_global_units_df`와 visible span merge 이후 컬럼 스냅샷:

- `global_unit_id`
- `global_start_time`
- `global_end_time`
- `elapsed_dwell_s`
- `n_cameras`
- `camera_path`
- `global_confidence`
- `seed_kind`
- `visible_start_time`
- `visible_end_time`
- `visible_episode_count`
- `visible_camera_count`

### 4.3 `hourly_metric_summary_df.pkl`

노트북 `summary` 기준 exact 컬럼:

- `date`
- `hour`
- `hour_start`
- `hour_end`
- `unique_global_units`
- `single_camera_units`
- `multi_camera_units`
- `mean_n_cameras`
- `visible_unique_units`
- `visible_episode_count`
- `visible_camera_count`
- `kpi_visible_unique_units`
- `kpi_visible_episode_count`
- `total_visible_dwell_s`
- `avg_visible_dwell_per_unit_s`
- `median_visible_episode_dwell_s`
- `p75_visible_episode_dwell_s`
- `p90_visible_episode_dwell_s`
- `kpi_total_visible_dwell_s`
- `kpi_avg_visible_dwell_per_unit_s`
- `metrics_version`

---

## 5. 06 노트북 Routes Output

### 5.1 `route_family_df.pkl`

`kt_route_grid_v2.py` 기준 exact 컬럼:

- `route_family_id`
- `camera_path`
- `unit_count`
- `visible_unit_count`
- `median_visible_dwell_s`
- `mean_route_confidence`
- `median_elapsed_s`
- `route_grid_version`

비고:

- 현재 산출물에는 `start_camera`, `end_camera`, `share`가 없다.
- 필요하면 `camera_path`에서 파생하거나 loader/view에서 계산한다.

---

## 6. 적재 경계 요약

measurement batch에 남길 것:

- raw `floating.jsonl` 파싱
- vehicle type 정규화
- `traffic` 적재
- 선택적 pedestrian pattern을 `audience_event_fact`로 적재

trajectory batch로 넘길 것:

- local stitch
- `presence_episode_df`
- `transition_nodes_df`
- `global_units_df`
- `global_presence_episode_df`
- `hourly_metric_summary_df`
- `route_family_df`

핵심 이유:

- measurement batch는 raw 단일 event 해석 문제다.
- trajectory batch는 multi-step 파생과 inter-camera association 문제다.
