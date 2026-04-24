from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import create_engine, text

from src.measurement.models import DashboardBinding


@dataclass(frozen=True, slots=True)
class CampaignWindow:
    media_id: int
    campaign_id: int
    started_at: datetime
    ended_at: datetime
    creative_name: str | None


@dataclass(frozen=True, slots=True)
class CreativeRef:
    creative_id: int
    campaign_id: int
    creative_name: str


@dataclass(frozen=True, slots=True)
class AttributionContext:
    campaign_windows: tuple[CampaignWindow, ...]
    creative_refs: tuple[CreativeRef, ...]


def load_dashboard_bindings(
    *,
    database_url: str | None,
    media_id: int,
) -> tuple[DashboardBinding, ...]:
    if not database_url:
        return ()
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT id, camera_code, source_type, media_id
                    FROM cameras
                    WHERE media_id = :media_id
                      AND is_active = true
                    ORDER BY id
                    """
                ),
                {"media_id": media_id},
            ).mappings().all()
    finally:
        engine.dispose()
    return tuple(
        DashboardBinding(
            camera_code=str(row["camera_code"]),
            source_type=_normalize_source_type(row["source_type"]),
            media_id=int(row["media_id"]),
            camera_id=int(row["id"]),
        )
        for row in rows
    )


def load_attribution_context(
    *,
    database_url: str | None,
    media_id: int,
) -> AttributionContext:
    if not database_url:
        return AttributionContext(campaign_windows=(), creative_refs=())
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            window_rows = connection.execute(
                text(
                    """
                    SELECT
                        mcm.media_id AS media_id,
                        cs.campaign_id AS campaign_id,
                        cs.started_at AS started_at,
                        cs.ended_at AS ended_at,
                        cs.creative_name AS creative_name
                    FROM media_campaign_map AS mcm
                    JOIN campaign_schedules AS cs
                      ON cs.campaign_id = mcm.campaign_id
                    WHERE mcm.media_id = :media_id
                      AND mcm.is_active = true
                    ORDER BY cs.started_at
                    """
                ),
                {"media_id": media_id},
            ).mappings().all()
            creative_rows = connection.execute(
                text(
                    """
                    SELECT id AS creative_id, campaign_id, name AS creative_name
                    FROM creatives
                    ORDER BY campaign_id, id
                    """
                )
            ).mappings().all()
    finally:
        engine.dispose()
    return AttributionContext(
        campaign_windows=tuple(_build_campaign_window(row) for row in window_rows),
        creative_refs=tuple(
            CreativeRef(
                creative_id=int(row["creative_id"]),
                campaign_id=int(row["campaign_id"]),
                creative_name=str(row["creative_name"]),
            )
            for row in creative_rows
        ),
    )


def _normalize_source_type(value: Any) -> str:
    normalized = str(value).strip().lower()
    if normalized in {"demographic", "floating"}:
        return normalized
    raise ValueError(f"unsupported source_type: {value}")


def _build_campaign_window(row: Any) -> CampaignWindow:
    started_at = _to_utc_naive(row["started_at"])
    ended_raw = row["ended_at"]
    ended_at = (
        _to_utc_naive(ended_raw)
        if ended_raw is not None
        else started_at + timedelta(minutes=1)
    )
    return CampaignWindow(
        media_id=int(row["media_id"]),
        campaign_id=int(row["campaign_id"]),
        started_at=started_at,
        ended_at=ended_at,
        creative_name=None if row["creative_name"] is None else str(row["creative_name"]),
    )


def _to_utc_naive(value: Any) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    localized = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return localized.astimezone(UTC).replace(tzinfo=None)
