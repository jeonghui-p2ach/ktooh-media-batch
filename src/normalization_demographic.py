from __future__ import annotations

from decimal import Decimal

from src.models import AudienceFactDraft, DashboardBinding, DemographicRawRecord

WATCH_THRESHOLDS = (1, 3, 7)


def normalize_demographic_records(
    records: tuple[DemographicRawRecord, ...],
    *,
    media_id_by_camera_code: dict[str, int],
    attentive_policy: str = "gaze_positive",
) -> tuple[AudienceFactDraft, ...]:
    drafts: list[AudienceFactDraft] = []
    for record in records:
        media_id = media_id_by_camera_code.get(record.camera_code)
        if media_id is None:
            continue
        attentive_value = _attentive_value(record, attentive_policy)
        segment_pairs = (
            ("total", "all"),
            ("gender", record.gender),
            ("age", record.age_band),
        )
        for segment_type, segment_value in segment_pairs:
            drafts.append(
                AudienceFactDraft(
                    occurred_at=record.occurred_at,
                    occurred_date=record.occurred_at.date(),
                    occurred_hour=record.occurred_at.hour,
                    media_id=media_id,
                    campaign_id=None,
                    creative_id=None,
                    creative_name=record.creative_name,
                    segment_type=segment_type,
                    segment_value=segment_value,
                    threshold_sec=None,
                    floating_population=Decimal("0"),
                    visible_population=Decimal("1"),
                    attentive_population=attentive_value,
                    watched_population=Decimal("0"),
                    watch_time_seconds=record.gaze_duration_seconds,
                    dwell_time_seconds=record.stay_duration_seconds,
                    play_count=Decimal("0"),
                    allocation_basis="camera_demographic",
                    source_type="demographic_measurement_v1",
                    source_batch_id=record.source_batch_id,
                    camera_code=record.camera_code,
                    raw_ref=record.raw_ref,
                    source_schema="demographic_measurement_v1",
                )
            )
            for threshold in WATCH_THRESHOLDS:
                drafts.append(
                    AudienceFactDraft(
                        occurred_at=record.occurred_at,
                        occurred_date=record.occurred_at.date(),
                        occurred_hour=record.occurred_at.hour,
                        media_id=media_id,
                        campaign_id=None,
                        creative_id=None,
                        creative_name=record.creative_name,
                        segment_type=segment_type,
                        segment_value=segment_value,
                        threshold_sec=threshold,
                        floating_population=Decimal("0"),
                        visible_population=Decimal("0"),
                        attentive_population=Decimal("0"),
                        watched_population=Decimal(
                            "1" if record.gaze_duration_seconds >= Decimal(threshold) else "0"
                        ),
                        watch_time_seconds=Decimal("0"),
                        dwell_time_seconds=Decimal("0"),
                        play_count=Decimal("0"),
                        allocation_basis="camera_demographic",
                        source_type="demographic_measurement_v1",
                        source_batch_id=record.source_batch_id,
                        camera_code=record.camera_code,
                        raw_ref=record.raw_ref,
                        source_schema="demographic_measurement_v1",
                    )
                )
    return tuple(drafts)


def _attentive_value(record: DemographicRawRecord, attentive_policy: str) -> Decimal:
    if attentive_policy == "gaze_positive":
        return Decimal("1") if record.gaze_duration_seconds > 0 else Decimal("0")
    return Decimal("1")
