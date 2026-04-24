# PLAN: Trajectory Reimplementation

## 0. 문서 목적

이 문서는 `ktooh-media-batch/src/trajectory`가 06 노트북 함수를 호출하지 않고 자체 Python 코드로 trajectory batch를 실행하도록 전환하기 위한 계획서다.

기존 문서와의 관계:

- `PLAN_TRAJECTORY_FROM_06.md`: 06 노트북 기반 산출물과 적재 계약
- `APPENDIX_06_NOTEBOOK_OUTPUT_COLUMNS.md`: 노트북 artifact 컬럼 스냅샷
- 이 문서: 노트북 호출 제거와 자체 구현 전환 계획

상태 표기:

- `[ ]` 미착수
- `[~]` 진행 중
- `[x]` 완료

## 1. 목표와 비목표

### 1.1 목표

- [ ] `src/trajectory/stages.py`에서 06 노트북 내부 함수 호출 의존을 제거한다.
- [ ] 노트북 산출물과 동일한 artifact 계약을 자체 코드로 생성한다.
- [ ] 핵심 로직은 작고 순수한 함수로 분리한다.
- [ ] I/O, pickle 저장, 외부 파일 읽기, DB 적재는 Boundary/Shell에 격리한다.
- [ ] 각 단계는 golden fixture와 unit test로 검증한다.
- [ ] dashboard 적재 계약은 기존 `PLAN_TRAJECTORY_FROM_06.md`와 호환한다.

### 1.2 비목표

- [ ] 한 번에 모든 association 알고리즘을 재작성하지 않는다.
- [ ] 노트북 exploratory QC 화면을 옮기지 않는다.
- [ ] dashboard API 구현을 이 문서 범위에 섞지 않는다.
- [ ] measurement batch 로직을 trajectory 구현에 재사용하지 않는다.
- [ ] 검증 기준 없이 노트북 결과와 다른 알고리즘으로 바꾸지 않는다.

### 1.3 완료 정의

- [ ] `trajectory-batch` 실행이 노트북 파일 import 없이 완료된다.
- [ ] `prepared_all`, `stitched_df_all`, `presence_episode_df`, `global_units_df`, `global_presence_episode_df`, `hourly_metric_summary_df`, `route_family_df`를 자체 코드로 생성한다.
- [ ] golden artifact 기준 row count, 컬럼셋, 주요 metric이 허용 오차 내에서 일치한다.
- [ ] `uv run pytest`와 `uv run ruff check .`가 통과한다.
- [ ] `PLAN_TRAJECTORY_FROM_06.md`의 DB/dashboard 계약을 깨지 않는다.

## 2. 현재 기준

현재 `src/trajectory` 구조:

```text
src/trajectory/
├── __init__.py
├── contracts.py
├── main.py
├── pipeline.py
├── stages.py
└── verify.py
```

현재 역할:

- [x] `contracts.py`: stage 순서, artifact 경로, 필수 컬럼 계약
- [x] `pipeline.py`: 순수 plan builder
- [x] `main.py`: `plan`, `verify-artifacts` CLI
- [x] `verify.py`: artifact 존재 검증
- [x] `stages.py`: 외부 runner/notebook 함수 호출 Boundary/Shell

재구현 원칙:

- [x] `contracts.py`는 유지한다.
- [x] `stages.py`는 점진적으로 자체 구현을 호출하도록 바꾼다.
- [x] 노트북은 당분간 reference implementation으로만 사용한다.
- [x] golden fixture 없이 알고리즘을 바꾸지 않는다.

## 3. 전환 전략

### 3.1 권장 순서

1. [ ] golden artifact 고정
2. [ ] artifact loader/validator 구현
3. [ ] metrics와 route family부터 자체 구현
4. [ ] global unit finalization 자체 구현
5. [ ] episode assignment 자체 구현
6. [ ] candidate edge scoring과 solver 자체 구현
7. [ ] revised global input 자체 구현
8. [ ] local stitch와 presence episode recovery 자체 구현
9. [ ] preprocess/groundplane boundary 자체 구현 또는 외부 모듈 의존 최소화
10. [ ] 노트북 호출 제거

### 3.2 왜 이 순서인가

- [x] `hourly_metric_summary`와 `route_family`는 입력/출력 계약이 작고 dashboard 가치가 높다.
- [x] `global_unit` visible interval union은 순수 함수로 검증하기 좋다.
- [x] candidate edge scoring, topology, local stitch는 파라미터와 geometry 영향이 커서 나중에 치환한다.
- [x] preprocess는 S3, geo transform, walkable region 등 I/O와 외부 자원이 많아 마지막에 다룬다.

## 4. 구현 단위

### 4.1 Unit A. Golden Artifact Fixture 고정 (`Tidy`)

목표:

- [ ] 노트북 결과와 자체 구현 결과를 비교할 기준을 만든다.

작업:

- [ ] `tests/fixtures/trajectory/golden/` 경로 결정
- [ ] 최소 golden run 선정
- [ ] golden artifact 목록 고정
  - [ ] `presence_episode_df.pkl`
  - [ ] `transition_units_df.pkl`
  - [ ] `transition_nodes_df.pkl`
  - [ ] `global_units_df.pkl`
  - [ ] `global_presence_episode_df.pkl`
  - [ ] `hourly_metric_summary_df.pkl`
  - [ ] `route_family_df.pkl`
- [ ] golden manifest 작성
  - [ ] source notebook path
  - [ ] run date
  - [ ] config hash 또는 config snapshot
  - [ ] row counts
  - [ ] column sets

완료 조건:

- [ ] 테스트가 golden artifact 존재 여부를 확인한다.
- [ ] golden artifact가 없으면 명확한 skip 또는 실패 정책을 따른다.

검증:

- [ ] `tests/trajectory/test_golden_contract.py`

### 4.2 Unit B. Artifact Loader와 Column Validator (`Feature`)

목표:

- [ ] pickle artifact를 안전하게 읽고 컬럼 계약을 검증한다.

작업:

- [ ] `src/trajectory/artifacts.py`
- [ ] `load_pickle_artifact(path)`
- [ ] `validate_required_columns(frame, spec)`
- [ ] `summarize_artifact(frame)`
- [ ] artifact별 row count/column set summary 생성

완료 조건:

- [ ] 누락 파일, 잘못된 확장자, 필수 컬럼 누락을 명확한 예외로 처리한다.
- [ ] 검증 로직은 pandas I/O를 제외하면 순수 함수로 분리한다.

검증:

- [ ] 정상 artifact 검증 테스트
- [ ] 컬럼 누락 테스트
- [ ] 빈 frame 테스트

### 4.3 Unit C. Route Family 자체 구현 (`Feature`)

목표:

- [ ] `kt_route_grid_v2.build_route_family_table` 호출을 제거할 수 있게 한다.

입력:

- [ ] `global_units_df`
- [ ] `global_presence_episode_df`

출력:

- [ ] `route_family_df`

작업:

- [ ] `src/trajectory/routes.py`
- [ ] `build_route_family_table(global_units, global_presence)`
- [ ] `route_family_id = "RF_" + camera_path.replace(">", "_")`
- [ ] `unit_count`
- [ ] `visible_unit_count`
- [ ] `median_visible_dwell_s`
- [ ] `mean_route_confidence`
- [ ] `median_elapsed_s`
- [ ] `route_grid_version`

완료 조건:

- [ ] golden `route_family_df`와 컬럼셋이 일치한다.
- [ ] 주요 집계값이 일치한다.
- [ ] 빈 input을 안정적으로 처리한다.

검증:

- [ ] pure unit test
- [ ] golden 비교 test

### 4.4 Unit D. Hourly Metrics 자체 구현 (`Feature`)

목표:

- [ ] `build_corrected_hourly_metrics` 노트북 함수 호출을 제거할 수 있게 한다.

입력:

- [ ] `global_units_df`
- [ ] `global_presence_episode_df`

출력:

- [ ] `hourly_metric_summary_df`

작업:

- [ ] `src/trajectory/metrics.py`
- [ ] hourly bucket 생성
- [ ] `global_unit_id` 기준 visible interval union
- [ ] `unique_global_units`
- [ ] `single_camera_units`
- [ ] `multi_camera_units`
- [ ] `mean_n_cameras`
- [ ] `visible_unique_units`
- [ ] `visible_episode_count`
- [ ] `visible_camera_count`
- [ ] `kpi_visible_unique_units`
- [ ] `total_visible_dwell_s`
- [ ] percentile metrics

완료 조건:

- [ ] 노트북 hourly 결과와 row count/컬럼셋이 일치한다.
- [ ] 핵심 수치가 허용 오차 내에서 일치한다.
- [ ] DST와 timezone 변환은 여기서 처리하지 않고 UTC 기준으로만 계산한다.

검증:

- [ ] interval union unit test
- [ ] hour boundary test
- [ ] golden 비교 test

### 4.5 Unit E. Global Unit Finalization 자체 구현 (`Feature`)

목표:

- [ ] `finalize_global_units` 노트북 함수 호출을 제거할 수 있게 한다.

입력:

- [ ] `base_global_units_df`
- [ ] `global_presence_episode_df`

출력:

- [ ] `global_units_df`

작업:

- [ ] `src/trajectory/global_units.py`
- [ ] visible span 계산
- [ ] visible episode count 계산
- [ ] visible camera count 계산
- [ ] base global unit과 merge

완료 조건:

- [ ] `global_units_df` 필수 컬럼 계약을 만족한다.
- [ ] visible span이 episode assignment와 일치한다.

검증:

- [ ] pure unit test
- [ ] golden 비교 test

### 4.6 Unit F. Episode Assignment 자체 구현 (`Feature`)

목표:

- [ ] `assign_episodes_to_global_units` 노트북 함수 호출을 제거할 수 있게 한다.

입력:

- [ ] `episode_units_df`
- [ ] `transition_units_df`
- [ ] `base_global_unit_members_df`

출력:

- [ ] `global_presence_episode_df`

작업:

- [ ] episode와 global unit의 시간 overlap 계산
- [ ] camera/local unit 관계 해소
- [ ] `assignment_mode` 정책 고정

완료 조건:

- [ ] assignment 누락/중복 정책이 명확하다.
- [ ] golden assignment 분포와 비교한다.

검증:

- [ ] overlap pure unit test
- [ ] duplicate assignment test
- [ ] golden 비교 test

### 4.7 Unit G. Global Unit Materialization 자체 구현 (`Feature`)

목표:

- [ ] `materialize_revised_global_units` 노트북 함수 호출을 제거할 수 있게 한다.

입력:

- [ ] `transition_units_df`
- [ ] `selected_global_edges_df`

출력:

- [ ] `base_global_units_df`
- [ ] `base_global_unit_members_df`

작업:

- [ ] selected edge graph 구성
- [ ] connected component 또는 path 기반 global unit 구성
- [ ] camera path 계산
- [ ] global confidence 계산

완료 조건:

- [ ] global unit count가 golden과 일치한다.
- [ ] member ordering이 안정적이다.

검증:

- [ ] graph unit test
- [ ] repeated camera policy test
- [ ] golden 비교 test

### 4.8 Unit H. Candidate Edge Solver 자체 구현 (`Feature`)

목표:

- [ ] `solve_revised_global_edges` 노트북 함수 호출을 제거할 수 있게 한다.

입력:

- [ ] `global_candidate_edges_df`
- [ ] global config

출력:

- [ ] `selected_global_edges_df`

작업:

- [ ] cost threshold 적용
- [ ] bipartite matching 또는 assignment solver 적용
- [ ] same-camera edge 금지 정책 적용

완료 조건:

- [ ] selected edge count와 cost 분포가 golden과 일치한다.
- [ ] deterministic ordering을 보장한다.

검증:

- [ ] small graph unit test
- [ ] threshold test
- [ ] golden 비교 test

### 4.9 Unit I. Candidate Edge Scoring 자체 구현 (`Feature`)

목표:

- [ ] `build_revised_candidate_edges` 노트북 함수 호출을 제거할 수 있게 한다.

입력:

- [ ] `transition_nodes_df`
- [ ] topology links
- [ ] pairwise offsets
- [ ] hour speed prior
- [ ] global config

출력:

- [ ] `global_candidate_edges_df`

작업:

- [ ] gap 계산
- [ ] expected gap 계산
- [ ] shortest path distance 결합
- [ ] implied speed 계산
- [ ] transition score 반영
- [ ] total edge cost 계산

완료 조건:

- [ ] 후보 edge 컬럼 계약을 만족한다.
- [ ] golden 후보 edge count와 cost 주요 분포가 일치한다.

검증:

- [ ] scoring pure unit test
- [ ] impossible speed filter test
- [ ] golden 비교 test

### 4.10 Unit J. Revised Global Input 자체 구현 (`Feature`)

목표:

- [ ] `build_revised_global_inputs` 노트북 함수 호출을 제거할 수 있게 한다.

입력:

- [ ] `prepared_all.pkl`
- [ ] `stitched_df_all.pkl`
- [ ] `presence_episode_df.pkl`
- [ ] scene transit zone table

출력:

- [ ] `episode_units_df`
- [ ] `transition_units_df`
- [ ] `transition_nodes_df`

작업:

- [ ] prepared column normalization
- [ ] episode unit 생성
- [ ] transition support trajectory 필터
- [ ] route points와 route length 계산
- [ ] transition node 생성

완료 조건:

- [ ] output column set이 golden과 일치한다.
- [ ] transition support count가 golden과 일치한다.

검증:

- [ ] column normalization unit test
- [ ] transition node unit test
- [ ] golden 비교 test

### 4.11 Unit K. Topology Static Boundary 정리 (`Feature`)

목표:

- [ ] `build_topology_static_stage` 의존을 자체 구현하거나 외부 모듈 의존으로 격리한다.

선택지:

- [ ] A안: `kt_topology_static_v2`를 배치 코드로 이관
- [ ] B안: topology는 외부 모듈 의존으로 유지하되 notebook 의존은 제거

권장:

- [ ] 1차는 B안으로 진행한다.
- [ ] A안은 geometry fixture와 성능 검증을 확보한 뒤 진행한다.

완료 조건:

- [ ] 06 노트북 파일 import 없이 topology stage를 호출할 수 있다.
- [ ] topology artifact 계약이 명확하다.

검증:

- [ ] topology output column test
- [ ] small topology fixture test

### 4.12 Unit L. Local Stitch / Presence Episode 자체 구현 (`Feature`)

목표:

- [ ] `run_local_scene_stitch_stage` 외부 의존을 줄인다.

주의:

- [ ] 이 단계는 trajectory 품질에 가장 큰 영향을 준다.
- [ ] local stitch 알고리즘 재구현은 충분한 golden fixture 이후에만 진행한다.

작업:

- [ ] camera table normalization
- [ ] state classification
- [ ] local association
- [ ] presence episode recovery
- [ ] QC summary

완료 조건:

- [ ] `prepared_all`, `stitched_df_all`, `presence_episode_df`가 golden과 비교 가능하다.

검증:

- [ ] camera별 fixture test
- [ ] presence episode count test
- [ ] dwell distribution 비교

### 4.13 Unit M. Preprocess / Groundplane Boundary 정리 (`Feature`)

목표:

- [ ] `run_s3_groundplane_stage` 외부 의존을 줄인다.

선택지:

- [ ] A안: S3 download + groundplane projection 자체 구현
- [ ] B안: 기존 `kt_trajectory_pipeline.py`를 외부 모듈 의존으로 유지하고 notebook 의존만 제거

권장:

- [ ] 1차는 B안으로 진행한다.
- [ ] S3/geo transform 자체 구현은 별도 계획으로 분리한다.

완료 조건:

- [ ] 06 노트북 import 없이 preprocess를 실행할 수 있다.
- [ ] raw -> camera table 계약이 문서화된다.

검증:

- [ ] local sample raw fixture test
- [ ] S3 없는 dry-run test

## 5. Stage Wrapper 치환 계획

현재:

```text
src/trajectory/stages.py
-> injected notebook/external functions
```

목표:

```text
src/trajectory/stages.py
-> src/trajectory/revised_input.py
-> src/trajectory/global_units.py
-> src/trajectory/metrics.py
-> src/trajectory/routes.py
```

치환 순서:

1. [ ] `build_route_family_table`
2. [ ] `build_corrected_hourly_metrics`
3. [ ] `finalize_global_units`
4. [ ] `assign_episodes_to_global_units`
5. [ ] `materialize_revised_global_units`
6. [ ] `solve_revised_global_edges`
7. [ ] `build_revised_candidate_edges`
8. [ ] `build_revised_global_inputs`
9. [ ] `build_topology_static_stage`
10. [ ] `run_local_scene_stitch_stage`
11. [ ] `run_s3_groundplane_stage`

## 6. 검증 전략

### 6.1 Unit Test

- [ ] 순수 함수는 작은 DataFrame fixture로 검증한다.
- [ ] 시간 interval 로직은 boundary case를 별도 테스트한다.
- [ ] graph/solver는 tiny graph fixture로 검증한다.

### 6.2 Golden Test

- [ ] notebook artifact와 자체 구현 artifact를 비교한다.
- [ ] row order가 의미 없으면 stable sort key를 정의한다.
- [ ] float 값은 허용 오차를 둔다.
- [ ] row count, column set, null count는 strict 비교한다.

### 6.3 CLI 검증

- [ ] `python -m src.trajectory.main plan`
- [ ] `python -m src.trajectory.main verify-artifacts`
- [ ] 자체 구현 run command 추가 후 smoke test

## 7. 중단 조건

- [ ] golden fixture 없이 association 알고리즘을 재작성해야 하면 중단한다.
- [ ] 같은 테스트 실패가 두 번 반복되면 중단하고 원인/맥락을 보고한다.
- [ ] 노트북 결과와 자체 구현 결과 차이가 1%를 넘고 원인을 설명할 수 없으면 중단한다.
- [ ] DB/dashboard 계약 변경이 필요하면 `PLAN_TRAJECTORY_FROM_06.md`와 dashboard 계획 문서를 먼저 갱신한다.

## 8. 추천 커밋 순서

1. [ ] `docs: plan trajectory reimplementation`
2. [ ] `test: add trajectory golden artifact contract`
3. [ ] `feat: add trajectory artifact loader`
4. [ ] `feat: reimplement trajectory route family`
5. [ ] `feat: reimplement trajectory hourly metrics`
6. [ ] `feat: reimplement global unit finalization`
7. [ ] `feat: reimplement episode assignment`
8. [ ] `feat: reimplement global unit materialization`
9. [ ] `feat: reimplement global edge solver`
10. [ ] `feat: reimplement global edge scoring`
11. [ ] `feat: reimplement revised global input`
12. [ ] `feat: remove notebook global-stage dependency`

## 9. 현재 결론

- [x] 자체 구현은 타당하다.
- [x] 단, 06 노트북은 당분간 reference implementation으로 유지한다.
- [x] 첫 구현 대상은 `route_family`와 `hourly_metric_summary`가 적절하다.
- [x] local stitch/preprocess는 가장 늦게 치환한다.
