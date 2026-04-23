from __future__ import annotations

from decimal import Decimal

from src.models import AudienceFactDraft, FloatingRawRecord, TrafficDraft

VEHICLE_TYPE_MAP = {
    "car": "CAR",
    "bus": "BUS",
    "truck": "TRUCK",
    "motorcycle": "MOTORCYCLE",
}


def normalize_floating_records(
    records: tuple[FloatingRawRecord, ...],
    *,
    media_id_by_camera_code: dict[str, int],
    include_pedestrian_pattern: bool,
    direction_mode: str,
) -> tuple[tuple[TrafficDraft, ...], tuple[AudienceFactDraft, ...]]:
    traffic_rows: list[TrafficDraft] = []
    audience_rows: list[AudienceFactDraft] = []
    for record in records:
        media_id = media_id_by_camera_code.get(record.camera_code)
        if media_id is None:
            continue
        normalized_type = _normalize_object_type(record.object_type)
        if normalized_type is not None:
            traffic_rows.append(
                TrafficDraft(
                    media_id=media_id,
                    campaign_id=None,
                    ts=record.started_at,
                    vehicle_type=normalized_type,
                    direction=_normalize_direction(record.status, direction_mode),
                    count=1,
                    camera_code=record.camera_code,
                    raw_ref=record.raw_ref,
                    source_batch_id=record.source_batch_id,
                )
            )
            continue
        if include_pedestrian_pattern and record.object_type.strip().lower() == "pedestrian":
            audience_rows.append(
                AudienceFactDraft(
                    occurred_at=record.started_at,
                    occurred_date=record.started_at.date(),
                    occurred_hour=record.started_at.hour,
                    media_id=media_id,
                    campaign_id=None,
                    creative_id=None,
                    creative_name=None,
                    segment_type="total",
                    segment_value="all",
                    threshold_sec=None,
                    floating_population=Decimal("0"),
                    visible_population=Decimal("0"),
                    attentive_population=Decimal("0"),
                    watched_population=Decimal("0"),
                    watch_time_seconds=Decimal("0"),
                    dwell_time_seconds=record.dwell_seconds,
                    play_count=Decimal("0"),
                    allocation_basis="camera_floating_pedestrian",
                    source_type="floating_pedestrian_pattern_v1",
                    source_batch_id=record.source_batch_id,
                    camera_code=record.camera_code,
                    raw_ref=record.raw_ref,
                    source_schema="floating_measurement_v1",
                )
            )
    return tuple(traffic_rows), tuple(audience_rows)


def _normalize_object_type(value: str) -> str | None:
    return VEHICLE_TYPE_MAP.get(value.strip().lower())


def _normalize_direction(status: str, direction_mode: str) -> str:
    if direction_mode == "status":
        if status in {"enter", "exit"}:
            return status
        return "unknown"
    return "unknown"
