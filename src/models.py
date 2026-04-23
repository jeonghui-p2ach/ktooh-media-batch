from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

WorkflowStatus = Literal["Succeeded", "Failed", "Error"]
SourceType = Literal["demographic", "floating"]


@dataclass(frozen=True, slots=True)
class BatchWindow:
    target_date: date
    timezone_name: str
    media_id: int


@dataclass(frozen=True, slots=True)
class PipelinePlan:
    window: BatchWindow
    steps: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BatchRequest:
    target_date: date
    media_id: int
    source_type: str
    camera_code: str | None
    dry_run: bool


@dataclass(frozen=True, slots=True)
class DashboardBinding:
    camera_code: str
    source_type: SourceType
    media_id: int
    camera_id: int | None


@dataclass(frozen=True, slots=True)
class CollectedObject:
    source_type: SourceType
    camera_code: str
    key: str
    source_batch_id: str
    local_path: Path | None = None
    bucket: str | None = None


@dataclass(frozen=True, slots=True)
class DemographicRawRecord:
    camera_code: str
    source_batch_id: str
    raw_ref: str
    occurred_at: datetime
    ended_at: datetime
    stay_duration_seconds: Decimal
    gaze_duration_seconds: Decimal
    gender: str
    age_band: str
    creative_name: str | None


@dataclass(frozen=True, slots=True)
class FloatingRawRecord:
    camera_code: str
    source_batch_id: str
    raw_ref: str
    object_type: str
    started_at: datetime
    ended_at: datetime
    dwell_seconds: Decimal
    status: str


@dataclass(frozen=True, slots=True)
class AudienceFactDraft:
    occurred_at: datetime
    occurred_date: date
    occurred_hour: int
    media_id: int
    campaign_id: int | None
    creative_id: int | None
    creative_name: str | None
    segment_type: str
    segment_value: str
    threshold_sec: int | None
    floating_population: Decimal
    visible_population: Decimal
    attentive_population: Decimal
    watched_population: Decimal
    watch_time_seconds: Decimal
    dwell_time_seconds: Decimal
    play_count: Decimal
    allocation_basis: str | None
    source_type: str
    source_batch_id: str
    camera_code: str
    raw_ref: str
    source_schema: str


@dataclass(frozen=True, slots=True)
class TrafficDraft:
    media_id: int
    campaign_id: int | None
    ts: datetime
    vehicle_type: str
    direction: str
    count: int
    camera_code: str
    raw_ref: str
    source_batch_id: str


@dataclass(frozen=True, slots=True)
class RejectedRow:
    source_type: SourceType
    camera_code: str
    source_batch_id: str
    raw_ref: str
    reason: str
    detail: str | None


@dataclass(frozen=True, slots=True)
class LoadSummary:
    collected_objects: int
    demographic_records: int
    floating_records: int
    rejected_rows: int
    audience_rows: int
    traffic_rows: int
