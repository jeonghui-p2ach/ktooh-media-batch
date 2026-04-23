from __future__ import annotations

from dataclasses import replace

from src.dashboard_registry import AttributionContext, CampaignWindow, CreativeRef
from src.models import AudienceFactDraft, RejectedRow


def resolve_attribution(
    drafts: tuple[AudienceFactDraft, ...],
    *,
    attribution_context: AttributionContext,
) -> tuple[tuple[AudienceFactDraft, ...], tuple[RejectedRow, ...]]:
    accepted: list[AudienceFactDraft] = []
    rejected: list[RejectedRow] = []
    for draft in drafts:
        if draft.source_type != "demographic_measurement_v1":
            accepted.append(draft)
            continue
        matches = _matching_campaigns(draft, attribution_context.campaign_windows)
        if not matches:
            accepted.append(draft)
            continue
        unique_campaign_ids = tuple(dict.fromkeys(match.campaign_id for match in matches))
        if len(unique_campaign_ids) > 1:
            rejected.append(
                RejectedRow(
                    source_type="demographic",
                    camera_code=draft.camera_code,
                    source_batch_id=draft.source_batch_id,
                    raw_ref=draft.raw_ref,
                    reason="campaign_ambiguous",
                    detail="multiple_campaign_matches",
                )
            )
            continue
        campaign_id = unique_campaign_ids[0]
        creative_id = _resolve_creative_id(
            campaign_id=campaign_id,
            creative_name=draft.creative_name,
            creative_refs=attribution_context.creative_refs,
        )
        accepted.append(
            replace(
                draft,
                campaign_id=campaign_id,
                creative_id=creative_id,
            )
        )
    return tuple(accepted), tuple(rejected)


def _matching_campaigns(
    draft: AudienceFactDraft,
    windows: tuple[CampaignWindow, ...],
) -> tuple[CampaignWindow, ...]:
    return tuple(
        window
        for window in windows
        if window.media_id == draft.media_id
        and window.started_at <= draft.occurred_at
        and draft.occurred_at < window.ended_at
    )


def _resolve_creative_id(
    *,
    campaign_id: int,
    creative_name: str | None,
    creative_refs: tuple[CreativeRef, ...],
) -> int | None:
    if creative_name is None:
        return None
    matches = tuple(
        creative_ref
        for creative_ref in creative_refs
        if creative_ref.campaign_id == campaign_id and creative_ref.creative_name == creative_name
    )
    if len(matches) != 1:
        return None
    return matches[0].creative_id
