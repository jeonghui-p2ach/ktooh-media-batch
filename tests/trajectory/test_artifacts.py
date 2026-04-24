import pickle
from pathlib import Path

import pytest

from src.trajectory.artifacts import (
    ArtifactSummary,
    load_pickle_artifact,
    object_to_rows,
    summarize_artifact,
    validate_required_columns,
)
from src.trajectory.contracts import ArtifactSpec


def test_load_pickle_artifact_reads_pickle_file(tmp_path: Path) -> None:
    path = tmp_path / "artifact.pkl"
    payload = [{"episode_id": "EP-1", "camera_name": "CAM_14"}]
    path.write_bytes(pickle.dumps(payload))

    loaded = load_pickle_artifact(path)

    assert loaded == payload


def test_load_pickle_artifact_rejects_non_pickle_extension(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"
    path.write_text("{}")

    with pytest.raises(ValueError, match=r"\.pkl"):
        load_pickle_artifact(path)


def test_validate_required_columns_accepts_matching_rows() -> None:
    spec = ArtifactSpec(
        name="presence_episode_df",
        stage="local-stitch",
        relative_path=Path("presence_episode_df.pkl"),
        artifact_format="pkl",
        required_columns=("episode_id", "camera_name"),
    )

    columns = validate_required_columns(
        (
            {"episode_id": "EP-1", "camera_name": "CAM_14", "extra": 1},
            {"episode_id": "EP-2", "camera_name": "CAM_15"},
        ),
        spec,
    )

    assert columns == ("episode_id", "camera_name", "extra")


def test_validate_required_columns_rejects_missing_columns() -> None:
    spec = ArtifactSpec(
        name="presence_episode_df",
        stage="local-stitch",
        relative_path=Path("presence_episode_df.pkl"),
        artifact_format="pkl",
        required_columns=("episode_id", "camera_name"),
    )

    with pytest.raises(ValueError, match="camera_name"):
        validate_required_columns(({"episode_id": "EP-1"},), spec)


def test_summarize_artifact_handles_empty_rows() -> None:
    summary = summarize_artifact(())

    assert summary == ArtifactSummary(row_count=0, columns=())


def test_object_to_rows_reads_mapping_sequence() -> None:
    rows = object_to_rows(
        [
            {"episode_id": "EP-1", "camera_name": "CAM_14"},
            {"episode_id": "EP-2", "camera_name": "CAM_15"},
        ]
    )

    assert rows[0]["episode_id"] == "EP-1"
    assert len(rows) == 2
