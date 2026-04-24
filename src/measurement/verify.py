from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine, text

from src.measurement.models import LoadSummary


def verify_batch_load(
    *,
    database_url: str | None,
    media_id: int,
    target_date: date,
    summary: LoadSummary,
    dry_run: bool,
) -> dict[str, int]:
    if dry_run or not database_url:
        return {
            "audience_rows": summary.audience_rows,
            "traffic_rows": summary.traffic_rows,
            "rejected_rows": summary.rejected_rows,
        }
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            audience_count = int(
                connection.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM audience_event_fact
                        WHERE media_id = :media_id
                          AND occurred_date = :target_date
                          AND source_type IN (
                              'demographic_measurement_v1',
                              'floating_pedestrian_pattern_v1'
                          )
                        """
                    ),
                    {"media_id": media_id, "target_date": target_date},
                ).scalar_one()
            )
            traffic_count = int(
                connection.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM traffic
                        WHERE media_id = :media_id
                          AND DATE(ts) = :target_date
                        """
                    ),
                    {"media_id": media_id, "target_date": target_date},
                ).scalar_one()
            )
    finally:
        engine.dispose()
    return {
        "audience_rows": audience_count,
        "traffic_rows": traffic_count,
        "rejected_rows": summary.rejected_rows,
    }
