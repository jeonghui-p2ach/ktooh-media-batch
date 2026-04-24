from datetime import datetime
from decimal import Decimal

from src.measurement.attribution import resolve_attribution
from src.measurement.dashboard_registry import AttributionContext, CampaignWindow, CreativeRef
from src.measurement.models import AudienceFactDraft


def test_resolve_attribution_sets_campaign_and_single_creative() -> None:
    draft = _draft(creative_name="Creative A")
    context = AttributionContext(
        campaign_windows=(
            CampaignWindow(
                media_id=101,
                campaign_id=201,
                started_at=datetime.fromisoformat("2026-04-23T00:00:00"),
                ended_at=datetime.fromisoformat("2026-04-24T00:00:00"),
                creative_name="Creative A",
            ),
        ),
        creative_refs=(
            CreativeRef(creative_id=301, campaign_id=201, creative_name="Creative A"),
        ),
    )

    accepted, rejected = resolve_attribution((draft,), attribution_context=context)

    assert not rejected
    assert accepted[0].campaign_id == 201
    assert accepted[0].creative_id == 301


def test_resolve_attribution_allows_campaign_without_creative_match() -> None:
    draft = _draft(creative_name="Missing Creative")
    context = AttributionContext(
        campaign_windows=(
            CampaignWindow(
                media_id=101,
                campaign_id=201,
                started_at=datetime.fromisoformat("2026-04-23T00:00:00"),
                ended_at=datetime.fromisoformat("2026-04-24T00:00:00"),
                creative_name=None,
            ),
        ),
        creative_refs=(),
    )

    accepted, rejected = resolve_attribution((draft,), attribution_context=context)

    assert not rejected
    assert accepted[0].campaign_id == 201
    assert accepted[0].creative_id is None


def test_resolve_attribution_rejects_multiple_campaign_matches() -> None:
    draft = _draft(creative_name=None)
    context = AttributionContext(
        campaign_windows=(
            CampaignWindow(
                media_id=101,
                campaign_id=201,
                started_at=datetime.fromisoformat("2026-04-23T00:00:00"),
                ended_at=datetime.fromisoformat("2026-04-24T00:00:00"),
                creative_name=None,
            ),
            CampaignWindow(
                media_id=101,
                campaign_id=202,
                started_at=datetime.fromisoformat("2026-04-23T00:00:00"),
                ended_at=datetime.fromisoformat("2026-04-24T00:00:00"),
                creative_name=None,
            ),
        ),
        creative_refs=(),
    )

    accepted, rejected = resolve_attribution((draft,), attribution_context=context)

    assert not accepted
    assert len(rejected) == 1
    assert rejected[0].reason == "campaign_ambiguous"


def _draft(*, creative_name: str | None) -> AudienceFactDraft:
    occurred_at = datetime.fromisoformat("2026-04-23T01:00:00")
    return AudienceFactDraft(
        occurred_at=occurred_at,
        occurred_date=occurred_at.date(),
        occurred_hour=occurred_at.hour,
        media_id=101,
        campaign_id=None,
        creative_id=None,
        creative_name=creative_name,
        segment_type="total",
        segment_value="all",
        threshold_sec=None,
        floating_population=Decimal("0"),
        visible_population=Decimal("1"),
        attentive_population=Decimal("1"),
        watched_population=Decimal("0"),
        watch_time_seconds=Decimal("1"),
        dwell_time_seconds=Decimal("5"),
        play_count=Decimal("0"),
        allocation_basis="camera_demographic",
        source_type="demographic_measurement_v1",
        source_batch_id="batch-1",
        camera_code="CAM_5",
        raw_ref="raw-1",
        source_schema="demographic_measurement_v1",
    )
