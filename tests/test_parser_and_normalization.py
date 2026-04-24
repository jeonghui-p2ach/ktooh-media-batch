from datetime import datetime
from decimal import Decimal
from pathlib import Path

from src.measurement.models import CollectedObject, DemographicRawRecord, FloatingRawRecord
from src.measurement.normalization_demographic import normalize_demographic_records
from src.measurement.normalization_floating import normalize_floating_records
from src.measurement.parser_demographic import parse_demographic_objects
from src.measurement.parser_floating import parse_floating_objects


def test_parse_and_normalize_demographic_sample() -> None:
    path = Path("./samples/demographic.jsonl")
    objects = (
        CollectedObject(
            source_type="demographic",
            camera_code="CAM_5",
            key=str(path),
            source_batch_id="sample-demographic",
            local_path=path,
            bucket=None,
        ),
    )
    records, rejected = parse_demographic_objects(objects)
    assert records
    assert not rejected
    drafts = normalize_demographic_records(records[:1], media_id_by_camera_code={"CAM_5": 101})
    assert any(draft.segment_type == "total" and draft.threshold_sec is None for draft in drafts)
    assert any(draft.segment_type == "total" and draft.threshold_sec == 1 for draft in drafts)


def test_parse_and_normalize_floating_sample() -> None:
    path = Path("./samples/floating.jsonl")
    objects = (
        CollectedObject(
            source_type="floating",
            camera_code="CAM_14",
            key=str(path),
            source_batch_id="sample-floating",
            local_path=path,
            bucket=None,
        ),
    )
    records, rejected = parse_floating_objects(objects)
    assert records
    assert not rejected
    traffic_rows, audience_rows = normalize_floating_records(
        records[:2],
        media_id_by_camera_code={"CAM_14": 101},
        include_pedestrian_pattern=True,
        direction_mode="status",
    )
    assert traffic_rows
    assert audience_rows
    assert all(row.count == 1 for row in traffic_rows)


def test_demographic_visibility_attention_and_watch_policy() -> None:
    occurred_at = datetime.fromisoformat("2026-04-23T01:02:03")
    records = (
        DemographicRawRecord(
            camera_code="CAM_5",
            source_batch_id="batch-1",
            raw_ref="raw-1",
            occurred_at=occurred_at,
            ended_at=occurred_at,
            stay_duration_seconds=Decimal("5"),
            gaze_duration_seconds=Decimal("3"),
            gender="female",
            age_band="30s",
            creative_name=None,
        ),
    )

    drafts = normalize_demographic_records(records, media_id_by_camera_code={"CAM_5": 101})
    total_base = tuple(
        draft
        for draft in drafts
        if draft.segment_type == "total" and draft.threshold_sec is None
    )
    total_watch = tuple(
        draft
        for draft in drafts
        if draft.segment_type == "total" and draft.threshold_sec == 3
    )

    assert len(total_base) == 1
    assert total_base[0].visible_population == Decimal("1")
    assert total_base[0].attentive_population == Decimal("1")
    assert total_base[0].watched_population == Decimal("0")
    assert len(total_watch) == 1
    assert total_watch[0].visible_population == Decimal("0")
    assert total_watch[0].attentive_population == Decimal("0")
    assert total_watch[0].watched_population == Decimal("1")


def test_floating_pedestrian_pattern_is_dwell_only() -> None:
    started_at = datetime.fromisoformat("2026-04-23T01:02:03")
    records = (
        FloatingRawRecord(
            camera_code="CAM_14",
            source_batch_id="batch-1",
            raw_ref="raw-1",
            object_type="pedestrian",
            started_at=started_at,
            ended_at=started_at,
            dwell_seconds=Decimal("7"),
            status="enter",
        ),
    )

    traffic_rows, audience_rows = normalize_floating_records(
        records,
        media_id_by_camera_code={"CAM_14": 101},
        include_pedestrian_pattern=True,
        direction_mode="status",
    )

    assert not traffic_rows
    assert len(audience_rows) == 1
    assert audience_rows[0].visible_population == Decimal("0")
    assert audience_rows[0].attentive_population == Decimal("0")
    assert audience_rows[0].watched_population == Decimal("0")
    assert audience_rows[0].dwell_time_seconds == Decimal("7")


def test_floating_traffic_direction_uses_canonical_values() -> None:
    started_at = datetime.fromisoformat("2026-04-23T01:02:03")
    records = (
        FloatingRawRecord(
            camera_code="CAM_14",
            source_batch_id="batch-1",
            raw_ref="raw-enter",
            object_type="car",
            started_at=started_at,
            ended_at=started_at,
            dwell_seconds=Decimal("1"),
            status="enter",
        ),
        FloatingRawRecord(
            camera_code="CAM_14",
            source_batch_id="batch-1",
            raw_ref="raw-exit",
            object_type="bus",
            started_at=started_at,
            ended_at=started_at,
            dwell_seconds=Decimal("1"),
            status="exit",
        ),
        FloatingRawRecord(
            camera_code="CAM_14",
            source_batch_id="batch-1",
            raw_ref="raw-unknown",
            object_type="truck",
            started_at=started_at,
            ended_at=started_at,
            dwell_seconds=Decimal("1"),
            status="stopped",
        ),
    )

    traffic_rows, _ = normalize_floating_records(
        records,
        media_id_by_camera_code={"CAM_14": 101},
        include_pedestrian_pattern=False,
        direction_mode="status",
    )

    assert tuple(row.direction for row in traffic_rows) == ("enter", "exit", "unknown")
