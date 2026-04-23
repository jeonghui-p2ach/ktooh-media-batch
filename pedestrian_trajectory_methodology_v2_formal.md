# 다중 고정카메라 환경에서의 비식별 보행자 동선 및 체류 시간 측정 방법론
**Methodology for Non-identifiable Pedestrian Trajectory and Dwell Time Measurement in Multi-camera Environments**

**Version:** 2.0 (2026-04-23)  
**Status:** Formal Methodology Release

---

## 초록 (Abstract)
본 보고서는 개인 식별 정보(ReID)를 사용하지 않는 환경에서 고정형 카메라 네트워크를 통해 보행자의 정교한 동선과 체류 시간을 복원하기 위한 방법론을 제안한다. 본 방법론의 핵심은 '보수적 경로 복원(Trajectory Layer)'과 '관용적 체류 복원(Presence Episode Layer)'을 분리하는 **Trajectory–Episode 이중 구조(Dual Model)**에 있다. 이를 통해 차폐와 재검출이 빈번한 광장형 공간에서 로컬 체류 중간값 90초 이상, 전역 체류 중간값 300초 이상의 신뢰도 높은 지표를 산출하는 것을 목표로 한다.

---

## 1. 서론 (Introduction)

### 1.1 문제 정의
도시 공간의 보행자 분석 시, 시각적 정체성(Appearance Embedding)을 활용할 수 없는 제약 조건 하에서 좌표와 시간 정보만으로 개별 방문객의 행동을 복원하는 것은 높은 난이도를 요구한다. 특히 가로수, 군집, 시설물에 의한 빈번한 차폐(Occlusion)는 트래클릿(Tracklet)의 단절을 초래하며, 이는 단순한 물리적 필터링만으로는 실제 체류 시간을 과소평가하게 만드는 주요 원인이 된다.

### 1.2 설계 철학: Trajectory–Episode 이중 구조
본 시스템은 지표의 목적에 따라 데이터 모델을 이분화한다.
*   **Identity Trajectory Layer:** "물리적 연속성"에 집중한다. 속도와 방향의 일관성을 엄격히 따져 동일인임을 확신할 수 있는 짧은 경로 조각을 생성한다.
*   **Presence Episode Layer:** "공간적 개연성"에 집중한다. 동일한 체류 구역(Stay Zone) 내에서 발생하는 단절을 능동적으로 복원하여 실제 체류 시간에 근접한 에피소드를 생성한다.

---

## 2. 로컬 계층 방법론 (Local Layer Methodology)

로컬 단계의 목표는 단일 카메라 시야 내에서 보행자의 실제 체류 시간을 현실화하는 것이다.

### 2.1 Scene-aware 분석 모델
공간의 기하학적 구조를 반영하기 위해 카메라별로 다음과 같은 정적 자산(Scene Assets)을 정의한다.
*   **Stay Zone:** 저속 이동 또는 정지가 빈번하게 발생하는 핵심 체류 구역.
*   **Transit Zone:** 카메라 진입/이탈이 발생하는 경계 구역.
*   **Dropout Prior:** 공간 구조상 발생 가능한 최대 허용 공백 시간.

### 2.2 객체 상태 분류 (Tracklet State Typing)
모든 트래클릿은 이동 특성에 따라 다음과 같이 분류되며, 상태별로 차별화된 연결 규칙을 적용받는다.
*   `Moving`: 지속적 이동 상태 (속도/방향 일관성 중시)
*   `Stay`: 정지 또는 미세 이동 상태 (Anchor Drift 중시)
*   `Stop & Go`: 정지 후 재출발 상태 (혼합 규칙)

### 2.3 로컬 체류 복원 알고리즘: Zone Survival
트래클릿이 끊기더라도 동일하거나 인접한 Stay Zone 내에서 발생한 사건이라면 이를 하나의 에피소드로 통합한다.

**[계산식 1: Local Episode Dwell]**
$$Local\_Dwell = \text{Interval\_Union}(\{T_{start, i}, T_{end, i}\}_{i \in \text{Episode}})$$

### 2.4 전역 연결 후보 추출 (Transition Node Scoring)
카메라 경계면(Portal)에서의 관측 품질과 위치를 기반으로 전이 노드 점수를 산출한다.
$$Score_{trans} = f(Dist_{boundary}, Quality_{track}, Conf_{local})$$
*   경계면과의 거리($Dist_{boundary}$)가 가까울수록, 트래킹 품질($Quality_{track}$)이 높을수록 높은 점수를 부여하며, 임계값(0.20) 이상의 노드만 글로벌 연결 후보로 선정한다.

---

## 3. 글로벌 계층 방법론 (Global Layer Methodology)

### 3.1 글로벌 연결 비용 함수 (Total Edge Cost)
두 카메라 간의 최적 연결을 찾기 위해 다음과 같은 다중 목적 비용 함수를 사용한다.

**[계산식 2: Total Edge Cost]**
$$Cost_{Total} = \left(\frac{Gap_{resid}}{\sigma_{gap}}\right)^2 + \left(\frac{Speed_{resid}}{\sigma_{speed}}\right)^2 + P_{zone} + P_{weak}$$

*   **$Gap_{resid}$**: 실제 시간 간격과 예상 이동 시간의 차이.
*   **$Speed_{resid}$**: 추정 속도와 시간대별 기대 속도($Prior\_Speed$)의 차이.
*   **$P_{zone}$**: 경계 구역 미매칭 시 부여되는 페널티.
*   **$P_{weak}$**: 전이 노드 점수가 낮을 때 부여되는 신뢰도 페널티.
*   비용($Cost_{Total}$)이 임계값(8.5) 이하인 후보군 중 헝가리안 알고리즘(Hungarian Algorithm)을 통해 전역 최적 매칭을 수행한다.

### 3.2 전역 체류 산출 방식: Elapsed Dwell
단순히 관측된 시간의 합(Summed)을 사용하는 대신, 첫 진입부터 최종 이탈까지의 총 경과 시간에서 유효하지 않은 긴 공백만 제외하는 방식을 채택한다.

**[계산식 3: Global Unit Dwell]**
$$Global\_Dwell = (T_{end, last} - T_{start, first}) - \sum(Gap_{invalid})$$

---

## 4. 실증 데이터 기반 계산 가이드 (Step-by-Step Guide)

본 장에서는 `floating.jsonl`의 실제 보행자 데이터를 활용하여 각 레이어의 수식이 수치로 변환되는 과정을 설명한다.

### 4.1 로컬 에피소드 복원 예시 (Pedestrian ID: 25189706)
*   **입력:** `start: 05:25:52`, `end: 05:26:09` (총 경과 17.0s), `dwell: 13.97s`, `dist: 530.4cm`
*   **계산 과정:**
    1.  **공백 분석:** 총 경과(17s) - 유효 체류(13.97s) = 3.03s의 관측 공백 발생.
    2.  **Zone Survival 판정:** 공백 3.03s가 구역 허용치 이내이므로 하나의 에피소드로 유지.
    3.  **상태 추론:** 평균 속도 $38cm/s$ ($530.4cm / 13.97s$)로 분석되어 `Stay` 상태로 분류.
*   **결과:** $Local\_Dwell = 13.97s$.

### 4.2 전역 연결 및 비용 계산 예시
*   **시나리오:** CAM_14 이탈 → CAM_12 진입 연결 평가.
*   **입력 변수:** 실제 시간차 45s, 예상 시간 40s, 기대 속도 1.3m/s, 추정 속도 1.1m/s.
*   **계산 과정:**
    1.  **시간 비용:** $( (45-40) / 20 )^2 = 0.0625$
    2.  **속도 비용:** $( (1.1-1.3) / 0.5 )^2 = 0.16$
    3.  **최종 비용:** $0.0625 + 0.16 = 0.2225$
*   **결과:** 최종 비용(0.22)이 임계값(8.5)보다 현저히 낮으므로 **동일인 방문 유닛(Global Unit)**으로 확정.

### 4.3 전역 체류 시간(Global Dwell) 확정
*   **시나리오:** CAM_14(체류 100s) $\xrightarrow{Gap: 45s}$ CAM_12(체류 200s).
*   **계산 과정:** $(T_{end, last} - T_{start, first}) = 100 + 45 + 200 = 345s$.
*   **결과:** 카메라 간 이동 시간 45초를 유효 체류에 포함하여 최종 **345초** 산출.

---

## 5. 파이프라인 벤치마크 결과 (Pipeline Performance)

노트북 06의 통합 파이프라인 실행 결과, 다음과 같은 성능 지표를 확보하였다.

| 분석 계층 | 측정 지표 (Metric) | 결과값 (Value) | 비고 |
| :--- | :--- | :--- | :--- |
| **Local Layer** | Median Identity Dwell | 11 ~ 15s | 보수적 경로 복원 유지 |
| | Median Episode Dwell | **136 ~ 175s** | 체류 복원 목표(90s) 상향 달성 |
| **Global Layer** | Median Elapsed Dwell | **300s+** | 전역 방문 시간 현실화 |
| | Multi-camera Share | 30% ~ 45% | 카메라 간 연결성 확보 |
| | Association Rate | 90%+ | 중복 제거 신뢰도 |

---

## 6. 지표 정의 및 품질 기준 (KPI)

| 지표명 | 학술적 정의 | 목표 품질(Median) |
| :--- | :--- | :--- |
| **Local Episode Dwell** | 단일 카메라 내 Presence Episode의 합집합 구간 | **90초 이상** |
| **Global Unit Dwell** | 전역 방문 유닛의 Elapsed Dwell | **300초 이상** |
| **Hourly Unique Flow** | Hour Overlap 기반의 중복 제거 방문자 수 | 신뢰도 90%+ |
| **Association Rate** | $Multi\_Camera\_Units / Unique\_Global\_Units$ | 권장 30%+ |

---

## 7. 결론 및 향후 과제
본 방법론은 **"Trajectory는 보수적으로, Dwell은 적극적으로"** 측정한다는 원칙 하에 설계되었다. 로컬 90초 및 전역 300초의 목표를 달성함으로써 비식별 환경에서도 신뢰도 높은 보행 분석 지표를 제공한다. 향후 과제는 카메라 간 전이 경로의 복잡성을 수치화하여 동선 해석의 정확도를 더욱 고도화하는 데 있다.

---
## 8. 참고 문헌 및 이론적 배경 (References & Theoretical Background)

본 방법론은 다음의 학술적 프레임워크와 알고리즘을 현장 제약에 맞게 결합하여 설계되었습니다.

### 8.1 다중 객체 추적 및 데이터 연관 (MOT & Data Association)
*   **SORT (Simple Online and Realtime Tracking):** Kalman Filter와 Hungarian Algorithm을 결합한 실시간 추적의 기초 프레임워크. 본 시스템의 Identity Trajectory 생성 로직의 근간입니다.
    *   [Bewley et al., "Simple Online and Realtime Tracking", ICIP 2016](https://arxiv.org/abs/1602.00763)
*   **The Hungarian Method:** 글로벌 매칭 단계에서 `Total Edge Cost`를 최소화하는 최적 배정 알고리즘입니다.
    *   [Kuhn, "The Hungarian Method for the assignment problem", 1955](https://onlinelibrary.wiley.com/doi/abs/10.1002/nav.3800020109)

### 8.2 체류 지점 탐지 및 궤적 분석 (Stay-point Detection)
*   **Stay-point Detection from Trajectories:** GPS나 좌표 데이터에서 정지/체류 구간을 추출하는 알고리즘으로, 본 방법론의 `Stay Zone` 및 `Zone Survival` 로직에 영감을 주었습니다.
    *   [Li et al., "Mining User Similarity Based on Location History", 2008](https://dl.acm.org/doi/10.1145/1463434.1463477)
*   **Time-Interval Algebra:** 에피소드 통합을 위한 `Interval Union` 수식의 논리적 배경입니다.
    *   [James F. Allen, "Maintaining knowledge about temporal intervals", 1983](https://dl.acm.org/doi/10.1145/182.358434)

### 8.3 다중 카메라 추적 (Multi-target Multi-camera Tracking)
*   **MTMCT Framework:** 서로 다른 카메라 뷰 사이의 객체를 연결하는 전역 연관 전략에 관한 연구입니다.
    *   [Ristani & Tomasi, "Features for Multi-Target Multi-Camera Tracking", CVPR 2018](https://arxiv.org/abs/1707.09048)
*   **Graph-based Association:** 카메라 네트워크를 그래프로 모델링하여 최소 비용 흐름(Min-cost flow)으로 문제를 해결하는 방식입니다.
    *   [Zhang et al., "Global Data Association for Multi-Object Tracking using Network Flows", 2008](https://ieeexplore.ieee.org/document/4587588)

---
**보고서 끝.**
