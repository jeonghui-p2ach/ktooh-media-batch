# KTOOH Media Batch

`project-pooh-kt`의 원천 데이터(JSONL, S3)를 읽어 분석 테이블에 적재하고 통계(Aggregate)를 생성하는 독립 배치 서비스입니다.
기존 노트북 기반의 분석 로직을 순수 Python으로 완전히 독립시켜 구현하였습니다.

## 주요 기능

- **S3 수집 (`measurement`)**: `ktooh-raw` S3 버킷에서 `demographic`, `floating` 데이터를 수집
- **Demographic 분석**: 연령/성별 감지 데이터 정규화 및 적재
- **Floating 분석**: 유동인구 이동 패턴 및 체류 시간 분석
- **Trajectory 분석 (`trajectory`)**: 다중 카메라 간의 동선 관리 및 GPS 기반 히트맵 생성
- **통계 집계**: Audience Fact 기반의 분/시간/일 단위 자동 집계 연동

## 프로젝트 구조

```text
src/
├── common/             # 공통 설정 및 로깅
├── measurement/        # Demographic & Floating 배치 파이프라인
│   ├── collector.py    # S3 수집 로직
│   ├── parser_*.py     # 데이터 파싱
│   ├── loader_*.py     # DB 적재 및 통계 트리거
│   └── service.py      # 배치 실행 제어
└── trajectory/         # Trajectory & GPS 분석 파이프라인
    ├── stages.py       # 파이프라인 단계 정의
    ├── materialization.py # 글로벌 유닛 생성 로직 (Directed Chain)
    ├── solver.py       # Hungarian 알고리즘 기반 매칭
    └── scoring.py      # 5항 비용 함수 기반 엣지 가중치
```

## 설치 및 설정

### 의존성 설치
```bash
uv sync
```

### 환경 변수 설정
운영 시 다음 환경 변수가 필요합니다:
- `MEDIA_BATCH_DATABASE_URL`: 대상 PostgreSQL 접속 주소
- `MEDIA_BATCH_SOURCE_BUCKET`: (선택) 원천 S3 버킷명 (기본: `ktooh-raw`)
- `MEDIA_BATCH_RAW_SOURCE_ROOT`: (선택) 로컬 테스트용 JSONL 루트 경로

## 사용 방법 (CLI)

### 1. Measurement 배치 실행 (Demographic/Floating)
```bash
# 전체 파이프라인 실행
uv run media-batch run-batch --target-date 2026-04-24 --media-id 101

# 실행 없이 데이터만 점검 (Dry-run)
uv run media-batch run-batch --target-date 2026-04-24 --media-id 101 --dry-run
```

### 2. Trajectory 배치 실행
```bash
# 로컬 아티팩트 기반 대시보드 적재
uv run trajectory-batch load-dashboard \
  --target-date 2026-04-24 \
  --run-root ./outputs \
  --media-id 101 \
  --database-url postgresql://...
```

## 현재 상태

- [x] **Phase 1: 모듈 독립화 완료** - 노트북 의존성 100% 제거
- [x] **Hungarian Solver 적용** - 정교한 동선 매칭 알고리즘 구현
- [x] **S3 최적 수집 구현** - Pagination 및 Gzip 지원
- [x] **단위 테스트 통과** - 50개 이상의 테스트 케이스 통과 (TDD)

## 문서

- [PLAN.md](PLAN.md): 전체 마이그레이션 계획 및 진행 상황
- [s3_demographic_floating_review.md](.gemini/antigravity/brain/0ea03698-d523-4075-bc02-8c535463ea0c/s3_demographic_floating_review.md): S3 수집 및 분석 상세 리뷰
- [code_review_ktooh_media_batch.md](.gemini/antigravity/brain/0ea03698-d523-4075-bc02-8c535463ea0c/code_review_ktooh_media_batch.md): Trajectory 모듈 정합성 리뷰
