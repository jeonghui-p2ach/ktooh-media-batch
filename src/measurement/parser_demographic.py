from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from src.measurement.collector import iter_object_payload_lines
from src.measurement.models import CollectedObject, DemographicRawRecord, RejectedRow


def parse_demographic_objects(
    objects: tuple[CollectedObject, ...],
) -> tuple[tuple[DemographicRawRecord, ...], tuple[RejectedRow, ...]]:
    accepted: list[DemographicRawRecord] = []
    rejected: list[RejectedRow] = []
    for obj in objects:
        if obj.source_type != "demographic":
            continue
        for line_number, payload_or_reason in iter_object_payload_lines(obj):
            raw_ref = f"{obj.key}:{line_number}"
            if isinstance(payload_or_reason, str):
                rejected.append(_rejected(obj, raw_ref, payload_or_reason, None))
                continue
            try:
                accepted.append(_parse_payload(obj, raw_ref, payload_or_reason))
            except (KeyError, ValueError, InvalidOperation, TypeError) as error:
                rejected.append(_rejected(obj, raw_ref, "invalid_demographic_payload", str(error)))
    return tuple(accepted), tuple(rejected)


def _parse_payload(
    obj: CollectedObject,
    raw_ref: str,
    payload: dict[str, Any],
) -> DemographicRawRecord:
    occurred_at = _to_utc_naive(payload["timestamp"])
    ended_at = _to_utc_naive(payload["last_seen"])
    if ended_at < occurred_at:
        raise ValueError("last_seen_before_timestamp")
    gender = _normalize_gender(payload.get("gender"), payload.get("par_gender"))
    age_band = _normalize_age_band(payload.get("age"), payload.get("par_age"))
    creative_name = None if payload.get("creative_name") is None else str(payload["creative_name"])
    return DemographicRawRecord(
        camera_code=_camera_code_from_device_id(str(payload["device_id"])),
        source_batch_id=obj.source_batch_id,
        raw_ref=raw_ref,
        occurred_at=occurred_at,
        ended_at=ended_at,
        stay_duration_seconds=Decimal(str(payload["stay_duration"])),
        gaze_duration_seconds=Decimal(str(payload["gaze_duration"])),
        gender=gender,
        age_band=age_band,
        creative_name=creative_name,
    )


def _rejected(
    obj: CollectedObject,
    raw_ref: str,
    reason: str,
    detail: str | None,
) -> RejectedRow:
    return RejectedRow(
        source_type="demographic",
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


def _camera_code_from_device_id(device_id: str) -> str:
    parts = device_id.split("_")
    if len(parts) >= 2 and parts[-2] == "CAM":
        return f"CAM_{parts[-1]}"
    if "CAM_" in device_id:
        return device_id[device_id.index("CAM_") :]
    return device_id


def _normalize_gender(gender: Any, par_gender: Any) -> str:
    for value in (gender, par_gender):
        normalized = str(value or "").strip().lower()
        if normalized in {"man", "male"}:
            return "male"
        if normalized in {"woman", "female"}:
            return "female"
    return "unknown"


def _normalize_age_band(age: Any, par_age: Any) -> str:
    if isinstance(age, (int, float)) or str(age).isdigit():
        numeric_age = int(float(age))
        if numeric_age < 20:
            return "10u"
        if numeric_age < 30:
            return "20s"
        if numeric_age < 40:
            return "30s"
        if numeric_age < 50:
            return "40s"
        if numeric_age < 60:
            return "50s"
        if numeric_age < 70:
            return "60s"
        return "70p"
    normalized = str(par_age or "").strip().lower()
    if normalized in {"10u", "20s", "30s", "40s", "50s", "60s", "70p"}:
        return normalized
    if normalized == "18-60":
        return "30s"
    return "unknown"
