from decimal import Decimal
from pathlib import Path

from src.models import CollectedObject
from src.normalization_demographic import normalize_demographic_records
from src.normalization_floating import normalize_floating_records
from src.parser_demographic import parse_demographic_objects
from src.parser_floating import parse_floating_objects


def test_parse_and_normalize_demographic_sample() -> None:
    path = Path("/Users/jeonghui/works/dashboard-poc/project-pooh-kt/docs/demographic.jsonl")
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
    path = Path("/Users/jeonghui/works/dashboard-poc/project-pooh-kt/docs/floating.jsonl")
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
