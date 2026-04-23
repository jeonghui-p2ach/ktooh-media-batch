# KTOOH Media Batch

`project-pooh-kt` raw jsonl을 읽어 `ktooh-dashboard-poc` 분석 테이블에 적재하는 독립 배치 프로젝트다.

## 범위

- 입력: `demographic.jsonl`, `floating.jsonl`
- 조회: `ktooh-dashboard-poc`의 `media`, `cameras`, `media_campaign_map`, `campaign_schedules`, `creatives`
- 출력:
  - `audience_event_fact`
  - `traffic`

## 핵심 분리

- camera source type의 `floating`과 dashboard metric의 `floating_population`은 다르게 취급한다.
- external floating population batch는 이 프로젝트 범위 밖이다.
- trajectory ETL과 이 프로젝트는 분리한다.
- 배치 이력 테이블은 두지 않고, 필요 시 삭제 후 다시 생성하는 운영 방식을 쓴다.

## 문서

- [PLAN.md](PLAN.md)

## 초기 구조

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
tests/
```

## CLI

```bash
uv sync
uv run python -m src.main plan --target-date 2026-04-23 --media-id 101
uv run python -m src.main run-step collect-s3-objects --target-date 2026-04-23 --media-id 101
uv run python -m src.main run-batch --target-date 2026-04-23 --media-id 101 --dry-run
```

## 현재 상태

- `UTC` 기준 `PipelineBuilder`와 `run-batch` CLI 구현
- local raw fallback + S3 object listing 경계 구현
- demographic / floating parser 구현
- demographic -> `audience_event_fact`, floating -> `traffic` 정규화 구현
- dashboard DB 기반 camera binding / attribution 조회 구현
- audience/traffic 적재와 aggregate ETL 호출 경로 구현
- 재생성/멱등 중심 적재 방향 고정

남은 작업:

- dashboard aggregate/query 경로와 UTC 조회 계약 정합성 점검
- canonical `direction` 값과 `노출` 정책 최종 확정
- DB 컬럼 추가 시 loader가 그 컬럼을 실제로 채우도록 확장
- 실제 DB 연결 상태에서 end-to-end 통합 검증
