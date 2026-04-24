# PLAN: Dashboard Trajectory Integration

## 0. 문서 목적

이 문서는 `ktooh-dashboard-poc`에 trajectory 조회 기능을 추가하기 위한 다음 작업 계획서다.

상위 계획:

- `PLAN.md`: measurement batch 계획
- `PLAN_TRAJECTORY_FROM_06.md`: 06 노트북 기반 trajectory batch 계획
- 이 문서: dashboard가 trajectory 테이블과 view를 읽기 위한 구현 계획

상태 표기:

- `[ ]` 미착수
- `[~]` 진행 중
- `[x]` 완료

## 1. 현재 기준

### 1.1 완료된 선행 작업

- [x] `ktooh-media-batch/src/measurement`와 `src/trajectory` 패키지 경계 분리
- [x] measurement 정책 테스트 고정
- [x] trajectory artifact/stage 계약 고정
- [x] trajectory `plan` CLI 추가
- [x] trajectory `verify-artifacts` CLI 추가
- [x] trajectory stage wrapper 추가
- [x] `pytest`: 27 passed
- [x] `ruff`: All checks passed

### 1.2 다음 작업 저장소

- [ ] 대상 저장소는 `ktooh-dashboard-poc`
- [ ] 기존 measurement API와 repository는 변경 최소화
- [ ] trajectory는 별도 모델, repository, service, route로 추가

### 1.3 범위

1차 범위:

- [ ] SQLAlchemy trajectory 모델 추가
- [ ] 기존 단일 Alembic migration에 trajectory DDL 추가
- [ ] read-only repository 추가
- [ ] service/schema/route 추가
- [ ] provider 등록
- [ ] API 단위 테스트 추가

2차 범위:

- [ ] dashboard 화면 연결
- [ ] 지도 spatial heatmap 렌더링
- [ ] 실제 DB 샘플 데이터로 end-to-end 검증

비범위:

- [ ] 기존 measurement dashboard API를 trajectory API로 대체하지 않는다.
- [ ] 1차에서 노트북 exploratory QC 화면을 옮기지 않는다.
- [ ] 1차에서 모든 intermediate artifact를 dashboard DB에 넣지 않는다.

## 2. 구현 단위

### 2.1 Unit A. Dashboard 스키마 경계 고정 (`Tidy`)

목표:

- [ ] trajectory 테이블과 view 이름을 dashboard 기준으로 확정한다.
- [ ] 기존 `analytics_repository.py`와 충돌하지 않는 읽기 경계를 확정한다.

작업:

- [ ] `ktooh-dashboard-poc` 현재 모델/마이그레이션 구조 확인
- [ ] `trajectory_*` 테이블 이름과 컬럼 목록을 `PLAN_TRAJECTORY_FROM_06.md`와 대조
- [ ] view 이름 확정
  - [ ] `trajectory_hourly_metrics_dashboard_v`
  - [ ] `trajectory_hourly_heatmap_v`
  - [ ] `trajectory_spatial_heatmap_dashboard_v`
- [ ] index 초안 확정

완료 조건:

- [ ] migration 작성 전에 테이블/view/index 계약이 문서와 일치한다.
- [ ] 기존 measurement aggregate 테이블과 이름 충돌이 없다.

검증:

- [ ] 문서 diff review

### 2.2 Unit B. SQLAlchemy 모델 추가 (`Feature`)

목표:

- [ ] dashboard codebase가 trajectory 원본 테이블과 view를 타입 있는 모델로 참조할 수 있다.

작업:

- [x] `app/models/trajectory_global_unit.py`
- [x] `app/models/trajectory_presence_episode.py`
- [x] `app/models/trajectory_global_presence_episode.py`
- [x] `app/models/trajectory_hourly_metric.py`
- [x] `app/models/trajectory_route_family.py`
- [x] `app/models/trajectory_spatial_heatmap_cell.py`
- [x] view read model 추가
  - [x] `trajectory_hourly_metrics_dashboard_view.py`
  - [x] `trajectory_hourly_heatmap_view.py`
  - [x] `trajectory_spatial_heatmap_dashboard_view.py`

완료 조건:

- [x] 모델 import가 성공한다.
- [x] 모든 모델이 `media_id`, `camera_code`, `campaign_id`, `creative_id` 필터 키를 가진다.
- [x] 시간 컬럼은 UTC 저장 전제로 `DateTime` 또는 `Date`/`SmallInteger` 조합을 사용한다.

검증:

- [x] `uv run pytest tests/test_init_contracts.py`
- [x] 신규 모델 import 테스트
- [x] 변경된 모델 파일 대상 `ruff check`

### 2.3 Unit C. Alembic Migration 확장 (`Feature`)

목표:

- [ ] DB에 trajectory 원본 테이블과 dashboard view를 생성할 수 있다.

작업:

- [x] 신규 migration 파일을 만들지 않고 기존 단일 migration 파일 확장
- [x] 테이블 생성
  - [x] `trajectory_presence_episodes`
  - [x] `trajectory_global_units`
  - [x] `trajectory_global_presence_episodes`
  - [x] `trajectory_hourly_metrics`
  - [x] `trajectory_route_families`
  - [x] `trajectory_spatial_heatmap_cells`
- [x] view 생성
  - [x] `trajectory_hourly_metrics_dashboard_v`
  - [x] `trajectory_hourly_heatmap_v`
  - [x] `trajectory_spatial_heatmap_dashboard_v`
- [x] index 생성
  - [x] `(media_id, target_date, hour_start)`
  - [x] `(camera_code, target_date, hour_start)`
  - [x] `(campaign_id, creative_id, hour_start)`
  - [x] spatial 조회용 `cell_id`

완료 조건:

- [x] migration upgrade/downgrade가 대칭이다.
- [x] view는 read-only 조회 전용이다.
- [x] Postgres 우선이며 SQLite 테스트 환경에서 깨지지 않는 전략을 정한다.

검증:

- [x] migration 파일 syntax check
- [x] `uv run alembic upgrade head --sql` offline SQL 생성 확인
- [~] `uv run pytest` 영향 확인: trajectory focused 테스트는 통과, 전체 테스트는 기존 seed/admin/camera repository 실패 존재

### 2.4 Unit D. Query Schema 추가 (`Feature`)

목표:

- [ ] trajectory API 요청/응답 계약을 Pydantic schema로 고정한다.

작업:

- [x] `app/schemas/trajectory_filter.py`
- [x] `app/schemas/trajectory_hourly.py`
- [x] `app/schemas/trajectory_route.py`
- [x] `app/schemas/trajectory_unit.py`
- [x] `app/schemas/trajectory_heatmap.py`

요청 필터:

- [ ] `start_date`
- [ ] `end_date`
- [ ] `timezone`
- [ ] `media_ids`
- [ ] `camera_codes`
- [ ] `campaign_ids`
- [ ] `creative_ids`
- [ ] `metric`
- [ ] spatial 전용 `bbox`, `zoom`, `hour`

완료 조건:

- [x] 잘못된 날짜/metric/bbox 입력을 validation error로 막는다.
- [x] 응답 schema가 프론트에서 바로 사용할 수 있는 이름을 가진다.

검증:

- [x] schema unit test
- [x] 변경된 schema/tests 대상 `ruff check`

### 2.5 Unit E. Repository 추가 (`Feature`)

목표:

- [ ] trajectory 조회 SQL을 `AnalyticsRepository`와 분리한다.

작업:

- [x] `app/repositories/trajectory_repository.py`
- [x] `load_hourly_metrics(query)`
- [x] `load_camera_hour_heatmap(query)`
- [x] `load_spatial_heatmap(query)`
- [x] `load_route_families(query)`
- [x] `load_global_units(query)`
- [x] `load_global_unit_detail(global_unit_id, query)`
- [x] `load_global_presence_episodes(global_unit_id, query)`

완료 조건:

- [x] `media_id + camera + campaign + creative` 필터가 모두 SQL에 반영된다.
- [x] UTC 저장값을 사용자 timezone 기준 날짜 범위로 조회한다.
- [x] spatial 조회는 bbox/zoom/hour를 받는다.

검증:

- [x] repository integration test
- [x] 빈 결과가 빈 list로 반환되는지 테스트
- [x] 필터 조합별 API 테스트

### 2.6 Unit F. Service 추가 (`Feature`)

목표:

- [ ] repository 결과를 API 응답 형태로 조립한다.

작업:

- [x] `app/services/analytics/trajectory_service.py`
- [x] `get_hourly_metrics(...)`
- [x] `get_camera_hour_heatmap(...)`
- [x] `get_spatial_heatmap(...)`
- [x] `get_route_families(...)`
- [x] `get_global_units(...)`
- [x] `get_global_unit_detail(...)`

완료 조건:

- [x] metric 선택값에 따라 heatmap value가 결정된다.
- [x] timezone 변환 책임이 service/repository 경계에서 일관된다.
- [x] repository 예외를 API 친화적 예외로 변환한다.

검증:

- [x] service/API integration test
- [x] metric 선택 테스트
- [x] global unit detail 조립 테스트

### 2.7 Unit G. API Route 추가 (`Feature`)

목표:

- [ ] `/api/v1/analysis/trajectory/*` read-only endpoint를 추가한다.

작업:

- [x] `app/routes/analytics/trajectory.py`
- [x] `GET /api/v1/analysis/trajectory/hourly`
- [x] `GET /api/v1/analysis/trajectory/camera-heatmap`
- [x] `GET /api/v1/analysis/trajectory/spatial-heatmap`
- [x] `GET /api/v1/analysis/trajectory/routes`
- [x] `GET /api/v1/analysis/trajectory/units`
- [x] `GET /api/v1/analysis/trajectory/units/{global_unit_id}`
- [x] route include 연결

완료 조건:

- [x] 기존 `/analysis/watch-*`, `/analysis/vehicle`, `/analysis/population`과 충돌하지 않는다.
- [x] 모든 endpoint는 read-only다.

검증:

- [x] route test
- [x] invalid query test
- [x] empty result response test

### 2.8 Unit H. Provider 등록 (`Feature`)

목표:

- [ ] Dishka DI에서 trajectory repository/service를 주입할 수 있다.

작업:

- [x] `app/providers/repository.py`에 `TrajectoryRepository` 등록
- [x] `app/providers/service.py`에 `TrajectoryService` 등록
- [x] route 의존성 연결

완료 조건:

- [x] app startup/import가 성공한다.
- [x] endpoint 호출 시 DI resolution error가 없다.

검증:

- [x] DI integration test
- [x] route smoke test

### 2.9 Unit I. Batch-Dashboard 계약 동기화 (`Tidy`)

목표:

- [ ] batch 문서와 dashboard 구현 계약이 갈라지지 않도록 맞춘다.

작업:

- [x] `PLAN_TRAJECTORY_FROM_06.md`의 DB/API 체크박스 업데이트
- [x] 이 문서의 완료 항목 업데이트
- [ ] 필요 시 `README.md`에 trajectory dashboard API 링크 추가

완료 조건:

- [x] 구현된 endpoint/table/view가 문서와 일치한다.

검증:

- [x] 문서 diff review

## 3. 추천 커밋 순서

1. [ ] `docs: split dashboard trajectory integration plan`
2. [x] `feat: add trajectory dashboard models`
3. [x] `feat: extend single migration with trajectory dashboard ddl`
4. [x] `feat: add trajectory schemas`
5. [x] `feat: add trajectory repository`
6. [x] `feat: add trajectory service`
7. [x] `feat: add trajectory api routes`
8. [x] `feat: register trajectory dependencies`
9. [x] `docs: update trajectory dashboard integration status`

## 4. 중단 조건

- [ ] 같은 테스트 실패가 두 번 반복되면 중단하고 원인/맥락을 보고한다.
- [ ] 기존 measurement API 변경이 필요해지면 중단하고 범위 변경 확인을 받는다.
- [ ] dashboard 스키마가 batch artifact 계약과 맞지 않으면 migration 작성 전에 중단한다.
- [ ] SQLite 테스트와 Postgres production DDL이 충돌하면 migration 전략을 먼저 확정한다.

## 5. 완료 기준

- [~] `ktooh-dashboard-poc` 테스트 통과: trajectory focused 테스트 통과, 전체 테스트는 기존 seed/admin/camera repository 실패 존재
- [~] `ruff` 통과: 변경 범위 통과, 전체 ruff는 기존 dashboard lint 실패 존재
- [x] trajectory API route smoke test 통과
- [x] migration 적용 가능
- [x] `media_id + camera + campaign + creative` 필터 동작
- [x] 시간대 패턴, camera heatmap, spatial heatmap, route family, global unit detail 조회 가능
