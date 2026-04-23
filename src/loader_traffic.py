from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import create_engine, text

from src.models import TrafficDraft


def load_traffic_rows(
    drafts: tuple[TrafficDraft, ...],
    *,
    database_url: str | None,
    media_id: int,
    target_date: date,
    dry_run: bool,
) -> int:
    if dry_run or not database_url or not drafts:
        return len(drafts)
    engine = create_engine(database_url)
    start_ts = datetime.combine(target_date, datetime.min.time())
    end_ts = start_ts + timedelta(days=1)
    try:
        available_columns = _load_column_names(engine, "traffic")
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    DELETE FROM traffic
                    WHERE media_id = :media_id
                      AND ts >= :start_ts
                      AND ts < :end_ts
                    """
                ),
                {"media_id": media_id, "start_ts": start_ts, "end_ts": end_ts},
            )
            rows = [_filter_row(asdict(draft), available_columns) for draft in drafts]
            if rows:
                columns = tuple(rows[0].keys())
                connection.execute(
                    text(
                        f"""
                        INSERT INTO traffic ({", ".join(columns)})
                        VALUES ({", ".join(f":{column}" for column in columns)})
                        """
                    ),
                    rows,
                )
    finally:
        engine.dispose()
    return len(drafts)


def _load_column_names(engine, table_name: str) -> set[str]:
    with engine.connect() as connection:
        rows = connection.execute(text(f"SELECT * FROM {table_name} LIMIT 0"))
        return set(rows.keys())


def _filter_row(row: dict[str, Any], allowed_columns: set[str]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key in allowed_columns}
