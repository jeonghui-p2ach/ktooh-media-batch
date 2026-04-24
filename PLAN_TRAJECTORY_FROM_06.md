# PLAN: Trajectory Load From 06 Notebook

## 0. 문서 목적

이 문서는 `@ktooh/06.integrated_local_global_revised_pipeline.ipynb`의 기초 로직을
배치 서비스와 적재 대상으로 옮기기 위한 별도 계획서다.

이 문서는 현재 `PLAN.md`와 다르다.

- `PLAN.md`: `project-pooh-kt`의 `demographic.jsonl`, `floating.jsonl` 적재 계획
- `PLAN_TRAJECTORY_FROM_06.md`: local/global trajectory 복원 결과 적재 계획

즉 이 문서는 measurement batch가 아니라
`presence_episode`, `global_unit`, `hourly metrics`, `route_family` 중심 계획이다.

상태 표기:

- `[ ]` 미착수
- `[~]` 진행 중
- `[x]` 완료

---

## 1. 노트북 기준 범위

### 1.1 노트북 핵심 단계

- [x] `run_s3_groundplane_stage`
- [x] `run_local_scene_stitch_stage`
- [x] `build_revised_global_inputs`
- [x] `build_topology_static_stage`
- [x] `build_revised_candidate_edges`
- [x] `solve_revised_global_edges`
- [x] `materialize_revised_global_units`
- [x] `assign_episodes_to_global_units`
- [x] `finalize_global_units`
- [x] `build_corrected_hourly_metrics`
- [x] `build_route_family_table`

### 1.2 노트북 핵심 산출물

- [x] `prepared_all.pkl`
- [x] `stitched_df_all.pkl`
- [x] `presence_episode_df.pkl`
- [x] `episode_units_df.pkl`
- [x] `transition_units_df.pkl`
- [x] `transition_nodes_df.pkl`
- [x] `global_candidate_edges_df.pkl`
- [x] `selected_global_edges_df.pkl`
- [x] `base_global_units_df.pkl`
- [x] `base_global_unit_members_df.pkl`
- [x] `global_units_df.pkl`
- [x] `global_presence_episode_df.pkl`
- [x] `hourly_metric_summary_df.pkl`
- [x] `route_family_df.pkl`

### 1.3 노트북 핵심 원칙

- [x] `presence_episode`는 dwell 객체다.
- [x] `transition_support_trajectory`만 inter-camera association 후보다.
- [x] hourly dwell은 `global_unit_id` 내부 interval union 후 합산한다.
- [x] route family는 finalized global unit 위에서 계산한다.

---

## 2. 목표와 비목표

### 2.1 목표

- [ ] 노트북 없이 배치 명령만으로 preprocess -> local -> revised global -> metrics -> routes를 실행할 수 있어야 한다.
- [ ] 노트북 산출물과 구조적으로 동일한 적재 대상 계약을 가져야 한다.
- [x] 결과를 파일 저장만이 아니라 DB 적재 대상으로도 재사용 가능해야 한다.
- [x] local/global/hourly/route 결과를 dashboard가 읽을 수 있는 형태로 노출할 수 있어야 한다.
- [x] dashboard 조회 필터는 최소 `media_id`, `camera_name` 또는 `camera_code`, 날짜 범위를 지원해야 한다.
- [~] trajectory 결과에도 `campaign_id`, `creative_id` 귀속을 포함해 media/campaign/creative 단위 drill-down이 가능해야 한다.
- [x] `hourly_metric_summary` 원본 적재와 dashboard용 집계 view, heatmap 조회 계약을 함께 고정해야 한다.
- [x] 지도 위 heatmap을 위해 `world_points` 또는 local world 좌표를 GPS 또는 지도 투영 좌표로 변환하는 계약을 고정해야 한다.

### 2.2 비목표

- [ ] `project-pooh-kt`의 measurement batch와 같은 저장소/같은 단계로 바로 합치지 않는다.
- [ ] 노트북 exploratory QC 화면 자체를 1차 목표로 옮기지 않는다.
- [ ] 1차에서 모든 intermediate artifact를 DB에 넣지 않는다.

### 2.3 완료 정의

- [ ] 배치가 `target_date`, `run_root` 기준으로 06 노트북과 동일한 주요 산출물을 생성한다.
- [x] `presence_episode`, `global_units`, `global_presence_episode`, `hourly_metric_summary`, `route_family`의 저장 계약이 고정된다.
- [ ] 적어도 파일 기반 golden 비교로 노트북과 일치 여부를 확인할 수 있다.
- [x] dashboard가 `media_id + camera` 필터로 trajectory 시간대 패턴, route family, heatmap을 조회할 수 있다.
- [x] dashboard가 지도 레이어 위에 trajectory spatial heatmap을 조회할 수 있다.

---

## 3. 제안 구조

### 3.1 프로젝트 경계

- [x] `ktooh-media-batch` 내부에서는 별도 하위 패키지로 분리한다.
- [ ] 운영/배포 독립성이 필요해지면 별도 프로젝트로 승격한다.

결론:

- [x] trajectory batch는 measurement batch와 문서뿐 아니라 패키지 경계도 분리하는 것이 기본이다.
- [x] 같은 저장소를 유지할 수는 있지만, 같은 `src` 루트 평면 구조에 섞는 방식은 피한다.
- [x] 1차 권장안은 `ktooh-media-batch/src/measurement`와 `ktooh-media-batch/src/trajectory`의 하위 패키지 분리다.
- [x] 2차 권장안은 운영/배포 독립성이 필요할 때 `ktooh-trajectory-batch/` 별도 프로젝트로 승격하는 것이다.
- [x] 1차 권장안에 따라 `src/measurement`, `src/trajectory`, `src/common` 패키지 경계를 생성했다.

권장:

```text
ktooh-trajectory-batch/
src/
├── preprocess.py
├── local_stage.py
├── global_stage.py
├── metrics_stage.py
├── routes_stage.py
├── storage.py
└── main.py
```

또는

```text
ktooh-media-batch/src/trajectory/
```

단, measurement batch와 실행 경로는 분리한다.

같은 저장소를 유지할 때 권장 구조:

```text
ktooh-media-batch/
├── src/
│   ├── common/
│   │   ├── config.py
│   │   └── logging_config.py
│   ├── measurement/
│   │   ├── main.py
│   │   ├── collector.py
│   │   ├── parser_demographic.py
│   │   ├── parser_floating.py
│   │   ├── normalization_demographic.py
│   │   ├── normalization_floating.py
│   │   ├── attribution.py
│   │   ├── loader_audience.py
│   │   ├── loader_traffic.py
│   │   └── verify.py
│   └── trajectory/
│       ├── main.py
│       ├── preprocess.py
│       ├── local_stage.py
│       ├── global_stage.py
│       ├── metrics_stage.py
│       ├── routes_stage.py
│       ├── storage.py
│       └── verify.py
├── PLAN.md
└── PLAN_TRAJECTORY_FROM_06.md
```

현재 적용된 최소 구조:

```text
ktooh-media-batch/
├── src/
│   ├── common/
│   │   ├── config.py
│   │   └── logging_config.py
│   ├── measurement/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── pipeline.py
│   │   ├── dashboard_registry.py
│   │   ├── collector.py
│   │   ├── parser_demographic.py
│   │   ├── parser_floating.py
│   │   ├── normalization_demographic.py
│   │   ├── normalization_floating.py
│   │   ├── attribution.py
│   │   ├── loader_audience.py
│   │   ├── loader_traffic.py
│   │   ├── service.py
│   │   └── verify.py
│   └── trajectory/
│       ├── __init__.py
│       ├── contracts.py
│       ├── main.py
│       ├── pipeline.py
│       ├── stages.py
│       └── verify.py
├── samples/
├── PLAN.md
└── PLAN_TRAJECTORY_FROM_06.md
```

반영 완료:

- [x] measurement batch 코드를 `src/measurement`로 이동
- [x] `config.py`, `logging_config.py`는 `src/common`으로 이동
- [x] trajectory는 아직 노트북 알고리즘 복사 없이 계약/CLI/wrapper/검증 경계까지 생성
- [x] measurement CLI entrypoint는 `src.measurement.main:app`로 변경
- [x] measurement 테스트는 `src.measurement.*` import를 사용
- [x] 샘플 jsonl은 저장소 내부 `samples/`를 사용
- [x] trajectory CLI entrypoint는 `src.trajectory.main:app`로 추가
- [x] trajectory `plan`, `verify-artifacts` 명령을 추가

### 3.2 상위 실행 흐름

```text
run-trajectory-batch
-> preprocess-groundplane
-> local-stitch
-> build-revised-global-input
-> build-topology-static
-> solve-global-edges
-> finalize-global-units
-> build-hourly-metrics
-> build-route-family
-> save-artifacts
-> verify
```

### 3.3 Measurement Batch와의 경계

- [x] `project-pooh-kt/docs/floating.jsonl`의 raw object event는 measurement batch와 trajectory batch가 함께 참조할 수 있는 공통 원천이다.
- [x] measurement batch는 raw event를 단일 camera 관측치로 해석하고 `traffic`, 선택적 `audience_event_fact`까지만 적재한다.
- [x] trajectory batch는 같은 raw를 preprocess/local stitch를 거쳐 `prepared_all`, `stitched_df_all`, `presence_episode_df`를 만든 뒤 inter-camera association 결과를 적재한다.
- [x] raw 단계에 없는 `global_unit_id`, `camera_path`, `transition_node_id`, `route_family_id`는 모두 trajectory 전용 파생 컬럼이다.
- [x] measurement batch는 camera 단위 KPI와 aggregate 책임만 가진다.
- [x] trajectory batch는 local/global unit, visible dwell union, route family 책임만 가진다.
- [x] 두 배치는 실행 경로와 저장 계약을 분리하고, 공통점은 raw 수집 계약과 UTC 시간 계약만 공유한다.
- [x] 단, trajectory batch는 dashboard 연계를 위해 `media_id`, `camera`, `campaign_id`, `creative_id` 귀속 차원은 함께 저장한다.

실행/패키지 경계:

- [x] measurement batch CLI와 trajectory batch CLI는 분리한다.
- [x] measurement batch 테스트와 trajectory batch 테스트는 분리한다.
- [x] measurement batch release와 trajectory batch release는 독립 가능해야 한다.
- [x] 공통 유틸이 필요하면 `src/common` 수준의 작은 공유 계층만 두고, 배치 로직은 공유하지 않는다.
- [x] 현재 공통 계층은 `config`, `logging_config`만 포함한다.

정리:

- `floating.jsonl` 원천 필드: `id`, `type`, `start_time`, `end_time`, `dwell`, `move_dist`, `status`, `bboxes`, `location`
- measurement batch 산출: `traffic`, 선택적 `audience_event_fact`
- trajectory batch 산출: `trajectory_presence_episodes`, `trajectory_global_units`, `trajectory_global_presence_episodes`, `trajectory_hourly_metrics`, `trajectory_route_families`

---

## 4. 적재 대상 계약

### 4.1 파일 적재 대상

- [x] `prepared_all`
- [x] `stitched_df_all`
- [x] `presence_episode_df`
- [x] `episode_units_df`
- [x] `transition_units_df`
- [x] `transition_nodes_df`
- [x] `global_candidate_edges_df`
- [x] `selected_global_edges_df`
- [x] `base_global_units_df`
- [x] `base_global_unit_members_df`
- [x] `global_units_df`
- [x] `global_presence_episode_df`
- [x] `hourly_metric_summary_df`
- [x] `route_family_df`

비고:

- [x] 위 항목은 `src/trajectory/contracts.py`의 `ARTIFACT_SPECS`에 `run_root` 상대 경로와 필수 컬럼 계약으로 고정했다.

### 4.2 DB 적재 우선순위

1차 우선:

- [x] `presence_episode`
- [x] `global_units`
- [x] `global_presence_episode`
- [x] `hourly_metric_summary`
- [x] `route_family`
- [x] `trajectory_hourly_metrics_dashboard_v`
- [x] `trajectory_hourly_heatmap_v`
- [x] `trajectory_spatial_heatmap_cells`
- [x] `trajectory_spatial_heatmap_dashboard_v`

2차 후보:

- [ ] `transition_nodes`
- [ ] `transition_units`
- [ ] `selected_global_edges`
- [ ] `global_candidate_edges`

### 4.3 DB 테이블 초안

- [x] `trajectory_presence_episodes`
- [x] `trajectory_global_units`
- [x] `trajectory_global_presence_episodes`
- [x] `trajectory_hourly_metrics`
- [x] `trajectory_route_families`

### 4.4 Dashboard 노출 초안

1차 조회 단위:

- [x] `media_id` 필터
- [x] `camera_name` 또는 `camera_code` 필터
- [x] `campaign_id` 필터
- [x] `creative_id` 필터

1차 노출 산출물:

- [x] 시간대별 `unique_global_units`, `visible_unique_units`, `total_visible_dwell_s`
- [x] camera x hour heatmap
- [x] 지도 위 spatial heatmap
- [x] 상위 `route_family`
- [x] `global_unit` 상세와 연결 episode 목록

권장:

- [x] raw `trajectory_hourly_metrics`는 배치 원본으로 유지
- [x] dashboard는 별도 집계 view `trajectory_hourly_metrics_dashboard_v`, `trajectory_hourly_heatmap_v`를 읽는다
- [x] 지도 heatmap은 별도 공간 집계 테이블 또는 view `trajectory_spatial_heatmap_dashboard_v`를 읽는다

### 4.5 GPS / 지도 좌표 최소 추가 작업

1차 결정:

- [x] 기준 좌표계를 **`EPSG:4326`**으로 고정한다.
- [x] camera별 `world_points -> geo` 변환 규칙을 어디서 관리할지 결정
- [x] point 단위 heatmap으로 갈지, grid cell / polygon 단위 heatmap으로 갈지 결정

권장:

- [x] 저장은 `grid cell` 중심으로 단순화한다. (집계 효율 및 데이터 용량 고려)
- [x] 최종 조회 좌표계는 **`EPSG:4326`**을 기본으로 사용한다.
- [x] raw point 전체를 dashboard로 직접 내리지 않고 batch에서 cell 집계를 만든다.
- [x] 1차 변환 규칙은 `trajectory-batch load-dashboard --geo-transform`의 camera별 affine 설정으로 주입한다.

부록:

- [x] 컬럼 스냅샷은 `APPENDIX_06_NOTEBOOK_OUTPUT_COLUMNS.md`에 정리한다.

---

## 5. 핵심 도메인 모델

### 5.1 Local Layer

- [ ] `PreparedTracklet`
- [ ] `StitchedTrajectory`
- [ ] `PresenceEpisode`
- [ ] **`LocalConfig`** (Stay Zone survival thresholds 등 포함)

### 5.2 Revised Global Input Layer

- [ ] `EpisodeUnit`
- [ ] `TransitionUnit`
- [ ] `TransitionNode`

### 5.3 Global Layer

- [ ] `GlobalCandidateEdge`
- [ ] `SelectedGlobalEdge`
- [ ] `BaseGlobalUnit`
- [ ] `BaseGlobalUnitMember`
- [ ] `GlobalUnit`
- [ ] `GlobalPresenceEpisode`
- [ ] **`GlobalConfig`** (max_edge_cost, unmatched_cost 등 파라미터 버전 관리)

### 5.4 Metrics Layer

- [ ] `HourlyMetricSummary`
- [ ] `RouteFamily`

---

## 6. 스키마 계약 초안

### 6.1 `trajectory_presence_episodes`

필수 컬럼:

- [ ] `target_date`
- [ ] `media_id`
- [ ] `camera_code`
- [ ] `local_unit_id`
- [ ] `camera_name`
- [ ] `campaign_id`
- [ ] `creative_id`
- [ ] `episode_id`
- [ ] `aoi_id`
- [ ] `stay_zone_id`
- [ ] `episode_start_time`
- [ ] `episode_end_time`
- [ ] `episode_dwell_s`
- [ ] `observed_time_s`
- [ ] `unobserved_gap_s`
- [ ] `observed_support_ratio`
- [ ] `max_gap_s`
- [ ] `median_gap_s`
- [ ] `kpi_eligible`
- [ ] `local_confidence`
- [ ] `support_tracklet_ids`
- [ ] `support_tracklet_count`
- [ ] `anchor_drift_m`
- [ ] `stay_state_fraction`
- [ ] `occlusion_support`
- [ ] `episode_status`
- [ ] `artifact_flag`
- [ ] `recovery_mode`
- [ ] `presence_episode_version`

권장 컬럼명 정리:

- [x] 적재 테이블 컬럼은 `episode_kpi_eligible -> kpi_eligible`
- [x] 적재 테이블 컬럼은 `episode_confidence -> local_confidence`
- [x] 시간 컬럼은 `episode_start_time`, `episode_end_time`로 유지
- [x] `source_batch_id`, `target_date`, `pipeline_version`, `created_at_utc` 같은 적재 메타 컬럼은 노트북 산출물 외부에서 loader가 부여
- [x] dashboard 필터용으로 `media_id`, `camera_code`, `campaign_id`, `creative_id`는 필수 차원으로 본다

### 6.2 `trajectory_global_units`

필수 컬럼:

- [ ] `target_date`
- [ ] `media_id`
- [ ] `camera_code`
- [ ] `global_unit_id`
- [ ] `campaign_id`
- [ ] `creative_id`
- [ ] `seed_kind`
- [ ] `global_start_time`
- [ ] `global_end_time`
- [ ] `elapsed_dwell_s`
- [ ] `n_cameras`
- [ ] `camera_path`
- [ ] `global_confidence`
- [ ] `visible_start_time`
- [ ] `visible_end_time`
- [ ] `visible_episode_count`
- [ ] `visible_camera_count`
- [ ] **`config_version`** (튜닝 파라미터 세트 식별자)
- [ ] **`repeated_camera_validation`** (동일 카메라 재진입 유지 로직 적용 여부/결과 플래그)

파생/검증 컬럼:

- [x] `repeated_camera`는 저장 필수 컬럼보다 검증용 계산 컬럼에 가깝다.
- [x] 필요하면 materialized view 또는 QC 쿼리에서 `camera_path`로 재계산한다.
- [x] `camera_code`는 대표 camera 1개를 저장하고, 전체 경로는 `camera_path`로 유지한다.
- [x] campaign/creative 귀속은 assignment 결과를 바탕으로 loader 단계에서 해소한다.

### 6.3 `trajectory_global_presence_episodes`

필수 컬럼:

- [ ] `target_date`
- [ ] `media_id`
- [ ] `camera_code`
- [ ] `global_unit_id`
- [ ] `local_unit_id`
- [ ] `camera_name`
- [ ] `campaign_id`
- [ ] `creative_id`
- [ ] `episode_start_time`
- [ ] `episode_end_time`
- [ ] `episode_dwell_s`
- [ ] `episode_kpi_eligible`
- [ ] `assignment_mode`

### 6.4 `trajectory_hourly_metrics`

필수 컬럼:

- [ ] `target_date`
- [ ] `media_id`
- [ ] `camera_code`
- [ ] `campaign_id`
- [ ] `creative_id`
- [ ] `date`
- [ ] `hour`
- [ ] `hour_start`
- [ ] `hour_end`
- [ ] `unique_global_units`
- [ ] `single_camera_units`
- [ ] `multi_camera_units`
- [ ] `mean_n_cameras`
- [ ] `visible_unique_units`
- [ ] `visible_episode_count`
- [ ] `visible_camera_count`
- [ ] `kpi_visible_unique_units`
- [ ] `kpi_visible_episode_count`
- [ ] `total_visible_dwell_s`
- [ ] `avg_visible_dwell_per_unit_s`
- [ ] `median_visible_episode_dwell_s`
- [ ] `p75_visible_episode_dwell_s`
- [ ] `p90_visible_episode_dwell_s`
- [ ] `kpi_total_visible_dwell_s`
- [ ] `kpi_avg_visible_dwell_per_unit_s`
- [ ] `metrics_version`

비고:

- [x] `trajectory_hourly_metrics`는 batch 원본 fact 성격으로 유지한다.
- [x] dashboard 조회용 rollup은 view에서 다시 만든다.

### 6.5 `trajectory_hourly_metrics_dashboard_v`

필수 컬럼:

- [ ] `target_date`
- [ ] `media_id`
- [ ] `camera_code`
- [ ] `campaign_id`
- [ ] `creative_id`
- [ ] `date`
- [ ] `hour`
- [ ] `hour_start`
- [ ] `visible_unique_units`
- [ ] `total_visible_dwell_s`
- [ ] `avg_visible_dwell_per_unit_s`
- [ ] `unique_global_units`
- [ ] `route_family_count`

용도:

- [x] dashboard overview / 상세분석 시계열 조회

### 6.6 `trajectory_hourly_heatmap_v`

필수 컬럼:

- [ ] `target_date`
- [ ] `media_id`
- [ ] `camera_code`
- [ ] `camera_name`
- [ ] `campaign_id`
- [ ] `creative_id`
- [ ] `hour`
- [ ] `heatmap_value`
- [ ] `visible_unique_units`
- [ ] `total_visible_dwell_s`

용도:

- [x] camera x hour 히트맵 조회
- [x] `heatmap_value`는 1차에서 `visible_unique_units` 또는 `total_visible_dwell_s` 중 선택 가능하게 둔다

### 6.7 `trajectory_spatial_heatmap_cells`

필수 컬럼:

- [ ] `target_date`
- [ ] `media_id`
- [ ] `camera_code`
- [ ] `camera_name`
- [ ] `campaign_id`
- [ ] `creative_id`
- [ ] `hour`
- [ ] `cell_id`
- [ ] `cell_centroid_lat`
- [ ] `cell_centroid_lng`
- [ ] `cell_polygon_wkt` 또는 `cell_geojson`
- [ ] `point_count`
- [ ] `visible_unique_units`
- [ ] `total_visible_dwell_s`
- [ ] `heatmap_value`
- [ ] **`spatial_ref`** (기본값: 'EPSG:4326')

용도:

- [x] 지도 오버레이용 원본 공간 집계 테이블
- [x] batch에서 point를 공간 cell로 묶은 결과 저장

비고:

- [x] 1차는 point cloud 전체 저장보다 `cell_id` 기반 집계가 더 안전하다.
- [x] `spatial_ref`는 **`EPSG:4326`** 고정을 원칙으로 한다.

### 6.8 `trajectory_spatial_heatmap_dashboard_v`

필수 컬럼:

- [ ] `target_date`
- [ ] `media_id`
- [ ] `camera_code`
- [ ] `camera_name`
- [ ] `campaign_id`
- [ ] `creative_id`
- [ ] `hour`
- [ ] `cell_id`
- [ ] `lat`
- [ ] `lng`
- [ ] `geometry_geojson`
- [ ] `heatmap_value`
- [ ] `visible_unique_units`
- [ ] `total_visible_dwell_s`

용도:

- [x] dashboard 지도 API의 직접 조회 view
- [x] 프론트가 바로 heatmap layer를 그릴 수 있는 응답 형식 제공

### 6.9 `trajectory_route_families`

필수 컬럼:

- [ ] `target_date`
- [ ] `media_id`
- [ ] `camera_code`
- [ ] `campaign_id`
- [ ] `creative_id`
- [ ] `route_family_id`
- [ ] `camera_path`
- [ ] `unit_count`
- [ ] `visible_unit_count`
- [ ] `median_visible_dwell_s`
- [ ] `mean_route_confidence`
- [ ] `median_elapsed_s`
- [ ] `route_grid_version`

비고:

- [x] 현재 06 노트북 산출물에는 `start_camera`, `end_camera`, `share`가 없다.
- [x] 필요하면 `camera_path` 파싱과 전체 unit 대비 비율 계산으로 loader/view에서 추가한다.

---

## 7. 구현 단계

### 7.1 Phase A. Notebook Contract Extraction (`Tidy`)

- [x] 06 노트북의 stage 입출력 계약을 문서로 분리
- [x] 각 pickle 산출물의 컬럼 목록을 고정
- [x] 노트북 의존 함수 목록과 호출 순서를 명시

완료 조건:

- [x] `06` 노트북을 안 열어도 stage/산출물 계약을 이해할 수 있다.
- [x] `src/trajectory/contracts.py`와 `tests/trajectory/test_contracts.py`로 stage 순서, 의존 함수, artifact 계약을 검증한다.

### 7.2 Phase B. Stage Wrapperization (`Feature`)

- [x] preprocess wrapper 추가
- [x] local stitch wrapper 추가
- [x] revised global wrapper 추가
- [x] metrics/routes wrapper 추가

완료 조건:

- [x] 노트북 함수 호출을 batch 코드에서 재현할 수 있다.

비고:

- [x] `src/trajectory/stages.py`는 외부 runner/notebook 함수들을 주입받는 Boundary/Shell이다.
- [x] 06 노트북 내부 함수의 알고리즘 복사는 아직 하지 않고, 호출 순서와 인자 계약을 테스트로 고정했다.

### 7.3 Phase C. Artifact Storage (`Feature`)

- [x] `run_root` 기준 artifact 저장 경로 고정
- [x] pickle/parquet 중 유지 포맷 확정
- [x] stage별 output naming 고정
- [x] dashboard view source가 되는 원본 테이블/뷰 naming 고정
- [x] spatial heatmap intermediate artifact naming 고정

### 7.4 Phase D. DB Loader (`Feature`)

- [x] `presence_episode` loader
- [x] `global_units` loader
- [x] `global_presence_episode` loader
- [x] `hourly_metric_summary` loader
- [x] `route_family` loader
- [x] `media_id`, `camera_code` 차원 적재
- [~] `campaign_id`, `creative_id` 귀속 해소
- [x] `trajectory_hourly_metrics_dashboard_v` view 생성
- [x] `trajectory_hourly_heatmap_v` view 생성
- [x] `world_points -> geo/grid cell` 변환 단계 추가
- [x] `trajectory_spatial_heatmap_cells` loader 추가
- [x] `trajectory_spatial_heatmap_dashboard_v` view 생성

완료 조건:

- [x] dashboard가 `media_id + camera + campaign + creative` 필터로 trajectory 결과를 읽을 수 있다.
- [x] hourly 원본과 dashboard view의 역할이 분리된다.
- [x] 지도 heatmap이 사용할 공간 좌표와 geometry가 안정적으로 제공된다.

### 7.5 Phase E. Verification (`Feature`)

- [x] 파일 산출물 존재 검증
- [x] loader dry-run row count 검증
- [ ] 주요 row count 비교
- [ ] notebook 결과와 golden 비교
- [ ] attribution null/중복/충돌 검증
- [ ] hourly view / heatmap view 샘플 조회 검증
- [ ] geo transform 샘플 검증
- [ ] spatial heatmap cell 집계 검증
- [ ] 지도 위 표시 위치 sanity check

---

## 8. 검증 전략

### 8.1 파일 기반 검증

- [ ] 06 노트북 산출 pickle과 row count 비교
- [ ] 컬럼셋 비교
- [ ] null/중복/시간 역전 검증
- [x] artifact 존재 검증
- [x] spatial heatmap intermediate artifact 존재 검증

### 8.2 로직 검증

- [ ] `presence_episode_count`
- [ ] `global_unit_count`
- [ ] `assignment_mode` 분포
- [ ] `hourly` 24개 head 비교
- [ ] `route_family` 상위 row 비교
- [ ] `media_id + camera` 필터 결과가 원본 camera 범위와 일치하는지 검증
- [ ] `campaign_id`, `creative_id` 귀속률과 충돌 케이스 검증
- [ ] heatmap 집계값과 hourly 원본 합산값 일치 검증
- [ ] geo 변환 후 point/cell이 camera 실제 영역 밖으로 벗어나지 않는지 검증
- [x] 동일 hour 기준 spatial heatmap 총합과 source point 수가 일관되는지 검증

### 8.3 운영 검증

- [x] dashboard가 필요한 trajectory 테이블을 실제로 읽을 수 있는지 확인
- [x] UTC 저장 / 사용자 시간대 조회 정책을 동일하게 적용
- [x] dashboard trajectory 화면이 `media_id`, `camera`, `campaign`, `creative` 필터를 지원하는지 확인
- [ ] dashboard view와 heatmap 응답 시간이 허용 범위인지 확인
- [ ] 지도 SDK에서 spatial heatmap layer가 정상 렌더링되는지 확인
- [ ] 지도 zoom level별 응답량과 렌더링 성능이 허용 범위인지 확인

---

## 9. `ktooh-dashboard-poc` 최소 변경 목록

### 9.1 목표

- [x] 기존 measurement KPI API와 충돌 없이 trajectory 조회 API를 별도 경로로 추가한다.
- [x] 1차는 read-only 조회만 지원한다.
- [x] 기존 `AnalyticsRepository`에 무리하게 섞지 않고 trajectory 전용 모델/조회 경계를 만든다.

### 9.2 최소 모델 추가

대상 위치:

- [x] `ktooh-dashboard-poc/app/models/`
- [x] `ktooh-dashboard-poc/alembic/versions/`

추가 모델:

- [x] `trajectory_presence_episode.py`
- [x] `trajectory_global_unit.py`
- [x] `trajectory_global_presence_episode.py`
- [x] `trajectory_hourly_metric.py`
- [x] `trajectory_route_family.py`

선택:

- [x] `trajectory_spatial_heatmap_cell.py`

view 또는 읽기 전용 모델:

- [x] `trajectory_hourly_metrics_dashboard_view.py`
- [x] `trajectory_hourly_heatmap_view.py`
- [x] `trajectory_spatial_heatmap_dashboard_view.py`

최소 컬럼 원칙:

- [x] 모든 trajectory 조회 모델은 `media_id`, `camera_code`, `campaign_id`, `creative_id` 필터 키를 가진다.
- [x] 시간 컬럼은 UTC 저장, 조회 시 timezone helper를 재사용한다.
- [x] 지도 heatmap 모델은 `lat`, `lng` 또는 `geometry_geojson`을 포함한다.

### 9.3 최소 Repository 추가

대상 위치:

- [x] `ktooh-dashboard-poc/app/repositories/`

추가 파일:

- [x] `trajectory_repository.py`
- [ ] 필요 시 `trajectory_map_repository.py`

최소 메서드:

- [x] `load_hourly_metrics(query)`
- [x] `load_camera_hour_heatmap(query)`
- [x] `load_spatial_heatmap(query)`
- [x] `load_route_families(query)`
- [x] `load_global_units(query)`
- [x] `load_global_unit_detail(global_unit_id, query)`
- [x] `load_global_presence_episodes(global_unit_id, query)`

구현 원칙:

- [x] 기존 `analytics_repository.py`는 `agg_audience_minute` 전용으로 유지한다.
- [x] trajectory 조회는 trajectory 전용 repository에서 끝낸다.
- [x] 지도 조회는 bbox, zoom, hour 필터를 받을 수 있게 둔다.

### 9.4 최소 Service 추가

대상 위치:

- [x] `ktooh-dashboard-poc/app/services/analytics/`

추가 파일:

- [x] `trajectory_service.py`
- [ ] 필요 시 `trajectory_map_service.py`

최소 메서드:

- [x] `get_hourly_metrics(...)`
- [x] `get_camera_hour_heatmap(...)`
- [x] `get_spatial_heatmap(...)`
- [x] `get_route_families(...)`
- [x] `get_global_units(...)`
- [x] `get_global_unit_detail(...)`

책임:

- [x] repository 결과를 dashboard 응답 형태로 조립
- [x] timezone 변환 적용
- [x] heatmap metric 선택값(`visible_unique_units`, `total_visible_dwell_s`) 처리
- [x] 지도 응답에서 bbox/zoom 기반 제한 적용

### 9.5 최소 Schema 추가

대상 위치:

- [x] `ktooh-dashboard-poc/app/schemas/`

추가 파일:

- [x] `trajectory_filter.py`
- [x] `trajectory_hourly.py`
- [x] `trajectory_route.py`
- [x] `trajectory_unit.py`
- [x] `trajectory_heatmap.py`

최소 응답 스키마:

- [x] `TrajectoryHourlyPoint`
- [x] `TrajectoryHourlyResponse`
- [x] `TrajectoryCameraHeatmapCell`
- [x] `TrajectoryCameraHeatmapResponse`
- [x] `TrajectorySpatialHeatmapCell`
- [x] `TrajectorySpatialHeatmapResponse`
- [x] `TrajectoryRouteFamilyItem`
- [x] `TrajectoryRouteFamilyResponse`
- [x] `TrajectoryGlobalUnitItem`
- [x] `TrajectoryGlobalUnitDetail`

### 9.6 최소 API 추가

대상 위치:

- [x] `ktooh-dashboard-poc/app/routes/analytics/`

추가 파일:

- [x] `trajectory.py`

최소 endpoint:

- [x] `GET /api/v1/analysis/trajectory/hourly`
- [x] `GET /api/v1/analysis/trajectory/camera-heatmap`
- [x] `GET /api/v1/analysis/trajectory/spatial-heatmap`
- [x] `GET /api/v1/analysis/trajectory/routes`
- [x] `GET /api/v1/analysis/trajectory/units`
- [x] `GET /api/v1/analysis/trajectory/units/{global_unit_id}`

최소 query parameter:

- [x] `start_date`
- [x] `end_date`
- [x] `timezone`
- [x] `media_ids`
- [x] `camera_codes`
- [x] `campaign_ids`
- [x] `creative_ids`
- [x] `metric`

지도 heatmap 전용 추가 parameter:

- [x] `bbox`
- [x] `zoom`
- [x] `hour`

원칙:

- [x] 기존 `/analysis/watch-pattern` 등 measurement API는 유지
- [x] trajectory API는 `/analysis/trajectory/*`로 분리

### 9.7 Provider / Container 변경

대상 위치:

- [x] `ktooh-dashboard-poc/app/providers/repository.py`
- [x] `ktooh-dashboard-poc/app/providers/service.py`
- [x] `ktooh-dashboard-poc/app/container.py`

최소 작업:

- [x] `TrajectoryRepository` 등록
- [x] `TrajectoryService` 등록
- [x] 새 route 의존성 주입 연결

### 9.8 최소 프론트 연결

대상 위치:

- [x] `ktooh-dashboard-poc/app/templates/pages/dashboard/map.html`
- [x] `ktooh-dashboard-poc/app/templates/pages/dashboard/details.html`
- [x] `ktooh-dashboard-poc/app/static/features/map/map.js`
- [x] 필요 시 `app/static/features/dashboard/details.js`

1차 UI:

- [x] trajectory 탭 또는 카드 추가
- [x] 시간대 패턴 차트
- [x] camera x hour heatmap
- [x] 지도 위 spatial heatmap
- [x] 상위 route family 테이블
- [x] global unit 상세 모달

원칙:

- [x] 기존 measurement dashboard를 덮어쓰지 않는다.
- [x] trajectory 섹션을 별도 카드/탭으로 추가한다.

### 9.9 최소 Migration / 성능 작업

- [x] **단일 Alembic Migration 버전** 생성 (테이블 및 뷰 통합)
- [x] `media_id`, `camera_code`, `campaign_id`, `creative_id`, 시간 컬럼 index 추가
- [x] spatial heatmap용 geometry 또는 cell index 전략 추가
- [x] **배치 시점의 Spatial Cell 사전 집계(Materialized View 등)** 검토

권장 index:

- [x] `(media_id, target_date, hour_start)`
- [x] `(camera_code, target_date, hour_start)`
- [x] `(campaign_id, creative_id, hour_start)`
- [x] spatial 조회용 `cell_id` 또는 geometry index (PostGIS GIST index 등)

### 9.10 최소 구현 순서

1. [x] SQLAlchemy 모델 + migration 추가
2. [x] trajectory repository 추가
3. [x] trajectory service + schema 추가
4. [x] trajectory API route 추가
5. [x] map/details 화면에 trajectory 조회 연결
6. [x] spatial heatmap 지도 렌더링 연결
7. [ ] 샘플 데이터 기준 응답/성능 검증

### 9.11 완료 기준

- [x] `ktooh-dashboard-poc`가 trajectory 원본 테이블과 dashboard view를 읽을 수 있다.
- [x] `media_id + camera + campaign + creative` 필터가 동작한다.
- [x] 시간대 패턴, camera heatmap, spatial heatmap, route family, global unit detail이 모두 조회된다.

---

## 10. 현재 결론

- [x] 현재 `ktooh-media-batch/PLAN.md`는 06 노트북 기반 계획 문서가 아니다.
- [x] 06 노트북 기반 적재 계획은 별도 문서가 필요하다.
- [x] 이 문서는 그 별도 문서의 1차 초안이다.

---

## 11. 다음 액션

1. [x] 이 문서 기준으로 trajectory 적재 대상 테이블 컬럼을 더 구체화한다.
2. [x] 06 노트북 산출물 컬럼 스냅샷을 추출해 부록 문서를 만든다.
3. [x] measurement batch와 trajectory batch의 경계를 문서로 명확히 정리한다.
4. [x] trajectory 필터 기준을 `media_id + camera`로 확정한다.
5. [x] trajectory에 `campaign_id`, `creative_id` 귀속 포함 정책을 반영한다.
6. [x] `hourly_metric_summary` 원본 + dashboard용 집계 view + heatmap 계획을 반영한다.
7. [x] GPS/지도 heatmap을 위한 공간 좌표 변환과 spatial heatmap 계획을 추가한다.
8. [x] `ktooh-dashboard-poc` 최소 API/모델/Repository 변경 목록을 추가한다.
9. [x] trajectory stage/artifact 계약을 `src/trajectory/contracts.py`로 고정한다.
10. [x] trajectory stage wrapper를 `src/trajectory/stages.py`로 고정한다.
11. [x] 다음 dashboard 연동 작업은 `PLAN_DASHBOARD_TRAJECTORY_INTEGRATION.md`에서 작은 작업 단위로 관리한다.

---
**References:**
- State-space Modeling for Pedestrian Tracking
- Graph-based Data Association in Multiple-Object Tracking
- Topology-aware Multi-camera Association Strategies
