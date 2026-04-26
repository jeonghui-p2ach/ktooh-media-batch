# PLAN: Trajectory Dashboard Compatibility Fixes

## 0. 문서 목적

이 문서는 `ktooh-media-batch`에서 생성·추출·계산한 trajectory 데이터와
`ktooh-dashboard-poc` 조회 계약 사이에서 확인된 호환성 및 계산식 문제를
개선하기 위한 단계별 작업 계획서다.

상위 문서:

- `PLAN_TRAJECTORY_FROM_06.md`: 06 노트북 기반 trajectory batch 이식 계획
- `PLAN_DASHBOARD_TRAJECTORY_INTEGRATION.md`: dashboard trajectory 조회 통합 계획
- 이 문서: 통합 이후 확인된 계산식·계약 보완 계획

상태 표기:

- `[ ]` 미착수
- `[~]` 진행 중
- `[x]` 완료

## 1. 전제와 원칙

### 1.1 전제

- [ ] 모든 시각 저장값은 UTC naive `datetime`으로 고정한다.
- [ ] dashboard 조회는 사용자 timezone 기준 날짜 범위를 UTC로 변환해 필터링한다.
- [ ] `target_date`는 batch 적재 단위이며, 사용자 timezone 표시용 날짜와 혼동하지 않는다.
- [ ] 기존 measurement dashboard API는 변경하지 않는다.
- [ ] trajectory API의 기존 public path는 유지한다.
- [ ] 구조 변경과 동작 변경은 분리 커밋한다.

### 1.2 우선순위

- [ ] P1. 카메라별 hourly metric 귀속 오류 제거
- [ ] P1. spatial heatmap `total_visible_dwell_s` 누적 오류 제거
- [ ] P2. `route_family_count` 의미 명확화 또는 시간대별 계산 보완
- [ ] P2. UTC 정규화 보장
- [ ] P3. 재적재 삭제 범위 명확화

### 1.3 완료 정의

- [ ] `media_id + camera_code + date range` 조회에서 hourly metric이 카메라별 의미와 일치한다.
- [ ] spatial heatmap에서 `total_visible_dwell_s` 선택 시 cell 단위 값이 재현 가능하게 계산된다.
- [ ] route count 필드 이름 또는 계산식이 dashboard 표시 의미와 일치한다.
- [ ] timezone-aware 입력 또는 offset 문자열이 UTC naive로 저장된다.
- [ ] 재적재 정책이 문서와 코드에서 동일하게 표현된다.
- [ ] details 탭과 map 화면이 수정된 trajectory 지표 의미를 오해 없이 표시한다.
- [ ] batch와 dashboard 양쪽 테스트가 통과한다.

## 2. 작업 단위

### 2.1 Unit A. 현재 계약 고정 및 회귀 테스트 추가 (`Tidy`)

목표:

- [ ] 수정 전에 현재 문제를 실패 테스트로 고정한다.
- [ ] 코드 동작 변경 없이 테스트명과 fixture로 의도를 명확히 한다.

작업:

- [ ] `ktooh-media-batch/tests/trajectory/test_metrics.py`에 카메라별 hourly 기대값 테스트 추가
- [ ] `ktooh-media-batch/tests/trajectory/test_loader.py`에 spatial dwell 누적 실패 케이스 추가
- [ ] `ktooh-media-batch/tests/trajectory/test_loader.py`에 timezone-aware datetime 정규화 기대 테스트 추가
- [ ] `ktooh-dashboard-poc/tests/test_trajectory_dashboard_api.py`에 route count 의미 테스트 추가
- [ ] 재적재 범위는 코드 변경 전 별도 테스트 또는 문서 확인 항목으로 고정

완료 조건:

- [ ] 새 테스트가 현재 구현에서 의도한 문제를 드러낸다.
- [ ] production code 변경 없이 테스트 추가만 포함된다.

검증:

- [ ] `cd ktooh-media-batch && uv run pytest tests/trajectory/test_metrics.py tests/trajectory/test_loader.py`
- [ ] `cd ktooh-dashboard-poc && uv run pytest tests/test_trajectory_dashboard_api.py`

### 2.2 Unit B. Hourly metric 카메라 귀속 수정 (`Feature`)

문제:

- [ ] `build_corrected_hourly_metrics`가 전체 `global_units`, `global_presence`를 한 번에 집계한다.
- [ ] loader는 `camera_name`이 없으면 context 첫 번째 카메라로 귀속한다.
- [ ] dashboard의 `camera_code` 필터 결과가 특정 카메라 지표처럼 보일 수 있다.

목표:

- [ ] hourly metric row가 명시적인 `camera_name` 또는 `camera_code` 의미를 가진다.
- [ ] camera filter가 dashboard에서 실제 카메라별 지표로 동작한다.

작업:

- [ ] `src/trajectory/metrics.py`에 카메라별 집계 단위를 도입한다.
- [ ] `global_presence` 기준으로 `camera_name`별 visible 지표를 계산한다.
- [ ] `unique_global_units`, `single_camera_units`, `multi_camera_units`, `mean_n_cameras`의 카메라별 의미를 확정한다.
- [ ] `hourly_metric_summary_df` 산출 row에 `camera_name`을 포함한다.
- [ ] loader의 첫 번째 카메라 fallback은 제거하거나 `media-wide` 전용 row에만 허용한다.
- [ ] dashboard view와 API 응답은 기존 `camera_code` 필터를 그대로 사용한다.

결정 필요:

- [ ] 옵션 A. `hourly_metric_summary_df`는 카메라별 row만 생성한다.
- [ ] 옵션 B. 카메라별 row와 `camera_code='ALL'` media-wide row를 함께 생성한다.
- [ ] 1차 권장안은 옵션 A다. 기존 dashboard 필터 의미가 가장 단순하고 중복 집계 위험이 낮다.

완료 조건:

- [ ] 각 hourly row는 `camera_name`을 가진다.
- [ ] `camera_codes=CAM_14` 조회가 `CAM_14` presence만 반영한다.
- [ ] 다중 카메라 global unit이 여러 카메라에서 보이면 각 카메라 row에 독립적으로 반영된다.

검증:

- [ ] `cd ktooh-media-batch && uv run pytest tests/trajectory/test_metrics.py tests/trajectory/test_loader.py`
- [ ] `cd ktooh-dashboard-poc && uv run pytest tests/test_trajectory_dashboard_api.py`

### 2.3 Unit C. Spatial heatmap dwell 누적 수정 (`Feature`)

문제:

- [ ] 같은 cell에 여러 transition row가 들어오면 `point_count`는 누적되지만 `total_visible_dwell_s`는 마지막 row 값으로 덮인다.
- [ ] dashboard는 `metric=total_visible_dwell_s`를 허용하므로 heatmap 값이 잘못 표시될 수 있다.

목표:

- [ ] cell 단위 `total_visible_dwell_s`가 정의된 정책에 따라 누적된다.
- [ ] `heatmap_value`, `point_count`, `visible_unique_units`, `total_visible_dwell_s`의 의미가 분리된다.

작업:

- [ ] `build_spatial_heatmap_cells`에서 `total_visible_dwell_s` 누적 로직을 수정한다.
- [ ] 동일 `local_unit_id`가 같은 cell에 여러 point를 남길 때 dwell을 중복 누적할지 정책을 확정한다.
- [ ] 권장 정책은 `local_unit_id + cell_id + hour` 단위 dwell 1회 누적이다.
- [ ] point 밀도는 `point_count`, 유닛 밀도는 `visible_unique_units`, 체류 강도는 `total_visible_dwell_s`로 분리한다.
- [ ] 테스트 fixture에 동일 cell 다중 row, 동일 unit 다중 point, 다중 unit 케이스를 포함한다.

완료 조건:

- [ ] 동일 cell의 여러 row dwell이 덮이지 않는다.
- [ ] 동일 unit의 여러 point 때문에 dwell이 과대 누적되지 않는다.
- [ ] `metric=total_visible_dwell_s` 응답이 batch 산출과 일치한다.

검증:

- [ ] `cd ktooh-media-batch && uv run pytest tests/trajectory/test_loader.py`
- [ ] `cd ktooh-dashboard-poc && uv run pytest tests/test_trajectory_dashboard_api.py`

### 2.4 Unit D. Route count 의미 정리 (`Tidy`)

문제:

- [ ] `trajectory_hourly_metrics_dashboard_v.route_family_count`는 시간대별 route count가 아니라 날짜 단위 route family count다.
- [ ] hourly 응답에 포함되어 시간별 지표처럼 해석될 수 있다.

목표:

- [ ] API 필드 이름과 계산식이 같은 의미를 가진다.
- [ ] 기존 사용자가 오해할 수 있는 필드를 방치하지 않는다.

작업:

- [ ] dashboard 화면과 JS에서 `route_family_count` 사용 위치를 확인한다.
- [ ] API schema의 필드명을 바꿀지, view 계산식을 바꿀지 결정한다.
- [ ] 문서에 선택한 의미를 명시한다.

결정 필요:

- [ ] 옵션 A. 필드명을 `daily_route_family_count`로 변경하고 계산식은 유지한다.
- [ ] 옵션 B. `route_family_count`를 hour overlap 기반으로 재계산한다.
- [ ] 1차 권장안은 옵션 A다. 현재 route family 산출물이 시간 window 정보를 충분히 갖지 않으므로 안전하다.

완료 조건:

- [ ] 이름만 바꾸는 경우 migration/view/schema/API 테스트가 함께 갱신된다.
- [ ] 계산식을 바꾸는 경우 route family와 global unit 시간 overlap 기준 테스트가 추가된다.

검증:

- [ ] `cd ktooh-dashboard-poc && uv run pytest tests/test_trajectory_dashboard_api.py`

### 2.5 Unit E. UTC 정규화 보장 (`Feature`)

문제:

- [ ] loader의 `_datetime`은 timezone-aware datetime 또는 offset 문자열에서 `tzinfo`만 제거한다.
- [ ] dashboard repository는 저장값을 UTC naive로 가정하고 사용자 timezone 날짜 범위로 조회한다.

목표:

- [ ] 모든 loader 시간 변환은 UTC naive를 반환한다.
- [ ] naive 입력은 기존 계약대로 UTC naive로 유지한다.
- [ ] aware 입력은 UTC로 변환한 뒤 `tzinfo`를 제거한다.

작업:

- [ ] `src/trajectory/loader.py`의 `_datetime` 변환을 UTC 정규화로 수정한다.
- [ ] `src/trajectory/metrics.py`, `routes.py`, `materialization.py`의 datetime helper도 같은 정책을 적용할지 검토한다.
- [ ] offset 문자열, timezone-aware `datetime`, naive `datetime` 테스트를 추가한다.
- [ ] dashboard timezone 경계 조회 테스트와 연결한다.

완료 조건:

- [ ] `2026-04-23T09:00:00+09:00` 입력이 `2026-04-23 00:00:00` UTC naive로 저장된다.
- [ ] `2026-04-23 00:00:00` naive 입력은 그대로 저장된다.
- [ ] KST 조회 경계에서 UTC 자정 이전/이후 row가 기대 날짜에 포함된다.

검증:

- [ ] `cd ktooh-media-batch && uv run pytest tests/trajectory/test_loader.py tests/trajectory/test_metrics.py`
- [ ] `cd ktooh-dashboard-poc && uv run pytest tests/test_trajectory_dashboard_api.py`

### 2.6 Unit F. 재적재 삭제 범위 명확화 (`Tidy`)

문제:

- [ ] `persist_dashboard_rows`는 `media_id + target_date` 기준으로 기존 row를 삭제한다.
- [ ] CLI는 `campaign_id`, `creative_id`를 받지만 삭제 조건에는 포함하지 않는다.
- [ ] 부분 campaign 적재를 허용한다고 해석하면 다른 campaign row 삭제 위험이 있다.

목표:

- [ ] 재적재 정책을 코드와 문서에서 동일하게 만든다.
- [ ] 운영자가 전체 재생성과 부분 재생성을 혼동하지 않게 한다.

작업:

- [ ] 현재 운영 의도를 결정한다.
- [ ] 옵션 A. `media_id + target_date` 전체 재생성 정책을 유지하고 CLI 도움말과 문서에 명시한다.
- [ ] 옵션 B. `media_id + target_date + campaign_id + creative_id` 부분 재생성 정책으로 변경한다.
- [ ] 권장안은 옵션 A다. trajectory global unit과 route family는 media/date 전체 문맥에서 계산되므로 부분 삭제는 데이터 일관성을 깨기 쉽다.
- [ ] 옵션 A 선택 시 `campaign_id`, `creative_id`는 row 귀속 메타데이터이며 재적재 scope가 아님을 문서화한다.
- [ ] 옵션 B 선택 시 global unit unique 제약과 route family 중복 가능성을 먼저 검토한다.

완료 조건:

- [ ] CLI help 또는 README에 재적재 scope가 명시된다.
- [ ] 테스트가 전체 재생성 정책 또는 부분 재생성 정책 중 하나를 검증한다.

검증:

- [ ] `cd ktooh-media-batch && uv run pytest tests/trajectory/test_loader.py`

### 2.7 Unit G. 통합 검증 및 샘플 비교 (`Feature`)

목표:

- [ ] batch 산출물과 dashboard 응답이 동일한 의미로 연결되는지 end-to-end로 확인한다.

작업:

- [ ] fixture 기반 `load-dashboard --dry-run` row count를 기록한다.
- [ ] 실제 test DB에 trajectory fixture를 적재한다.
- [ ] dashboard API로 hourly, camera heatmap, spatial heatmap, routes, units를 조회한다.
- [ ] batch artifact 합계와 dashboard 응답 합계를 비교한다.
- [ ] 카메라 필터, campaign 필터, creative 필터, timezone 필터를 각각 검증한다.

완료 조건:

- [ ] hourly visible/dwell 합계가 batch 산출과 일치한다.
- [ ] spatial heatmap cell 합계가 loader 산출과 일치한다.
- [ ] route count 필드 의미가 문서와 응답에서 일치한다.
- [ ] UTC/KST 날짜 경계 조회가 기대대로 동작한다.

검증:

- [ ] `cd ktooh-media-batch && uv run pytest`
- [ ] `cd ktooh-dashboard-poc && uv run pytest`
- [ ] 필요 시 `trajectory-batch load-dashboard --dry-run` 샘플 실행

### 2.8 Unit H. Dashboard UI 동기화 (`Feature`)

문제:

- [ ] 현재 계획은 batch 계산식과 API 계약 보정 중심이며, 이미 존재하는 dashboard trajectory UI 반영 작업이 분리되어 있지 않다.
- [ ] `details.html`, `details.js`, `map.js`는 현재 `route_family_count`, `heatmap_value`, `visible_unique_units` 의미를 전제로 렌더링한다.
- [ ] API 필드명 또는 metric 의미가 바뀌면 화면 문구, 차트 라벨, KPI 제목, 빈 상태 설명도 함께 수정되어야 한다.

목표:

- [ ] dashboard details 탭과 map 화면이 수정된 trajectory 계약에 맞춰 동일한 의미를 보여준다.
- [ ] 사용자가 media-wide 수치와 camera-level 수치를 혼동하지 않도록 화면 copy와 상호작용을 정리한다.

작업:

- [ ] `ktooh-dashboard-poc/app/templates/pages/dashboard/details.html`의 trajectory KPI 제목과 표 헤더를 점검한다.
- [ ] `ktooh-dashboard-poc/app/static/features/dashboard/details.js`의 KPI 계산식이 새 계약과 일치하는지 수정한다.
- [ ] `route_family_count`가 `daily_route_family_count`로 바뀌면 details template, JS, schema 소비 코드를 함께 갱신한다.
- [ ] hourly chart 라벨에 camera-level 집계인지 media-wide 집계인지 명시한다.
- [ ] camera heatmap 표에서 metric 선택값과 표 제목이 일치하도록 제어를 추가하거나 copy를 보완한다.
- [ ] unit 상세 modal에 `camera_path`, dwell, confidence 외에 필요한 설명 문구가 있는지 점검한다.
- [ ] `ktooh-dashboard-poc/app/templates/pages/dashboard/map.html`과 `app/static/features/map/map.js`에서 spatial heatmap metric 선택 UI 필요 여부를 검토한다.
- [ ] map 화면이 현재 고정 `heatmap_value`만 요청하므로 `visible_unique_units` / `total_visible_dwell_s` 전환 UI를 넣을지 결정한다.
- [ ] trajectory API 로딩 실패 시 탭별 에러 메시지와 empty state 문구를 trajectory 전용 의미로 분리한다.
- [ ] i18n key가 부족하면 `app/core/i18n.py`에 trajectory 관련 문구를 추가한다.

결정 필요:

- [ ] 옵션 A. map 화면은 계속 `heatmap_value` 고정으로 유지하고 details 탭에서만 세부 비교를 제공한다.
- [ ] 옵션 B. map 화면에 metric selector를 추가해 `heatmap_value`, `visible_unique_units`, `total_visible_dwell_s`를 전환한다.
- [ ] 1차 권장안은 옵션 B다. 이번 보완의 핵심이 spatial metric 의미 정합화이므로 화면에서도 선택 가능해야 검증이 쉽다.

완료 조건:

- [ ] details trajectory KPI, 차트, 테이블 제목이 수정된 metric 의미와 일치한다.
- [ ] map heatmap이 선택된 metric과 동일한 legend/copy를 표시한다.
- [ ] API 필드명 변경이 있으면 UI에서 구 필드명을 참조하지 않는다.
- [ ] 빈 데이터와 오류 상태에서 사용자가 무엇이 없는지 이해할 수 있는 문구가 표시된다.

검증:

- [ ] `cd ktooh-dashboard-poc && uv run pytest tests/test_trajectory_dashboard_api.py`
- [ ] trajectory UI 관련 단위 테스트 또는 DOM 스냅샷 테스트가 없으면 최소 smoke 테스트를 추가한다.
- [ ] desktop과 mobile viewport에서 details 탭과 map 화면을 수동 확인한다.

## 3. 권장 실행 순서

1. [ ] Unit A. 실패 테스트와 현재 계약 고정
2. [ ] Unit B. Hourly metric 카메라 귀속 수정
3. [ ] Unit C. Spatial heatmap dwell 누적 수정
4. [ ] Unit D. Route count 의미 정리
5. [ ] Unit E. UTC 정규화 보장
6. [ ] Unit F. 재적재 삭제 범위 명확화
7. [ ] Unit G. 통합 검증 및 샘플 비교
8. [ ] Unit H. Dashboard UI 동기화

## 4. 커밋 분리 기준

권장 커밋:

- [ ] `test: capture trajectory dashboard compatibility gaps`
- [ ] `fix: compute trajectory hourly metrics per camera`
- [ ] `fix: accumulate trajectory spatial dwell by cell`
- [ ] `refactor: clarify trajectory route count dashboard contract`
- [ ] `fix: normalize trajectory loader datetimes to utc`
- [ ] `docs: clarify trajectory dashboard reload scope`
- [ ] `test: verify trajectory dashboard integration totals`
- [ ] `feat: align trajectory dashboard ui with revised metrics`

주의:

- [ ] `Tidy` 커밋에는 production behavior 변경을 넣지 않는다.
- [ ] `Feature` 커밋에는 관련 없는 formatting 또는 rename을 넣지 않는다.
- [ ] 같은 파일을 수정하더라도 구조 정리와 계산식 변경은 분리한다.

## 5. 리스크와 확인 질문

### 5.1 리스크

- [ ] 카메라별 hourly로 바꾸면 기존 media-wide 합계를 기대하던 dashboard 화면의 숫자가 달라질 수 있다.
- [ ] spatial dwell을 unit 단위 1회 누적으로 바꾸면 point density와 dwell intensity의 스케일이 달라진다.
- [ ] route count 필드명을 바꾸면 API 소비 코드 수정이 필요하다.
- [ ] UTC 정규화는 기존에 KST naive로 잘못 저장된 과거 데이터와 혼재될 수 있다.
- [ ] map 화면에 metric selector를 추가하면 기존 사용자의 기본 heatmap 해석이 달라질 수 있다.

### 5.2 구현 전 확인 질문

- [ ] hourly metric은 카메라별 row만 둘지, `ALL` row를 함께 둘지 결정해야 한다.
- [ ] spatial dwell은 `local_unit_id + cell_id + hour` 단위 1회 누적 정책으로 확정할지 결정해야 한다.
- [ ] route count는 필드명 변경으로 정리할지, 시간대별 계산식으로 바꿀지 결정해야 한다.
- [ ] 재적재는 `media_id + target_date` 전체 재생성 정책으로 확정할지 결정해야 한다.
- [ ] map 화면에서 trajectory heatmap metric selector를 노출할지 결정해야 한다.
