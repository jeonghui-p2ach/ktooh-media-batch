from __future__ import annotations

import pickle
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.trajectory.contracts import ArtifactSpec


@dataclass(frozen=True, slots=True)
class ArtifactSummary:
    row_count: int
    columns: tuple[str, ...]


def load_pickle_artifact(path: Path) -> Any:
    if path.suffix != ".pkl":
        raise ValueError(f"artifact must be a .pkl file: {path}")
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("rb") as file:
        return pickle.load(file)


def object_to_rows(value: Any) -> tuple[dict[str, Any], ...]:
    if hasattr(value, "to_dict"):
        records = value.to_dict(orient="records")
        return tuple(dict(record) for record in records)
    if isinstance(value, Mapping):
        return tuple(dict(row) for row in value.values() if isinstance(row, Mapping))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(dict(row) for row in value if isinstance(row, Mapping))
    raise TypeError("artifact must be a DataFrame-like object or sequence of mappings")


def validate_required_columns(
    rows: Sequence[Mapping[str, Any]],
    spec: ArtifactSpec,
) -> tuple[str, ...]:
    available_columns = _collect_columns(rows)
    missing_columns = tuple(
        column for column in spec.required_columns if column not in available_columns
    )
    if missing_columns:
        raise ValueError(
            f"artifact {spec.name} is missing required columns: {', '.join(missing_columns)}"
        )
    return available_columns


def summarize_artifact(rows: Sequence[Mapping[str, Any]]) -> ArtifactSummary:
    return ArtifactSummary(
        row_count=len(rows),
        columns=_collect_columns(rows),
    )


def _collect_columns(rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    ordered_columns: list[str] = []
    seen_columns: set[str] = set()
    for row in rows:
        for column in row:
            if column in seen_columns:
                continue
            seen_columns.add(column)
            ordered_columns.append(str(column))
    return tuple(ordered_columns)
