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
- [ ] Alembic migration 추가
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

- [ ] `app/models/trajectory_global_unit.py`
- [ ] `app/models/trajectory_global_presence_episode.py`
- [ ] `app/models/trajectory_hourly_metric.py`
- [ ] `app/models/trajectory_route_family.py`
- [ ] `app/models/trajectory_spatial_heatmap_cell.py`
- [ ] view read model 추가
  - [ ] `trajectory_hourly_metrics_dashboard_view.py`
  - [ ] `trajectory_hourly_heatmap_view.py`
  - [ ] `trajectory_spatial_heatmap_dashboard_view.py`

완료 조건:

- [ ] 모델 import가 성공한다.
- [ ] 모든 모델이 `media_id`, `camera_code`, `campaign_id`, `creative_id` 필터 키를 가진다.
- [ ] 시간 컬럼은 UTC 저장 전제로 `DateTime` 또는 `Date`/`SmallInteger` 조합을 사용한다.

검증:

- [ ] `uv run pytest tests/test_init_contracts.py`
- [ ] 신규 모델 import 테스트
- [ ] `uv run ruff check app/models`

### 2.3 Unit C. Alembic Migration 추가 (`Feature`)

목표:

- [ ] DB에 trajectory 원본 테이블과 dashboard view를 생성할 수 있다.

작업:

- [ ] 신규 migration 파일 생성
- [ ] 테이블 생성
  - [ ] `trajectory_global_units`
  - [ ] `trajectory_global_presence_episodes`
  - [ ] `trajectory_hourly_metrics`
  - [ ] `trajectory_route_families`
  - [ ] `trajectory_spatial_heatmap_cells`
- [ ] view 생성
  - [ ] `trajectory_hourly_metrics_dashboard_v`
  - [ ] `trajectory_hourly_heatmap_v`
  - [ ] `trajectory_spatial_heatmap_dashboard_v`
- [ ] index 생성
  - [ ] `(media_id, target_date, hour_start)`
  - [ ] `(camera_code, target_date, hour_start)`
  - [ ] `(campaign_id, creative_id, hour_start)`
  - [ ] spatial 조회용 `cell_id`

완료 조건:

- [ ] migration upgrade/downgrade가 대칭이다.
- [ ] view는 read-only 조회 전용이다.
- [ ] Postgres 우선이며 SQLite 테스트 환경에서 깨지지 않는 전략을 정한다.

검증:

- [ ] migration 파일 syntax check
- [ ] 가능하면 test DB에서 upgrade 실행
- [ ] `uv run pytest` 영향 확인

### 2.4 Unit D. Query Schema 추가 (`Feature`)

목표:

- [ ] trajectory API 요청/응답 계약을 Pydantic schema로 고정한다.

작업:

- [ ] `app/schemas/trajectory_filter.py`
- [ ] `app/schemas/trajectory_hourly.py`
- [ ] `app/schemas/trajectory_route.py`
- [ ] `app/schemas/trajectory_unit.py`
- [ ] `app/schemas/trajectory_heatmap.py`

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

- [ ] 잘못된 날짜/metric/bbox 입력을 validation error로 막는다.
- [ ] 응답 schema가 프론트에서 바로 사용할 수 있는 이름을 가진다.

검증:

- [ ] schema unit test
- [ ] `uv run ruff check app/schemas tests`

### 2.5 Unit E. Repository 추가 (`Feature`)

목표:

- [ ] trajectory 조회 SQL을 `AnalyticsRepository`와 분리한다.

작업:

- [ ] `app/repositories/trajectory_repository.py`
- [ ] `load_hourly_metrics(query)`
- [ ] `load_camera_hour_heatmap(query)`
- [ ] `load_spatial_heatmap(query)`
- [ ] `load_route_families(query)`
- [ ] `load_global_units(query)`
- [ ] `load_global_unit_detail(global_unit_id, query)`
- [ ] `load_global_presence_episodes(global_unit_id, query)`

완료 조건:

- [ ] `media_id + camera + campaign + creative` 필터가 모두 SQL에 반영된다.
- [ ] UTC 저장값을 사용자 timezone 기준 날짜 범위로 조회한다.
- [ ] spatial 조회는 bbox/zoom/hour를 받는다.

검증:

- [ ] repository unit/integration test
- [ ] 빈 결과가 빈 list로 반환되는지 테스트
- [ ] 필터 조합별 SQL 조건 테스트

### 2.6 Unit F. Service 추가 (`Feature`)

목표:

- [ ] repository 결과를 API 응답 형태로 조립한다.

작업:

- [ ] `app/services/analytics/trajectory_service.py`
- [ ] `get_hourly_metrics(...)`
- [ ] `get_camera_hour_heatmap(...)`
- [ ] `get_spatial_heatmap(...)`
- [ ] `get_route_families(...)`
- [ ] `get_global_units(...)`
- [ ] `get_global_unit_detail(...)`

완료 조건:

- [ ] metric 선택값에 따라 heatmap value가 결정된다.
- [ ] timezone 변환 책임이 service/repository 경계에서 일관된다.
- [ ] repository 예외를 API 친화적 예외로 변환한다.

검증:

- [ ] service unit test
- [ ] metric 선택 테스트
- [ ] global unit detail 조립 테스트

### 2.7 Unit G. API Route 추가 (`Feature`)

목표:

- [ ] `/analysis/trajectory/*` read-only endpoint를 추가한다.

작업:

- [ ] `app/routes/analytics/trajectory.py`
- [ ] `GET /analysis/trajectory/hourly`
- [ ] `GET /analysis/trajectory/camera-heatmap`
- [ ] `GET /analysis/trajectory/spatial-heatmap`
- [ ] `GET /analysis/trajectory/routes`
- [ ] `GET /analysis/trajectory/units`
- [ ] `GET /analysis/trajectory/units/{global_unit_id}`
- [ ] route include 연결

완료 조건:

- [ ] 기존 `/analysis/watch-*`, `/analysis/vehicle`, `/analysis/population`과 충돌하지 않는다.
- [ ] 모든 endpoint는 read-only다.

검증:

- [ ] route test
- [ ] invalid query test
- [ ] empty result response test

### 2.8 Unit H. Provider 등록 (`Tidy/Feature 분리`)

목표:

- [ ] Dishka DI에서 trajectory repository/service를 주입할 수 있다.

작업:

- [ ] `app/providers/repository.py`에 `TrajectoryRepository` 등록
- [ ] `app/providers/service.py`에 `TrajectoryService` 등록
- [ ] route 의존성 연결

완료 조건:

- [ ] app startup/import가 성공한다.
- [ ] endpoint 호출 시 DI resolution error가 없다.

검증:

- [ ] DI integration test
- [ ] route smoke test

### 2.9 Unit I. Batch-Dashboard 계약 동기화 (`Tidy`)

목표:

- [ ] batch 문서와 dashboard 구현 계약이 갈라지지 않도록 맞춘다.

작업:

- [ ] `PLAN_TRAJECTORY_FROM_06.md`의 DB/API 체크박스 업데이트
- [ ] 이 문서의 완료 항목 업데이트
- [ ] 필요 시 `README.md`에 trajectory dashboard API 링크 추가

완료 조건:

- [ ] 구현된 endpoint/table/view가 문서와 일치한다.

검증:

- [ ] 문서 diff review

## 3. 추천 커밋 순서

1. [ ] `docs: split dashboard trajectory integration plan`
2. [ ] `feat: add trajectory dashboard models`
3. [ ] `feat: add trajectory dashboard migration`
4. [ ] `feat: add trajectory schemas`
5. [ ] `feat: add trajectory repository`
6. [ ] `feat: add trajectory service`
7. [ ] `feat: add trajectory api routes`
8. [ ] `feat: register trajectory dependencies`
9. [ ] `docs: update trajectory dashboard integration status`

## 4. 중단 조건

- [ ] 같은 테스트 실패가 두 번 반복되면 중단하고 원인/맥락을 보고한다.
- [ ] 기존 measurement API 변경이 필요해지면 중단하고 범위 변경 확인을 받는다.
- [ ] dashboard 스키마가 batch artifact 계약과 맞지 않으면 migration 작성 전에 중단한다.
- [ ] SQLite 테스트와 Postgres production DDL이 충돌하면 migration 전략을 먼저 확정한다.

## 5. 완료 기준

- [ ] `ktooh-dashboard-poc` 테스트 통과
- [ ] `ruff` 통과
- [ ] trajectory API route smoke test 통과
- [ ] migration 적용 가능
- [ ] `media_id + camera + campaign + creative` 필터 동작
- [ ] 시간대 패턴, camera heatmap, spatial heatmap, route family, global unit detail 조회 가능
