from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import create_engine, text

from src.measurement.models import AudienceFactDraft


def load_audience_facts(
    drafts: tuple[AudienceFactDraft, ...],
    *,
    database_url: str | None,
    media_id: int,
    target_date: date,
    dry_run: bool,
) -> int:
    if dry_run or not database_url or not drafts:
        return len(drafts)
    engine = create_engine(database_url)
    try:
        available_columns = _load_column_names(engine, "audience_event_fact")
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    DELETE FROM audience_event_fact
                    WHERE media_id = :media_id
                      AND occurred_date = :target_date
                      AND source_type IN (
                          'demographic_measurement_v1',
                          'floating_pedestrian_pattern_v1'
                      )
                    """
                ),
                {"media_id": media_id, "target_date": target_date},
            )
            rows = [_filter_row(asdict(draft), available_columns) for draft in drafts]
            if rows:
                columns = tuple(rows[0].keys())
                connection.execute(
                    text(
                        f"""
                        INSERT INTO audience_event_fact ({", ".join(columns)})
                        VALUES ({", ".join(f":{column}" for column in columns)})
                        """
                    ),
                    rows,
                )
    finally:
        engine.dispose()
    return len(drafts)


def trigger_aggregates(
    *,
    database_url: str | None,
    media_id: int,
    target_date: date,
    dry_run: bool,
) -> None:
    if dry_run or not database_url:
        return
    engine = create_engine(database_url)
    start_ts = datetime.combine(target_date, datetime.min.time())
    end_ts = start_ts + timedelta(days=1)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    DELETE FROM agg_audience_minute
                    WHERE media_id = :media_id
                      AND bucket_start_at >= :start_ts
                      AND bucket_start_at < :end_ts
                    """
                ),
                {"media_id": media_id, "start_ts": start_ts, "end_ts": end_ts},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO agg_audience_minute (
                        bucket_start_at, media_id, campaign_id, creative_id,
                        segment_type, segment_value, threshold_sec,
                        floating_population, visible_population, attentive_population,
                        watched_population, watch_time_seconds, dwell_time_seconds, play_count
                    )
                    SELECT
                        date_trunc('minute', occurred_at) AS bucket_start_at,
                        media_id,
                        COALESCE(campaign_id, 0) AS campaign_id,
                        COALESCE(creative_id, 0) AS creative_id,
                        segment_type,
                        segment_value,
                        COALESCE(threshold_sec, 0) AS threshold_sec,
                        SUM(floating_population), SUM(visible_population),
                        SUM(attentive_population), SUM(watched_population),
                        SUM(watch_time_seconds), SUM(dwell_time_seconds), SUM(play_count)
                    FROM audience_event_fact
                    WHERE media_id = :media_id
                      AND occurred_date = :target_date
                    GROUP BY 1,2,3,4,5,6,7
                    """
                ),
                {"media_id": media_id, "target_date": target_date},
            )
            connection.execute(
                text(
                    """
                    DELETE FROM agg_audience_hourly
                    WHERE media_id = :media_id
                      AND date = :target_date
                    """
                ),
                {"media_id": media_id, "target_date": target_date},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO agg_audience_hourly (
                        date, hour, weekday, media_id, campaign_id, creative_id,
                        segment_type, segment_value, threshold_sec,
                        floating_population, visible_population, attentive_population,
                        watched_population, watch_time_seconds, dwell_time_seconds, play_count
                    )
                    SELECT
                        CAST(:target_date AS DATE),
                        EXTRACT(HOUR FROM bucket_start_at)::SMALLINT,
                        EXTRACT(DOW FROM bucket_start_at)::SMALLINT,
                        media_id,
                        COALESCE(campaign_id, 0) AS campaign_id,
                        COALESCE(creative_id, 0) AS creative_id,
                        segment_type,
                        segment_value,
                        COALESCE(threshold_sec, 0) AS threshold_sec,
                        SUM(floating_population), SUM(visible_population),
                        SUM(attentive_population), SUM(watched_population),
                        SUM(watch_time_seconds), SUM(dwell_time_seconds), SUM(play_count)
                    FROM agg_audience_minute
                    WHERE media_id = :media_id
                      AND bucket_start_at >= :start_ts
                      AND bucket_start_at < :end_ts
                    GROUP BY 1,2,3,4,5,6,7,8,9
                    """
                ),
                {
                    "media_id": media_id,
                    "target_date": target_date,
                    "start_ts": start_ts,
                    "end_ts": end_ts,
                },
            )
            connection.execute(
                text(
                    """
                    DELETE FROM agg_audience_daily
                    WHERE media_id = :media_id
                      AND date = :target_date
                    """
                ),
                {"media_id": media_id, "target_date": target_date},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO agg_audience_daily (
                        date, weekday, media_id, campaign_id, creative_id,
                        segment_type, segment_value, threshold_sec,
                        floating_population, visible_population, attentive_population,
                        watched_population, watch_time_seconds, dwell_time_seconds, play_count
                    )
                    SELECT
                        date,
                        weekday,
                        media_id,
                        COALESCE(campaign_id, 0) AS campaign_id,
                        COALESCE(creative_id, 0) AS creative_id,
                        segment_type,
                        segment_value,
                        COALESCE(threshold_sec, 0) AS threshold_sec,
                        SUM(floating_population), SUM(visible_population),
                        SUM(attentive_population), SUM(watched_population),
                        SUM(watch_time_seconds), SUM(dwell_time_seconds), SUM(play_count)
                    FROM agg_audience_hourly
                    WHERE media_id = :media_id
                      AND date = :target_date
                    GROUP BY 1,2,3,4,5,6,7,8
                    """
                ),
                {"media_id": media_id, "target_date": target_date},
            )
    finally:
        engine.dispose()


def _load_column_names(engine, table_name: str) -> set[str]:
    with engine.connect() as connection:
        rows = connection.execute(text(f"SELECT * FROM {table_name} LIMIT 0"))
        return set(rows.keys())


def _filter_row(row: dict[str, Any], allowed_columns: set[str]) -> dict[str, Any]:
    filtered = {key: value for key, value in row.items() if key in allowed_columns}
    if "created_at" in allowed_columns and "created_at" not in filtered:
        filtered["created_at"] = datetime.now(UTC).replace(tzinfo=None)
    return filtered
