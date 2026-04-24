from __future__ import annotations

import gzip
import hashlib
import json
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import boto3

from src.common.config import Settings
from src.measurement.models import CollectedObject, DashboardBinding


def collect_objects(
    *,
    target_date: date,
    bindings: tuple[DashboardBinding, ...],
    settings: Settings,
) -> tuple[CollectedObject, ...]:
    local_objects = _collect_local_objects(bindings=bindings, settings=settings)
    if local_objects:
        return local_objects
    return _collect_s3_objects(target_date=target_date, bindings=bindings, settings=settings)


def iter_object_payload_lines(
    collected_object: CollectedObject,
) -> Iterator[tuple[int, dict[str, object] | str]]:
    if collected_object.local_path is not None:
        yield from _iter_local_jsonl_lines(collected_object.local_path)
        return

    if collected_object.bucket is None:
        return
    client = boto3.client("s3")
    response = client.get_object(Bucket=collected_object.bucket, Key=collected_object.key)
    raw_body = response["Body"]
    for line_number, raw_line in enumerate(raw_body.iter_lines(), start=1):
        yield _parse_json_line(raw_line.decode("utf-8"), line_number)


def _collect_local_objects(
    *,
    bindings: tuple[DashboardBinding, ...],
    settings: Settings,
) -> tuple[CollectedObject, ...]:
    if not settings.raw_source_root.exists():
        return ()
    objects: list[CollectedObject] = []
    for binding in bindings:
        local_filename = (
            settings.local_demographic_filename
            if binding.source_type == "demographic"
            else settings.local_floating_filename
        )
        local_path = settings.raw_source_root / local_filename
        if not local_path.exists():
            continue
        objects.append(
            CollectedObject(
                source_type=binding.source_type,
                camera_code=binding.camera_code,
                key=str(local_path),
                source_batch_id=_source_batch_id(str(local_path)),
                local_path=local_path,
                bucket=None,
            )
        )
    return tuple(objects)


def _collect_s3_objects(
    *,
    target_date: date,
    bindings: tuple[DashboardBinding, ...],
    settings: Settings,
) -> tuple[CollectedObject, ...]:
    client = boto3.client("s3")
    objects: list[CollectedObject] = []
    for binding in bindings:
        prefix = f"raw/date={target_date.isoformat()}/device_id={binding.camera_code}/"
        continuation_token: str | None = None
        while True:
            kwargs = {
                "Bucket": settings.source_bucket,
                "Prefix": prefix,
                "MaxKeys": 1000,
            }
            if continuation_token is not None:
                kwargs["ContinuationToken"] = continuation_token
            response = client.list_objects_v2(**kwargs)
            for item in response.get("Contents", []):
                key = str(item["Key"])
                objects.append(
                    CollectedObject(
                        source_type=binding.source_type,
                        camera_code=binding.camera_code,
                        key=key,
                        source_batch_id=_source_batch_id(key),
                        local_path=None,
                        bucket=settings.source_bucket,
                    )
                )
            if not response.get("IsTruncated"):
                break
            continuation_token = response.get("NextContinuationToken")
    return tuple(objects)


def _iter_local_jsonl_lines(local_path: Path) -> Iterator[tuple[int, dict[str, object] | str]]:
    opener = gzip.open if local_path.suffix == ".gz" else open
    with opener(local_path, "rt", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            yield _parse_json_line(raw_line, line_number)


def _parse_json_line(raw_line: str, line_number: int) -> tuple[int, dict[str, object] | str]:
    stripped = raw_line.strip()
    if not stripped:
        return line_number, "empty_line"
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return line_number, "invalid_json"
    if not isinstance(payload, dict):
        return line_number, "json_not_object"
    return line_number, payload


def _source_batch_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]
