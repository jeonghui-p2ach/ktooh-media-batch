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

- [ ] `media_id`, `target_date`를 받아 `project-pooh-kt` 계열 raw jsonl을 수집할 수 있어야 한다.
- [ ] `demographic` source는 `audience_event_fact`와 aggregate 테이블에서 바로 조회 가능한 fact row를 만들어야 한다.
- [ ] `floating` source는 1차에서 차량 `traffic` 적재를 끝내야 한다.
- [ ] pedestrian audience pattern은 선택 범위로 두되, 필요하면 2차로 이월할 수 있어야 한다.
- [ ] `ktooh-dashboard-poc`의 `media`, `cameras`, `media_campaign_map`, `campaign_schedules`, `creatives`를 사용해 귀속을 해소해야 한다.
- [ ] `source_batch_id + raw_ref` 기준으로 안전하게 재생성/재처리가 가능해야 한다.

### 1.2 비목표

- [ ] 외부 유동인구 batch를 이 프로젝트로 대체하지 않는다.
- [ ] trajectory 전체 파이프라인을 이 프로젝트에 섞지 않는다.
- [ ] raw payload만으로 creative가 항상 확정된다고 가정하지 않는다.
- [ ] 배치 실행 이력 테이블(`batch_runs`, `batch_run_files`, `batch_quarantine`)을 운영 관리 목적으로 만들지 않는다.
- [ ] 1차 릴리스에서 운영 UI까지 함께 수정하지 않는다.

### 1.3 완료 정의

- [ ] `plan`, `run-step`, `run-batch` CLI가 동작한다.
- [ ] 샘플 demographic/floating jsonl을 실제 parser로 읽을 수 있다.
- [ ] demographic raw에서 `audience_event_fact` 적재 후 aggregate ETL까지 완료된다.
- [ ] floating raw에서 `traffic` 적재가 완료된다.
- [ ] 같은 원천 파일을 다시 처리할 때 삭제 후 재생성 또는 멱등 upsert가 예측 가능하게 동작한다.

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
- [ ] `ktooh-dashboard-poc` aggregate/query 경로가 이 계약과 모순 없이 동작하는지 함께 점검한다.

---

## 3. 선결 결정

### 3.1 `노출` 매핑

- [ ] `노출 = attentive_population`
- [ ] 또는 `노출 = visible_population` + `가시권` 별도 재정의

권장:

- [ ] 1차는 `가시권 = visible_population`, `노출 = attentive_population`, `시청 = watched_population`

### 3.2 creative 미확정 정책

- [ ] campaign 단일 매칭이면 `creative_id = NULL`로 적재 허용
- [ ] campaign 복수 매칭이면 reject

권장:

- [ ] campaign 단일이면 적재, creative는 단일 해소일 때만 채움

### 3.3 floating pedestrian pattern 범위

- [ ] 1차 릴리스에 포함
- [ ] 1차는 traffic만 적재하고 pattern은 2차로 이월

권장:

- [ ] 1차는 traffic 적재를 먼저 끝내고, pedestrian pattern은 `dwell_time_seconds`만 보수적으로 포함

### 3.4 fact 추적 컬럼 추가

- [ ] `audience_event_fact`에 `camera_code`, `raw_ref`, `source_schema` 추가
- [ ] 별도 운영 이력 테이블은 만들지 않음

권장:

- [ ] 추적 컬럼 추가 포함

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

### 4.3 책임 분리

- [ ] parser: raw line -> typed DTO
- [ ] normalization: typed DTO -> draft row
- [ ] attribution: media/campaign/creative 귀속 해소
- [ ] loader: DB insert/upsert 또는 삭제 후 재생성
- [ ] dashboard_registry: dashboard DB read 경계
- [ ] verify: 적재 후 수치 검증

---

## 5. 데이터 계약

**시간 필드(§2.5, §2.6)**: `occurred_at`, `occurred_date`, `occurred_hour`, `ts`, raw 시각 필드는 모두 UTC 기준을 따른다. 화면 조회 시에는 저장된 UTC 시각을 사용자 설정 시간대(기본 KST)로 변환해 사용한다.

### 5.1 내부 모델

- [ ] `BatchRequest`
- [ ] `DashboardBinding`
- [ ] `CollectedObject`
- [ ] `DemographicRawRecord`
- [ ] `FloatingRawRecord`
- [ ] `AudienceFactDraft`
- [ ] `TrafficDraft`
- [ ] `RejectedRow`
- [ ] `LoadSummary`

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

- [ ] `occurred_at`
- [ ] `occurred_date`
- [ ] `occurred_hour`
- [ ] `media_id`
- [ ] `campaign_id` (`NULL` 허용)
- [ ] `creative_id` (`NULL` 허용)
- [ ] `segment_type`
- [ ] `segment_value`
- [ ] `threshold_sec`
- [ ] `floating_population`
- [ ] `visible_population`
- [ ] `attentive_population`
- [ ] `watched_population`
- [ ] `watch_time_seconds`
- [ ] `dwell_time_seconds`
- [ ] `play_count`
- [ ] `allocation_basis`
- [ ] `source_type`
- [ ] `source_batch_id`
- [ ] `camera_code`
- [ ] `raw_ref`
- [ ] `source_schema`

### 5.5 `TrafficDraft`

- [ ] `media_id`
- [ ] `campaign_id` (`NULL` 허용)
- [ ] `ts`
- [ ] `vehicle_type`
- [ ] `direction`
- [ ] `count`
- [ ] `camera_code`
- [ ] `raw_ref`
- [ ] `source_batch_id`

---

## 6. 원천별 적재 규칙

### 6.1 demographic -> audience facts

생성 규칙:

- [ ] total 세그먼트 row 생성
- [ ] gender 세그먼트 row 생성
- [ ] age 세그먼트 row 생성
- [ ] watch threshold row는 `1`, `3`, `7`초 기준으로 생성

metric 규칙:

- [ ] `visible_population = 1`
- [ ] `attentive_population = 노출 정책에 따른 0/1`
- [ ] `watched_population = threshold 통과 시 1`
- [ ] `watch_time_seconds = gaze_duration`
- [ ] `dwell_time_seconds = stay_duration`
- [ ] `play_count = 0`
- [ ] `allocation_basis = camera_demographic`

### 6.2 floating -> traffic

대상 타입:

- [ ] `Car`
- [ ] `Bus`
- [ ] `Truck`
- [ ] `Motorcycle`

적재 규칙:

- [ ] `ts = start_time` (UTC)
- [ ] `count = 1`
- [ ] `campaign_id = NULL`
- [ ] `direction`은 canonical 값 집합으로 고정한다.

### 6.3 floating -> audience pattern

- [ ] 대상 타입은 `Pedestrian`
- [ ] 1차에서 제외 가능
- [ ] 포함 시 `dwell_time_seconds = dwell` 중심으로 최소 적재
- [ ] campaign/creative 귀속은 1차에서 제외 또는 `NULL`

---

## 7. DB 변경안

### 7.1 유지할 테이블

- [x] `audience_event_fact`
- [x] `agg_audience_minute`
- [x] `agg_audience_hourly`
- [x] `agg_audience_daily`
- [x] `traffic`

### 7.2 `audience_event_fact` 변경

- [ ] `camera_code VARCHAR(50)` 추가
- [ ] `raw_ref VARCHAR(255)` 추가
- [ ] `source_schema VARCHAR(64)` 추가

인덱스 검토:

- [ ] `ix_aef_camera_occurred`
- [ ] `ix_aef_raw_ref`
- [x] unique key 후보: `(source_batch_id, raw_ref, segment_type, segment_value, threshold_sec)`
- [ ] `source_batch_id` 생성 규칙을 문서와 코드에 같은 방식으로 고정한다.

### 7.3 `traffic` 변경

- [ ] `camera_code VARCHAR(50)` 추가
- [ ] `source_batch_id VARCHAR(64)` 추가
- [ ] `raw_ref VARCHAR(255)` 추가

인덱스 검토:

- [ ] `ix_traffic_camera_ts`
- [ ] `ix_traffic_source_batch`
- [x] unique key 후보: `(source_batch_id, raw_ref, vehicle_type, direction)`

### 7.4 별도 운영 이력 테이블 미도입

- [x] `batch_runs`, `batch_run_files`, `batch_quarantine`는 만들지 않는다.
- [x] 운영 중 재처리가 필요하면 대상 일자/매체 데이터를 삭제 후 다시 적재한다.
- [x] 실패/제외 row는 영구 저장 테이블이 아니라 로그와 테스트 결과로 확인한다.
- [ ] loader는 삭제 후 재생성 또는 upsert 중 하나로 동작 방식을 고정한다.

---

## 8. 구현 단계

### 8.1 Phase 0. 구조와 계약 정리 (`Tidy`)

대상 파일:

- [ ] `src/models.py`
- [ ] 신규 `dashboard_registry.py`
- [ ] 신규 `collector.py`
- [ ] 신규 parser/normalization/loader 파일
- [ ] `README.md`

작업:

- [ ] 현재 스캐폴드 모델을 실제 raw schema 기준으로 재정의
- [ ] env var 계약을 `MEDIA_BATCH_` 기준으로 고정
- [ ] `run-batch` 명령 추가 계획 확정
- [ ] `PipelineBuilder.timezone_name`을 `UTC`로 통일

### 8.2 Phase 1. dashboard registry 조회 (`Feature`)

- [ ] `media_id`로 active cameras 조회
- [ ] `camera_code`, `source_type`, `media_id` binding 생성
- [ ] `media_campaign_map`, `campaign_schedules`, `creatives` 로딩 함수 추가

### 8.3 Phase 2. source object 수집 (`Feature`)

- [ ] camera/source_type별 S3 prefix 계산
- [ ] object listing
- [ ] local raw root fallback
- [ ] object metadata manifest 생성
- [ ] 페이지네이션 누락 없이 완전 수집

### 8.4 Phase 3. parser 구현 (`Feature`)

- [ ] line-by-line jsonl 스트리밍 파싱
- [ ] typed DTO 변환
- [ ] invalid timestamp/numeric/enum reject taxonomy 구현
- [ ] `raw_ref = {s3_key}:{line_number}` 규칙 고정

완료 조건:

- [ ] 샘플 jsonl을 실제 parser로 읽어 DTO를 만든다.
- [ ] 잘못된 row는 reject 결과로 분리되고 로드 대상에서 제외된다.

### 8.5 Phase 4. demographic normalization (`Feature`)

- [ ] `DemographicRawRecord -> AudienceFactDraft[]`
- [ ] total/gender/age 세그먼트 분해
- [ ] threshold row 생성
- [ ] attentive/watched 산식 적용

### 8.6 Phase 5. floating normalization (`Feature`)

- [ ] vehicle type 분류
- [ ] direction/status 정규화
- [ ] `FloatingRawRecord -> TrafficDraft[]`
- [ ] pedestrian pattern row 정책 적용

### 8.7 Phase 6. attribution (`Feature`)

- [ ] media/campaign schedule overlap 매칭
- [ ] creative_name 해소
- [ ] 복수 campaign 매칭 시 reject 정책 반영

### 8.8 Phase 7. loader 구현 (`Feature`)

- [ ] audience fact idempotent insert/upsert
- [ ] traffic idempotent insert/upsert
- [ ] `source_batch_id` 생성 규칙 구현
- [ ] 삭제 후 재생성 모드와 upsert 모드 중 하나를 고정

완료 조건:

- [ ] 같은 원천 파일을 다시 처리해도 중복 적재되지 않는다.
- [ ] 삭제 후 재생성 또는 upsert 재실행 모두 예측 가능하게 동작한다.

### 8.9 Phase 8. aggregate / verify (`Feature`)

- [ ] aggregate ETL 호출 방식 확정
- [ ] raw count vs loaded count 검증
- [ ] aggregate row 생성 여부 검증
- [ ] UTC 저장 후 dashboard 조회 시 사용자 시간대(기본 KST) 기준으로 기대한 날짜/시간에 노출되는지 검증

### 8.10 Phase 9. CLI 운영화 (`Feature`)

- [ ] `run-batch` 명령 추가
- [ ] `--dry-run`
- [ ] `--source-type demographic|floating|all`
- [ ] `--camera-code`

---

## 9. 테스트 전략

### 9.1 단위 테스트

- [ ] parser demographic
- [ ] parser floating
- [ ] demographic normalization
- [ ] floating normalization
- [ ] attribution
- [ ] step/status validation

### 9.2 통합 테스트

- [ ] media binding -> object listing
- [ ] demographic file -> audience facts -> aggregate ETL
- [ ] floating file -> traffic
- [ ] dry-run / rerun idempotency
- [ ] UTC 저장 후 KST 조회 경계 테스트

### 9.3 샘플 기반 golden 테스트

- [ ] `project-pooh-kt/docs/demographic.jsonl`
- [ ] `project-pooh-kt/docs/floating.jsonl`
- [ ] accepted row 수
- [ ] rejected row 수
- [ ] generated fact 수
- [ ] generated traffic 수
- [ ] UTC 자정 경계 row의 조회 날짜/시간

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

- [ ] batch 완료 후 `audience_event_fact` row 존재
- [ ] batch 완료 후 `traffic` row 존재
- [ ] aggregate row 생성 확인
- [ ] 사용자 시간대가 KST일 때 UTC 저장 데이터가 기대한 로컬 날짜/시간으로 조회되는지 확인

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
