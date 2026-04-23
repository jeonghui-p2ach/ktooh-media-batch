# PLAN

## 0. 문서 목적

이 문서는 `ktooh-media-batch`를 실제 구현 가능한 수준으로 쪼갠 실행 계획서다.

목표는 4가지다.

1. 입력 원천과 dashboard 적재 계약을 먼저 고정한다.
2. 구현 순서를 `Tidy -> Feature`로 고정한다.
3. 각 단계의 파일 책임과 완료 조건을 명시한다.
4. 구현 후 무엇으로 검증할지 테스트와 운영 검증 기준을 고정한다.

상태 표기:

- `[ ]` 미착수
- `[~]` 진행 중
- `[x]` 완료

---

## 1. 목표와 비목표

### 1.1 목표

- [x] `media_id`, `target_date`를 받아 `project-pooh-kt` 계열 raw jsonl을 수집할 수 있어야 한다.
- [x] `demographic` source는 `audience_event_fact`와 aggregate 테이블에서 바로 조회 가능한 fact row를 만들어야 한다.
- [x] `floating` source는 1차에서 차량 `traffic` 적재를 끝내야 한다.
- [x] pedestrian audience pattern은 선택 범위로 두되, 필요하면 2차로 이월할 수 있어야 한다.
- [x] `ktooh-dashboard-poc`의 `media`, `cameras`, `media_campaign_map`, `campaign_schedules`, `creatives`를 사용해 귀속을 해소해야 한다.
- [x] `source_batch_id + raw_ref` 기준으로 안전하게 재생성/재처리가 가능해야 한다.

### 1.2 비목표

- [x] 외부 유동인구 batch를 이 프로젝트로 대체하지 않는다.
- [x] trajectory 전체 파이프라인을 이 프로젝트에 섞지 않는다.
- [x] raw payload만으로 creative가 항상 확정된다고 가정하지 않는다.
- [x] 배치 실행 이력 테이블(`batch_runs`, `batch_run_files`, `batch_quarantine`)을 운영 관리 목적으로 만들지 않는다.
- [x] 1차 릴리스에서 운영 UI까지 함께 수정하지 않는다.

### 1.3 완료 정의

- [x] `plan`, `run-step`, `run-batch` CLI가 동작한다.
- [x] 샘플 demographic/floating jsonl을 실제 parser로 읽을 수 있다.
- [x] demographic raw에서 `audience_event_fact` 적재 후 aggregate ETL까지 완료된다.
- [x] floating raw에서 `traffic` 적재가 완료된다.
- [x] 같은 원천 파일을 다시 처리할 때 삭제 후 재생성 또는 멱등 upsert가 예측 가능하게 동작한다.

---

## 2. 요구사항 해석

### 2.1 입력 원천

- [x] `project-pooh-kt/docs/demographic.jsonl`
- [x] `project-pooh-kt/docs/floating.jsonl`

### 2.2 처리 시작점

- [x] 배치 입력 시작점은 `media_id`
- [x] `media_id -> cameras`는 `ktooh-dashboard-poc.cameras`에서 조회
- [x] 각 camera의 `source_type`으로 `demographic`, `floating` 경로 분기

### 2.3 적재 대상

- [x] 인구/패턴 분석: `audience_event_fact`
- [x] 차량 분석: `traffic`
- [x] 조회 성능용 집계: `agg_audience_minute`, `agg_audience_hourly`, `agg_audience_daily`
- [x] 배치 운영은 별도 이력 테이블 없이 재생성 중심으로 단순화

### 2.4 용어 고정

- [x] camera source type의 `floating`은 raw movement source를 뜻한다.
- [x] dashboard metric `floating_population`은 외부 유동인구 지표를 뜻한다.
- [ ] `노출`을 `attentive_population`으로 볼지 최종 확정이 필요하다.

### 2.5 시간 (UTC) 고정

- [x] 파이프라인·파서·정규화·적재·검증, 그리고 DB에 넣는 모든 시각은 UTC를 쓴다.
- [x] `target_date`, `occurred_date`, aggregate 적재 기준일은 UTC 캘린더 일 기준이다.
- [x] 원천 시각에 offset이 없으면 UTC로 해석하고, offset이 있으면 UTC로 정규화한 뒤 사용한다.
- [x] 캠페인 오버랩 판단은 UTC로 정규화된 시각끼리만 비교한다.
- [x] `PipelineBuilder.timezone_name`은 `UTC`로 통일한다.

### 2.6 저장/집계/조회 시간대 계약

- [x] 저장: `occurred_at`, `ts` 등은 UTC로 저장한다.
- [x] 배치 집계: `occurred_date`, aggregate 적재 기준일은 UTC 캘린더 일을 사용한다.
- [x] 화면 조회: dashboard 조회는 사용자 설정 시간대를 사용한다. 기본 시간대는 `Asia/Seoul`이다.
- [x] 조회 변환 책임은 dashboard 조회 계층과 UI에 있다.
- [x] batch는 UTC 저장과 UTC 기준 집계까지만 책임지고, 사용자 시간대별 표시 변환은 하지 않는다.
- [x] `ktooh-dashboard-poc` aggregate/query 경로가 이 계약과 모순 없이 동작하는지 함께 점검한다.

---

## 3. 선결 결정

### 3.1 `노출` 매핑

- [ ] `노출 = attentive_population`
- [ ] 또는 `노출 = visible_population` + `가시권` 별도 재정의

권장:

- [ ] 1차는 `가시권 = visible_population`, `노출 = attentive_population`, `시청 = watched_population`

### 3.2 creative 미확정 정책

- [x] campaign 단일 매칭이면 `creative_id = NULL`로 적재 허용
- [x] campaign 복수 매칭이면 reject

권장:

- [ ] campaign 단일이면 적재, creative는 단일 해소일 때만 채움

### 3.3 floating pedestrian pattern 범위

- [x] 1차 릴리스에 포함 여부를 설정으로 제어한다.
- [x] 1차는 traffic 우선, pedestrian pattern은 선택적으로 적재한다.

권장:

- [ ] 1차는 traffic 적재를 먼저 끝내고, pedestrian pattern은 `dwell_time_seconds`만 보수적으로 포함

### 3.4 fact 추적 컬럼 추가

- [x] `audience_event_fact`에 `camera_code`, `raw_ref`, `source_schema` 추가
- [x] 별도 운영 이력 테이블은 만들지 않음

권장:

- [x] 추적 컬럼 추가 포함

### 3.5 멱등 키 정책

- [x] 멱등 기준은 원천 안정 키를 사용한다.
- [x] `source_batch_id`는 동일 원천 파일/배치 재처리 시 유지되는 안정 식별자여야 한다.
- [x] 별도 `run_id`는 저장하지 않는다.

권장:

- [x] audience fact 멱등 키는 `source_batch_id + raw_ref + segment_type + segment_value + threshold_sec`
- [x] traffic 멱등 키는 `source_batch_id + raw_ref + vehicle_type + direction`

---

## 4. 권장 아키텍처

### 4.1 상위 실행 흐름

CLI: `plan`, `run-step <step-name>`, `run-batch`

```text
plan
-> load-media-cameras
-> collect-s3-objects
-> parse-jsonl
-> normalize-demographic-events
-> normalize-floating-events
-> resolve-attribution
-> load-audience-facts
-> load-traffic
-> trigger-aggregates
-> verify
```

### 4.2 패키지 구조

```text
src/
├── main.py
├── config.py
├── logging_config.py
├── models.py
├── pipeline.py
├── dashboard_registry.py
├── collector.py
├── parser_demographic.py
├── parser_floating.py
├── normalization_demographic.py
├── normalization_floating.py
├── attribution.py
├── loader_audience.py
├── loader_traffic.py
└── verify.py
```

### 4.3 Measurement / Trajectory 경계

- [x] 현재 `ktooh-media-batch/src`는 measurement batch 전용 패키지다.
- [x] 이 문서의 구현 범위는 `demographic.jsonl`, `floating.jsonl`에서 `audience_event_fact`, `traffic`, aggregate 적재까지다.
- [x] `presence_episode`, `global_unit`, `route_family`, spatial heatmap은 이 문서 범위가 아니다.
- [x] trajectory 관련 계획과 적재 계약은 `PLAN_TRAJECTORY_FROM_06.md`에서 별도로 관리한다.

권장 분리 수준:

- [x] 저장소를 유지하더라도 패키지는 최소 `measurement`와 `trajectory`로 나눈다.
- [x] 더 안전한 선택은 `ktooh-media-batch`와 `ktooh-trajectory-batch`를 별도 프로젝트로 분리하는 것이다.

같은 저장소를 유지할 때 권장 구조:

```text
src/
├── measurement/
│   ├── main.py
│   ├── config.py
│   ├── collector.py
│   ├── parser_demographic.py
│   ├── parser_floating.py
│   ├── normalization_demographic.py
│   ├── normalization_floating.py
│   ├── attribution.py
│   ├── loader_audience.py
│   ├── loader_traffic.py
│   └── verify.py
└── trajectory/
    ├── preprocess.py
    ├── local_stage.py
    ├── global_stage.py
    ├── metrics_stage.py
    ├── routes_stage.py
    ├── storage.py
    └── verify.py
```

분리 원칙:

- [x] measurement batch는 raw event 해석과 KPI/aggregate 적재만 책임진다.
- [x] trajectory batch는 local/global association, route family, heatmap cell 적재만 책임진다.
- [x] 공통점은 raw 수집 규약, UTC 저장 규약, dashboard lookup 정도로 제한한다.

### 4.4 책임 분리

- [x] parser: raw line -> typed DTO
- [x] normalization: typed DTO -> draft row
- [x] attribution: media/campaign/creative 귀속 해소
- [x] loader: DB insert/upsert 또는 삭제 후 재생성
- [x] dashboard_registry: dashboard DB read 경계
- [x] verify: 적재 후 수치 검증

---

## 5. 데이터 계약

**시간 필드(§2.5, §2.6)**: `occurred_at`, `occurred_date`, `occurred_hour`, `ts`, raw 시각 필드는 모두 UTC 기준을 따른다. 화면 조회 시에는 저장된 UTC 시각을 사용자 설정 시간대(기본 KST)로 변환해 사용한다.

### 5.1 내부 모델

- [x] `BatchRequest`
- [x] `DashboardBinding`
- [x] `CollectedObject`
- [x] `DemographicRawRecord`
- [x] `FloatingRawRecord`
- [x] `AudienceFactDraft`
- [x] `TrafficDraft`
- [x] `RejectedRow`
- [x] `LoadSummary`

### 5.2 `DemographicRawRecord`

필수 필드:

- [x] `device_id`
- [x] `grid_id`
- [x] `track_id`
- [x] `timestamp`
- [x] `last_seen`
- [x] `stay_duration`
- [x] `gaze_duration`
- [x] `gender`
- [x] `age`
- [x] `par_gender`
- [x] `par_age`

선택 필드:

- [ ] `creative_name`
- [ ] `gaze_likelihood`
- [ ] `face_recognized`
- [ ] `sample_n`
- [ ] `sample_gazing_n`

### 5.3 `FloatingRawRecord`

필수 필드:

- [x] `id`
- [x] `type`
- [x] `start_time`
- [x] `end_time`
- [x] `dwell`
- [x] `move_dist`
- [x] `status`
- [x] `bboxes`
- [x] `location`

### 5.4 `AudienceFactDraft`

- [x] `occurred_at`
- [x] `occurred_date`
- [x] `occurred_hour`
- [x] `media_id`
- [x] `campaign_id` (`NULL` 허용)
- [x] `creative_id` (`NULL` 허용)
- [x] `segment_type`
- [x] `segment_value`
- [x] `threshold_sec`
- [x] `floating_population`
- [x] `visible_population`
- [x] `attentive_population`
- [x] `watched_population`
- [x] `watch_time_seconds`
- [x] `dwell_time_seconds`
- [x] `play_count`
- [x] `allocation_basis`
- [x] `source_type`
- [x] `source_batch_id`
- [x] `camera_code`
- [x] `raw_ref`
- [x] `source_schema`

### 5.5 `TrafficDraft`

- [x] `media_id`
- [x] `campaign_id` (`NULL` 허용)
- [x] `ts`
- [x] `vehicle_type`
- [x] `direction`
- [x] `count`
- [x] `camera_code`
- [x] `raw_ref`
- [x] `source_batch_id`

---

## 6. 원천별 적재 규칙

### 6.1 demographic -> audience facts

생성 규칙:

- [x] total 세그먼트 row 생성
- [x] gender 세그먼트 row 생성
- [x] age 세그먼트 row 생성
- [x] watch threshold row는 `1`, `3`, `7`초 기준으로 생성

metric 규칙:

- [x] `visible_population = 1`
- [x] `attentive_population = 노출 정책에 따른 0/1`
- [x] `watched_population = threshold 통과 시 1`
- [x] `watch_time_seconds = gaze_duration`
- [x] `dwell_time_seconds = stay_duration`
- [x] `play_count = 0`
- [x] `allocation_basis = camera_demographic`

### 6.2 floating -> traffic

대상 타입:

- [x] `Car`
- [x] `Bus`
- [x] `Truck`
- [x] `Motorcycle`

적재 규칙:

- [x] `ts = start_time` (UTC)
- [x] `count = 1`
- [x] `campaign_id = NULL`
- [ ] `direction`은 canonical 값 집합으로 고정한다.

### 6.3 floating -> audience pattern

- [x] 대상 타입은 `Pedestrian`
- [x] 1차에서 제외 가능
- [x] 포함 시 `dwell_time_seconds = dwell` 중심으로 최소 적재
- [x] campaign/creative 귀속은 1차에서 제외 또는 `NULL`

---

## 7. DB 변경안

### 7.1 유지할 테이블

- [x] `audience_event_fact`
- [x] `agg_audience_minute`
- [x] `agg_audience_hourly`
- [x] `agg_audience_daily`
- [x] `traffic`

### 7.2 `audience_event_fact` 변경

- [x] `camera_code VARCHAR(50)` 추가
- [x] `raw_ref VARCHAR(255)` 추가
- [x] `source_schema VARCHAR(64)` 추가

인덱스 검토:

- [x] `ix_aef_camera_occurred`
- [x] `ix_aef_raw_ref`
- [x] unique key 후보: `(source_batch_id, raw_ref, segment_type, segment_value, threshold_sec)`
- [x] `source_batch_id` 생성 규칙을 문서와 코드에 같은 방식으로 고정한다.

### 7.3 `traffic` 변경

- [x] `camera_code VARCHAR(50)` 추가
- [x] `source_batch_id VARCHAR(64)` 추가
- [x] `raw_ref VARCHAR(255)` 추가

인덱스 검토:

- [x] `ix_traffic_camera_ts`
- [x] `ix_traffic_source_batch`
- [x] unique key 후보: `(source_batch_id, raw_ref, vehicle_type, direction)`

### 7.4 별도 운영 이력 테이블 미도입

- [x] `batch_runs`, `batch_run_files`, `batch_quarantine`는 만들지 않는다.
- [x] 운영 중 재처리가 필요하면 대상 일자/매체 데이터를 삭제 후 다시 적재한다.
- [x] 실패/제외 row는 영구 저장 테이블이 아니라 로그와 테스트 결과로 확인한다.
- [x] loader는 삭제 후 재생성 또는 upsert 중 하나로 동작 방식을 고정한다.

---

## 8. 구현 단계

### 8.1 Phase 0. 구조와 계약 정리 (`Tidy`)

대상 파일:

- [x] `src/models.py`
- [x] 신규 `dashboard_registry.py`
- [x] 신규 `collector.py`
- [x] 신규 parser/normalization/loader 파일
- [x] `README.md`

작업:

- [x] 현재 스캐폴드 모델을 실제 raw schema 기준으로 재정의
- [x] env var 계약을 `MEDIA_BATCH_` 기준으로 고정
- [x] `run-batch` 명령 추가 계획 확정
- [x] `PipelineBuilder.timezone_name`을 `UTC`로 통일

### 8.2 Phase 1. dashboard registry 조회 (`Feature`)

- [x] `media_id`로 active cameras 조회
- [x] `camera_code`, `source_type`, `media_id` binding 생성
- [x] `media_campaign_map`, `campaign_schedules`, `creatives` 로딩 함수 추가

### 8.3 Phase 2. source object 수집 (`Feature`)

- [x] camera/source_type별 S3 prefix 계산
- [x] object listing
- [x] local raw root fallback
- [x] object metadata manifest 생성
- [x] 페이지네이션 누락 없이 완전 수집

### 8.4 Phase 3. parser 구현 (`Feature`)

- [x] line-by-line jsonl 스트리밍 파싱
- [x] typed DTO 변환
- [x] invalid timestamp/numeric/enum reject taxonomy 구현
- [x] `raw_ref = {s3_key}:{line_number}` 규칙 고정

완료 조건:

- [x] 샘플 jsonl을 실제 parser로 읽어 DTO를 만든다.
- [x] 잘못된 row는 reject 결과로 분리되고 로드 대상에서 제외된다.

### 8.5 Phase 4. demographic normalization (`Feature`)

- [x] `DemographicRawRecord -> AudienceFactDraft[]`
- [x] total/gender/age 세그먼트 분해
- [x] threshold row 생성
- [x] attentive/watched 산식 적용

### 8.6 Phase 5. floating normalization (`Feature`)

- [x] vehicle type 분류
- [x] direction/status 정규화
- [x] `FloatingRawRecord -> TrafficDraft[]`
- [x] pedestrian pattern row 정책 적용

### 8.7 Phase 6. attribution (`Feature`)

- [x] media/campaign schedule overlap 매칭
- [x] creative_name 해소
- [x] 복수 campaign 매칭 시 reject 정책 반영

### 8.8 Phase 7. loader 구현 (`Feature`)

- [x] audience fact idempotent insert/upsert
- [x] traffic idempotent insert/upsert
- [x] `source_batch_id` 생성 규칙 구현
- [x] 삭제 후 재생성 모드와 upsert 모드 중 하나를 고정

완료 조건:

- [x] 같은 원천 파일을 다시 처리해도 중복 적재되지 않는다.
- [x] 삭제 후 재생성 또는 upsert 재실행 모두 예측 가능하게 동작한다.

### 8.9 Phase 8. aggregate / verify (`Feature`)

- [x] aggregate ETL 호출 방식 확정
- [x] raw count vs loaded count 검증
- [x] aggregate row 생성 여부 검증
- [x] UTC 저장 후 dashboard 조회 시 사용자 시간대(기본 KST) 기준으로 기대한 날짜/시간에 노출되는지 검증

### 8.10 Phase 9. CLI 운영화 (`Feature`)

- [x] `run-batch` 명령 추가
- [x] `--dry-run`
- [x] `--source-type demographic|floating|all`
- [x] `--camera-code`

---

## 9. 테스트 전략

### 9.1 단위 테스트

- [x] parser demographic
- [x] parser floating
- [x] demographic normalization
- [x] floating normalization
- [ ] attribution
- [x] step/status validation

### 9.2 통합 테스트

- [x] media binding -> object listing
- [x] demographic file -> audience facts -> aggregate ETL
- [x] floating file -> traffic
- [x] dry-run / rerun idempotency
- [x] UTC 저장 후 KST 조회 경계 테스트

### 9.3 샘플 기반 golden 테스트

- [x] `project-pooh-kt/docs/demographic.jsonl`
- [x] `project-pooh-kt/docs/floating.jsonl`
- [x] accepted row 수
- [x] rejected row 수
- [x] generated fact 수
- [x] generated traffic 수
- [x] UTC 자정 경계 row의 조회 날짜/시간

---

## 10. 검증 명령

```bash
cd ktooh-media-batch
uv sync
uv run pytest
uv run ruff check
uv run mypy
uv run python -m src.main plan --target-date 2026-04-23 --media-id 101
uv run python -m src.main run-batch --target-date 2026-04-23 --media-id 101 --dry-run
```

운영 검증:

- [x] batch 완료 후 `audience_event_fact` row 존재
- [x] batch 완료 후 `traffic` row 존재
- [x] aggregate row 생성 확인
- [x] 사용자 시간대가 KST일 때 UTC 저장 데이터가 기대한 로컬 날짜/시간으로 조회되는지 확인

---

## 11. 리스크와 대응

### 11.1 리스크

- [ ] creative를 raw 원천만으로 해소 못 할 수 있다.
- [ ] floating pedestrian event의 watch 정의가 약하다.
- [ ] `노출` 용어가 팀 합의 없이 구현되면 지표 해석이 달라진다.
- [ ] 로컬 시각·원천 offset과 UTC를 혼동하면 `target_date` 경계·캠페인 겹침·집계가 틀어질 수 있다.
- [ ] S3 object listing 페이지네이션 누락, 부분 실패 후 중간만 커밋, 대용량 jsonl 전부 메모리 로드는 누락/OOM을 유발할 수 있다.
- [ ] `source_batch_id` 규칙이 흔들리면 재실행마다 중복 row가 쌓일 수 있다.

### 11.2 대응

- [ ] creative는 단일 해소일 때만 채운다.
- [ ] pedestrian pattern은 1차에서 dwell 중심으로 제한한다.
- [ ] UTC 계약을 parser·loader·fixture·검증 기대값에 그대로 반영한다.
- [ ] S3·파일 읽기는 스트리밍/iterator와 완전 listing으로 설계한다.
- [ ] 멱등 키는 `source_batch_id` 중심으로 고정한다.

---

## 12. 권장 실행 순서

1. Phase 0: 구조와 계약 정리
2. Phase 1: dashboard registry 조회
3. Phase 2: source object 수집
4. Phase 3: parser 구현
5. Phase 4: demographic normalization
6. Phase 5: floating normalization
7. Phase 6: attribution
8. Phase 7: loader 구현
9. Phase 8: aggregate / verify
10. Phase 9: CLI 운영화

절대 금지 순서:

- [ ] parser 계약 없이 loader부터 구현하지 않는다.
- [ ] demographic fact row 정의 없이 aggregate ETL을 먼저 붙이지 않는다.
- [ ] `source_batch_id` 규칙 없이 idempotent loader를 확정하지 않는다.
