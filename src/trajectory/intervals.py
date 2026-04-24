from collections.abc import Sequence
from datetime import datetime


def union_interval_seconds(intervals: Sequence[tuple[datetime, datetime]]) -> float:
    """
    주어진 datetime 구간(start, end)들의 겹치는 영역을 병합하여
    고유한 전체 지속 시간(초) 합을 반환합니다.
    """
    if not intervals:
        return 0.0

    # 1. start_time 기준으로 정렬
    sorted_intervals = sorted(intervals, key=lambda x: x[0])

    union_seconds = 0.0
    current_start, current_end = sorted_intervals[0]

    for start, end in sorted_intervals[1:]:
        if start <= current_end:
            # 겹치거나 이어지는 경우: current_end 갱신
            current_end = max(current_end, end)
        else:
            # 겹치지 않는 경우: 누적하고 current 구간 갱신
            union_seconds += (current_end - current_start).total_seconds()
            current_start, current_end = start, end

    # 마지막 구간 누적
    union_seconds += (current_end - current_start).total_seconds()

    return max(0.0, union_seconds)
