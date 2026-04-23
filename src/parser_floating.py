from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from src.collector import iter_object_payload_lines
from src.models import CollectedObject, FloatingRawRecord, RejectedRow


def parse_floating_objects(
    objects: tuple[CollectedObject, ...],
) -> tuple[tuple[FloatingRawRecord, ...], tuple[RejectedRow, ...]]:
    accepted: list[FloatingRawRecord] = []
    rejected: list[RejectedRow] = []
    for obj in objects:
        if obj.source_type != "floating":
            continue
        for line_number, payload_or_reason in iter_object_payload_lines(obj):
            raw_ref = f"{obj.key}:{line_number}"
            if isinstance(payload_or_reason, str):
                rejected.append(_rejected(obj, raw_ref, payload_or_reason, None))
                continue
            try:
                accepted.append(_parse_payload(obj, raw_ref, payload_or_reason))
            except (KeyError, ValueError, InvalidOperation, TypeError) as error:
                rejected.append(_rejected(obj, raw_ref, "invalid_floating_payload", str(error)))
    return tuple(accepted), tuple(rejected)


def _parse_payload(
    obj: CollectedObject,
    raw_ref: str,
    payload: dict[str, Any],
) -> FloatingRawRecord:
    started_at = _to_utc_naive(payload["start_time"])
    ended_at = _to_utc_naive(payload["end_time"])
    if ended_at < started_at:
        raise ValueError("end_before_start")
    return FloatingRawRecord(
        camera_code=obj.camera_code,
        source_batch_id=obj.source_batch_id,
        raw_ref=raw_ref,
        object_type=str(payload["type"]),
        started_at=started_at,
        ended_at=ended_at,
        dwell_seconds=Decimal(str(payload["dwell"])),
        status=str(payload["status"]).strip().lower(),
    )


def _rejected(
    obj: CollectedObject,
    raw_ref: str,
    reason: str,
    detail: str | None,
) -> RejectedRow:
    return RejectedRow(
        source_type="floating",
        camera_code=obj.camera_code,
        source_batch_id=obj.source_batch_id,
        raw_ref=raw_ref,
        reason=reason,
        detail=detail,
    )


def _to_utc_naive(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    localized = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return localized.astimezone(UTC).replace(tzinfo=None)
